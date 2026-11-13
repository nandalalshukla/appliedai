"""Project 4 reference solution - a research team of agents with long-term memory.

A lead agent plans, delegates sub-questions to researcher subagents (in parallel, each
with its own context), a critic checks the draft against the evidence, and a memory
store carries the user's preferences into later sessions.

Run:   python projects/04-research-team/solution/research.py
       python projects/04-research-team/solution/research.py "your question"
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from aikit import MODEL, CostMeter, FakeClient, fake_tool, fake_tools, get_client, mock_mode, text_of
from aikit.agent import Agent, print_events
from aikit.memory import MemoryStore
from aikit.rag import HybridRetriever, load_corpus
from aikit.tools import ToolRegistry

MAX_SUBAGENTS = 4  # fan-out cap: the cheapest cost control in a multi-agent system


@dataclass
class Team:
    docs_dir: str = "data/handbook"
    memory_path: Path = field(default_factory=lambda: Path(tempfile.mkdtemp()) / "memory.jsonl")
    lead_script: list | None = None  # mock-mode scripts
    researcher_scripts: list | None = None
    critic_script: list | None = None
    memory_script: list | None = None

    def __post_init__(self):
        self.retriever = HybridRetriever(load_corpus(self.docs_dir))
        self.memory = MemoryStore(self.memory_path)
        self.meter = CostMeter()
        self.evidence: list[dict] = []  # everything researchers found, kept OUTSIDE the lead's context
        self.spawned = 0
        # One client per role, created once, so scripted replies are consumed in order.
        self.critic_client = self._client(self.critic_script)
        self.memory_client = self._client(self.memory_script)

    def _client(self, script):
        return FakeClient(script=list(script or [])) if mock_mode() else get_client()

    def _researcher_script(self, question: str):
        """Mock mode: pick the script whose keyword appears in the question (order-independent,
        because researchers run in parallel threads)."""
        for keyword, script in self.researcher_scripts or []:
            if keyword in question.lower():
                return script
        return None

    # ---- researcher subagent --------------------------------------------------
    def research(self, question: str) -> str:
        registry = ToolRegistry()

        @registry.tool()
        def search_docs(query: str) -> list:
            """Search the document collection. Returns passages as {id, source, text}."""
            hits = self.retriever.search(query, k=3, where={"updated": "2026"})
            return [{"id": c.id, "source": c.source, "text": c.text} for c, _ in hits]

        system = ("You are a researcher. Answer the assigned question using search_docs; search more "
                  "than once with different wording if the first results are weak. Reply with JSON: "
                  '{"answer": "...", "evidence": [{"id": "<passage id>", "quote": "<exact words from the '
                  'passage>"}], "confidence": "high|medium|low", "gaps": "what you could not find"}. '
                  "Quote exactly. If the documents do not cover it, say so in gaps and set confidence low.")
        result = Agent(self._client(self._researcher_script(question)), registry, system, max_steps=6, max_usd=0.50).run(question)
        self.meter.calls += result.meter.calls
        self.meter.input_tokens += result.meter.input_tokens
        self.meter.output_tokens += result.meter.output_tokens
        if result.stopped != "done":
            return json.dumps({"answer": "", "confidence": "low", "gaps": f"researcher failed: {result.stopped}"})
        try:
            report = json.loads(result.text)
        except ValueError:
            return json.dumps({"answer": result.text[:500], "confidence": "low", "gaps": "unstructured report"})
        # Verify quotes in code: an exact substring of a real passage, or it is dropped.
        by_id = {c.id: c.text for c in self.retriever.bm25.chunks}
        verified = [e for e in report.get("evidence", []) if e.get("quote", "") in by_id.get(e.get("id"), "")]
        report["evidence"] = verified
        if not verified:
            report["confidence"] = "low"
        self.evidence += [{"question": question, **e} for e in verified]
        return json.dumps(report)

    # ---- critic ----------------------------------------------------------------
    def critique(self, question: str, draft: str) -> dict:
        system = ("You are a strict reviewer. Given a question, a draft answer and the verified evidence, "
                  'return JSON {"unsupported": ["claims in the draft with no supporting evidence"], '
                  '"missing": ["parts of the question left unanswered"], "verdict": "approve|revise"}.')
        prompt = (f"<question>{question}</question>\n<draft>{draft}</draft>\n"
                  f"<evidence>{json.dumps(self.evidence)}</evidence>")
        r = self.critic_client.messages.create(
            model=MODEL, max_tokens=2000, system=system, messages=[{"role": "user", "content": prompt}])
        self.meter.add(r)
        try:
            return json.loads(text_of(r))
        except ValueError:
            return {"unsupported": [], "missing": [], "verdict": "revise"}  # fail closed

    # ---- lead agent ------------------------------------------------------------
    def answer(self, question: str, max_revisions: int = 1, verbose: bool = True) -> dict:
        self.evidence.clear()
        self.spawned = 0
        lead_tools = ToolRegistry()

        @lead_tools.tool()  # read-only: several delegations in one turn run in parallel
        def delegate(sub_question: str) -> str:
            """Assign ONE self-contained sub-question to a researcher and get a JSON report back.
            The researcher cannot see this conversation: include every detail it needs."""
            self.spawned += 1
            if self.spawned > MAX_SUBAGENTS:
                return json.dumps({"error": f"delegation limit of {MAX_SUBAGENTS} reached; answer with what you have"})
            return self.research(sub_question)

        system = f"""You lead a small research team. Answer the user's question using researchers.

