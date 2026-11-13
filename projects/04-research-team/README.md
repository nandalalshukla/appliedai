# Project 4: Research team with memory

**After Module 6 · 12-15 hours · Skills: orchestration, subagents, delegation, parallelism, evidence verification, a critic loop, long-term memory**

## What you will build

A multi-agent research assistant:

```
question ─► LEAD ──delegate──► RESEARCHER 1 ─┐   (parallel, separate contexts,
              │   ──delegate──► RESEARCHER 2 ─┤    each returns a short JSON report)
              │ ◄──── reports ────────────────┘
              ▼
            draft ─► CRITIC (checks the draft against verified evidence) ─► revise once if needed
              ▼
            answer with citations ─► MEMORY write path (what to remember about this user)
```

On a second question from the same user, recalled memories shape the answer.

The project has you make the decisions that matter in multi-agent work: how to split a question, what a delegation message must contain, what a subagent returns, how to stop loops, and how to keep costs bounded. You will also measure whether the extra agents were worth it.

## Before you start

- Finish Module 6 and its labs, especially [6.2](../../modules/06-memory-multi-agent/labs/02_long_term_memory.py) and [6.3](../../modules/06-memory-multi-agent/labs/03_orchestrator_specialists.py).
- Working file: `projects/04-research-team/my_research.py`.
- Corpus: `data/handbook/` to start; your own documents later.

---

## Step 1: Build one researcher

**Goal:** a subagent that answers one question from the documents and returns structured evidence.

**Do:** write `research(question) -> str`. Inside, create a `ToolRegistry` with one tool, `search_docs(query)`, returning passages as `{id, source, text}`. Run an `Agent` with a system prompt that requires a JSON report:

```json
{"answer": "...", "evidence": [{"id": "api.md#0", "quote": "exact words"}],
 "confidence": "high|medium|low", "gaps": "what could not be found"}
```

Give it `max_steps=6` and a small `max_usd`.

**Check:** `research("What are the API rate limits?")` returns JSON with a quote. In mock mode, script two turns: a `search_docs` call, then the report.

**If it fails:** if `json.loads` fails on the final text, handle it: return a low-confidence report instead of crashing.

## Step 2: Verify quotes in code

**Goal:** no fabricated evidence leaves the researcher.

**Do:** before returning, keep only evidence items whose `quote` is an exact substring of the passage with that `id`. If none survive, set `confidence` to `low`. Append verified items to a team-level `evidence` list.

**Check:** script a researcher that returns one real quote and one invented quote. Only the real one survives.

> This is the cheapest and strongest anti-hallucination measure in the project. It needs no model call.

## Step 3: Handle researcher failure

**Do:** if the researcher stops for any reason other than `done`, return a JSON report with empty answer, `low` confidence and the reason in `gaps`.

**Check:** set `max_steps=1`. The lead still receives a well-formed report saying the researcher failed.

## Step 4: Build the lead with a `delegate` tool

**Goal:** an orchestrator whose only tool is delegation.

**Do:** create the lead's registry with `delegate(sub_question)`, which calls `research`. Leave it read-only so that several delegations in one turn run in parallel. Write the lead's system prompt:

- split into independent sub-questions and delegate them in one turn
- scale effort: one researcher for a simple question, never more than four
- each sub-question must be self-contained, because the researcher sees nothing else
- write the answer only from the reports, citing passage IDs
- state what is unknown when a report has gaps

**Check:** a two-part question produces two `delegate` calls in the same step. Look at the trace.

**Check 2 (live mode):** read the sub-questions the lead wrote. Could a stranger answer each one without seeing the original question? If not, strengthen the delegation rule.

## Step 5: Cap the fan-out

**Do:** count delegations per question. Beyond `MAX_SUBAGENTS`, `delegate` returns an error telling the lead to answer with what it has.

**Check:** set the cap to 1 and ask a three-part question. The lead answers the part it could research and names what is missing.

## Step 6: Add a critic

**Goal:** an independent check of the draft against the evidence.

**Do:** write `critique(question, draft) -> dict` as a single model call (not an agent) that sees the question, the draft and the **verified evidence list**, and returns `{"unsupported": [...], "missing": [...], "verdict": "approve|revise"}`. On a parse error return `revise` (fail closed).

**Check:** script a draft containing a claim with no evidence ("Our uptime guarantee is 99.99%"). The critic lists it.

## Step 7: One bounded revision

**Do:** if the verdict is `revise`, send the critic's findings back to the lead as a user message, continuing the same conversation, and get a new draft. Allow at most `max_revisions` rounds (start with 1), then return the best draft with the review attached.

**Check:** the unsupported sentence is gone from the final answer, replaced by a statement of what is unknown.

**Check 2:** make the critic always say `revise`. The loop must still end. This is the livelock from Lab 6.4.

## Step 8: Add long-term memory

**Do:**

- Read path: put `memory.as_context(question)` into the lead's system prompt.
- Write path: after answering, call `memory.remember(client, exchange)`.
- Store the memory file per user (for example `memory/<user_id>.jsonl`).

**Check:** ask a question that reveals something durable ("I'm building an integration with your API"). Then, with a new `Team` object using the same memory file, ask "what should I watch out for?". The recalled memory appears in the lead's system prompt.

**If it fails:** print `team.memory.items` after the first question. If it is empty, your write path did not run or the extraction returned no operations.

## Step 9: Account for cost

**Do:** aggregate token usage across the lead, every researcher and the critic into one `CostMeter`. Return the number of researchers spawned with every answer.

**Check:** you can state: "this answer used N model calls across M agents and cost about $X".

## Step 10: Is multi-agent worth it here?

**Goal:** make the decision with data.

**Do:** build a single-agent baseline: one `Agent` with the `search_docs` tool and the same answer rules. Write eight questions (three simple, three two-part, two unanswerable). Run both systems and record for each: correct? grounded? model calls, tokens.

**Check:** a table with two rows per question. Write five sentences: where did the team win, where did it only cost more, and which would you ship for which kind of question?

> The honest outcome of this step is often "single agent for most questions, team for broad ones". Being able to show that is worth more than the team itself.

---

## Done when

- [ ] Researchers return structured reports with quotes verified in code
- [ ] The lead delegates independent sub-questions in parallel, with a fan-out cap
- [ ] Researcher failures surface as reports, never as silence
- [ ] A critic checks the draft against verified evidence; revision is bounded
- [ ] Memory is written after a session and recalled in the next
- [ ] Total cost is reported per answer
- [ ] A written comparison against a single-agent baseline

## Compare with the reference

[`solution/research.py`](solution/research.py): `python projects/04-research-team/solution/research.py`

## Stretch goals

1. **Deadlines.** Give each researcher a wall-clock deadline; the lead proceeds with the reports that arrived.
2. **Specialists.** Replace generic researchers with specialists that have different corpora or tools, plus a web-search specialist.
3. **Tracing.** One trace for the whole question with a span per agent, using `aikit.trace`.
4. **Memory hygiene.** Add `forget`, a relevance floor on recall, and a test that an injected instruction in a document never becomes a memory.
5. **Cheaper workers.** Run researchers on a small model and the lead on a large one. Re-run Step 10.

## How to talk about this in an interview

"I built an orchestrator with parallel research subagents, a critic, and long-term memory. Two things made it reliable: researchers return quotes that are verified as exact substrings in code, and every loop between agents is bounded. I also compared it with a single-agent baseline, and found the team only paid off on multi-part questions, so I would route by question type."
