"""Lab 6.3 - Orchestrator + specialists, running subagents in parallel.

One agent with one context does most jobs. You add agents for three reasons:
  1. CONTEXT   a sub-task needs lots of reading that would flood the main context
  2. PARALLEL  independent sub-tasks can run at the same time
  3. SPECIALISM different tools, instructions or model per role

Pattern: an ORCHESTRATOR splits the work and calls SPECIALISTS through a
`delegate` tool. Each specialist is a fresh Agent with its own context; only
its short report comes back.

Run:  python modules/06-memory-multi-agent/labs/03_orchestrator_specialists.py
"""

from typing import Literal

from aikit import FakeClient, fake_tool, fake_tools, get_client, mock_mode
from aikit.agent import Agent, print_events
from aikit.rag import HybridRetriever, load_corpus
from aikit.tools import ToolRegistry

retriever = HybridRetriever(load_corpus("data/handbook"))
usage = {"subagent_calls": 0, "subagent_tokens": 0}

# ---- specialists: narrow instructions, narrow tools --------------------------

def make_specialist(role: str, product: str, script: list) -> Agent:
    registry = ToolRegistry()

    @registry.tool()
    def search_handbook(query: str) -> list:
        """Search this team's section of the company handbook. Returns matching passages."""
        return [c.text for c, _ in retriever.search(query, k=2, where={"product": product, "updated": "2026"})]

    system = (
        f"You are the {role} specialist. Answer the assigned question using search_handbook. "
        "Reply with a short factual report (at most 3 sentences) including exact numbers. "
        "If the handbook does not cover it, say so. Your report is read by another agent, not a human."
    )
    client = FakeClient(script=script) if mock_mode() else get_client()
    return Agent(client, registry, system, max_steps=6)


SPECIALIST_SCRIPTS = {
    "billing": [fake_tool("search_handbook", {"query": "plan downgrade Team to Free"}),
                "Downgrades take effect at the end of the billing cycle. Moving from Team to Free "
                "deletes shared workspaces after a 30 day grace period."],
    "storage": [fake_tool("search_handbook", {"query": "storage limits Free plan"}),
                "The Free plan includes 5 GB of storage (Team has 1 TB per workspace). Over-quota "
                "workspaces get error STG-507 and uploads fail until files are removed."],
}

# ---- orchestrator: one tool, `delegate` --------------------------------------

orchestrator_tools = ToolRegistry()


@orchestrator_tools.tool()  # read_only -> several delegate calls in one turn run in PARALLEL
def delegate(specialist: Literal["billing", "storage"], task: str) -> str:
    """Hand a self-contained question to a specialist agent and get back its short report.

    The specialist knows nothing about the conversation: put everything it needs in `task`.
    billing: plans, charges, refunds, invoices. storage: quotas, files, regions, storage errors.
    """
    agent = make_specialist(specialist, specialist, list(SPECIALIST_SCRIPTS[specialist]))
    result = agent.run(task)
    usage["subagent_calls"] += result.meter.calls
    usage["subagent_tokens"] += result.meter.input_tokens + result.meter.output_tokens
    if result.stopped != "done":
        return f"[{specialist} specialist failed: {result.stopped}]"  # failures are reported, not hidden
    return result.text


ORCHESTRATOR_SYSTEM = """You coordinate specialists to answer customer questions.

- Break the question into independent parts and delegate each to the right specialist.
  Delegate independent parts in the same turn so they run in parallel.
- Each task you write must stand alone: the specialist cannot see this conversation.
- Then combine the reports into one clear answer. Use only what the reports say.
- For a simple question in one area, delegate once. Do not over-split."""

client = get_client(script=[
    fake_tools([
        ("delegate", {"specialist": "billing", "task": "What happens to a customer's account and data when they downgrade from the Team plan to the Free plan, and when does it take effect?"}),
        ("delegate", {"specialist": "storage", "task": "What is the storage limit on the Free plan, and what happens if a workspace holds more than that limit?"}),
    ]),
    "If you downgrade from Team to Free, the change applies at the end of your billing cycle, and "
    "shared workspaces are deleted after a 30 day grace period. The Free plan allows 5 GB (Team "
    "allows 1 TB), so with 40 GB stored you would be over quota: uploads fail with error STG-507 "
    "until you remove files. Export or trim your data before downgrading.",
])

if __name__ == "__main__":
    orchestrator = Agent(client, orchestrator_tools, ORCHESTRATOR_SYSTEM, max_steps=6, on_event=print_events)
    result = orchestrator.run("I have 40 GB of files on the Team plan. What happens if I downgrade to Free?")
    print("\nANSWER:", result.text)
    print(f"\norchestrator: {result.meter.calls} model calls | specialists: {usage['subagent_calls']} model calls")

# What to notice:
# - Context isolation: each specialist read handbook passages; the orchestrator
#   saw only two 2-sentence reports. Its context stays small.
# - The delegation message is the specialist's ENTIRE briefing. Vague tasks
#   ("look into storage") are the top cause of multi-agent failure.
# - Cost: 2 orchestrator calls + 4 specialist calls. A single agent with one
#   search tool would have used about 3. Multi-agent buys isolation and
#   parallelism, and you pay for it in tokens.
#
# Try it:
# 1. Solve the same question with ONE agent holding the search tool. Compare
#    model calls and answer quality. When is the single agent the right call?
# 2. Make the storage specialist fail (max_steps=1). Does the orchestrator
#    tell the user part of the answer is missing?
# 3. Add an output contract: specialists return JSON {answer, confidence, sources}.