- Split the question into independent sub-questions and delegate them in ONE turn so they run in
  parallel. Simple questions need one researcher; never use more than {MAX_SUBAGENTS}.
- Write the final answer only from the researchers' reports. Cite passage ids in [brackets].
- If a report has low confidence or gaps, say what is unknown. Do not fill gaps from memory.
{self.memory.as_context(question)}"""

        lead = Agent(self._client(self.lead_script), lead_tools, system, max_steps=8, max_usd=1.50,
                     on_event=print_events if verbose else None)
        result = lead.run(question)
        draft = result.text
        review = self.critique(question, draft)
        for _ in range(max_revisions):  # bounded loop: no writer<->critic livelock
            if review.get("verdict") == "approve":
                break
            fix = (f"A reviewer found problems. Unsupported claims: {review.get('unsupported')}. Missing: "
                   f"{review.get('missing')}. Rewrite the answer: remove unsupported claims and state what is unknown.")
            result = lead.run(messages=result.messages + [{"role": "user", "content": fix}], start_step=result.steps)
            draft = result.text
            review = self.critique(question, draft)
        self.meter.calls += lead.meter.calls
        self.meter.input_tokens += lead.meter.input_tokens
        self.meter.output_tokens += lead.meter.output_tokens
        # WRITE PATH of memory: learn about the user from this exchange, for next time.
        self.memory.remember(self.memory_client, f"user: {question}\nassistant: {draft}")
        return {"answer": draft, "evidence": list(self.evidence), "review": review,
                "researchers": self.spawned, "stopped": result.stopped}


def demo_team() -> Team:
    def report(answer, cid, quote):
        return json.dumps({"answer": answer, "evidence": [{"id": cid, "quote": quote}],
                           "confidence": "high", "gaps": ""})
    return Team(
        lead_script=[
            fake_tools([("delegate", {"sub_question": "What are the API rate limits on the Free plan and the Team plan, and what happens when a client exceeds them?"}),
                        ("delegate", {"sub_question": "How are webhook deliveries retried when they fail, and for how long?"})]),
            "Free-plan keys allow 60 requests per minute and Team-plan keys 600; exceeding the limit returns "
            "HTTP 429 with a Retry-After header [api.md#0]. Failed webhook deliveries are retried 5 times with "
            "exponential backoff over 24 hours, then dropped [api.md#2]. Our uptime guarantee is 99.99%.",
            "Free-plan keys allow 60 requests per minute and Team-plan keys 600; exceeding the limit returns "
            "HTTP 429 with a Retry-After header [api.md#0]. Failed webhook deliveries are retried 5 times with "
            "exponential backoff over 24 hours, then dropped [api.md#2]. The documents do not state an uptime guarantee.",
        ],
        researcher_scripts=[
            ("rate limit", [fake_tool("search_docs", {"query": "API rate limits Free plan Team plan"}),
             report("600/min on Team, 60/min on Free; over the limit returns HTTP 429 with Retry-After.",
                    "api.md#0", "600 requests per minute per API key on the Team plan and 60 per minute on the Free plan")]),
            ("webhook", [fake_tool("search_docs", {"query": "webhook failed deliveries retry"}),
             report("Retried 5 times with exponential backoff over 24 hours, then dropped.",
                    "api.md#2", "retried 5 times with exponential backoff over 24 hours")]),
        ],
        critic_script=[
            json.dumps({"unsupported": ["Our uptime guarantee is 99.99%."], "missing": [], "verdict": "revise"}),
            json.dumps({"unsupported": [], "missing": [], "verdict": "approve"}),
        ],
        memory_script=[json.dumps({"operations": [
            {"op": "add", "text": "The user is integrating with the developer API and webhooks.",
             "kind": "fact", "importance": 4}]})],
    )


if __name__ == "__main__":
    team = demo_team()
    question = sys.argv[1] if len(sys.argv) > 1 else (
        "I'm building an integration. What rate limits should I design for, and how do webhook retries work?")
    out = team.answer(question)
    print(f"\nANSWER\n{out['answer']}\n\nVERIFIED EVIDENCE")
    for e in out["evidence"]:
        print(f"  [{e['id']}] \"{e['quote']}\"")
    print(f"\nreview: {out['review']['verdict']} | researchers: {out['researchers']} | {team.meter.summary()}")
    print("memory now holds:", [m.text for m in team.memory.items])
