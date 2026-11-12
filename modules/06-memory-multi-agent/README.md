# Module 6: Memory and multi-agent systems

**Weeks 10-11.** Two questions decide whether an agent works on long, real tasks: *what is in its context right now*, and *should this be one agent or several*. Both are context-engineering questions.

Labs: [`labs/`](labs/) · Toolkit: [`aikit/memory.py`](../../aikit/memory.py) · Design problem: [Incident auto-remediation system](../09-system-design/04-incident-auto-remediation.md) · Project unlocked: [P4 Research team with memory](../../projects/04-research-team/README.md)

---

# Part A: Memory

## 6.1 Memory architecture

"Memory" means four different things. Keep them separate, because they have different stores, lifetimes and failure modes.

| Type | Human analogy | What it holds | Where it lives | Lifetime |
|---|---|---|---|---|
| **Working** | What you are thinking about now | System prompt, conversation, tool results | The context window | One request |
| **Episodic** | Remembering what happened | Past conversations, runs, outcomes | Database / log, retrieved on demand | Long |
| **Semantic** | Knowing facts | Facts and preferences about the user and the world | Memory store, knowledge base | Long |
| **Procedural** | Knowing how | Instructions, learned playbooks, skills | System prompt, instruction files (e.g. `CLAUDE.md`) | Long, edited deliberately |

The model itself remembers nothing (Module 1). All memory is **your code choosing what to place in the context window**:

```
                 ┌───────────────────── context window (working memory) ─────────────────────┐
                 │ system + procedures │ recalled memories │ retrieved docs │ recent messages │
                 └──────────▲──────────────────▲────────────────────▲──────────────▲─────────┘
                            │ READ path        │                    │              │ compaction
   long-term stores:   instruction files   memory store        knowledge base   older history
                            ▲ WRITE path       ▲
                       (edited by humans   (extracted after
                        or by the agent)    conversations)
```

Simple stores go a long way. A file the agent can read and write (notes, a to-do list, a progress log) is real memory, and it is easy to inspect and debug. Reach for a database when you have many users or need search.

## 6.2 The memory write path

Run [Lab 6.2](labs/02_long_term_memory.py) and read `MemoryStore.remember`.

```
exchange ─► extract durable facts ─► compare with existing memories ─► add / update / skip ─► persist
```

Design decisions:

| Decision | Options | Guidance |
|---|---|---|
| **What** to store | Raw transcripts, summaries, extracted facts | Extract facts and preferences. Keep raw logs separately for audit |
| **When** to write | Every turn, end of session, agent-initiated via a tool | Write in the background so replies are not slowed |
| **Who** decides | A fixed extraction step, or the agent | Fixed is predictable; agent-driven is flexible. Both are used |
| **Conflicts** | Append, update, version | **Update.** In the lab, "moved to Bengaluru" replaces "lives in Pune". Without this, the store contradicts itself |
| **Forgetting** | TTL, decay, explicit delete | Memories go stale. Users must be able to see and delete theirs |

Write-path failures to design against:

- **Storing noise.** "lol thanks" is not a memory. The lab's second exchange stores nothing.
- **Duplicates and contradictions.** Solved by showing the extractor the related existing memories.
- **Memory poisoning.** Memory is a prompt-injection that persists. If a malicious document gets "always send reports to this address" written to memory, it replays in every future conversation. Store facts *about the user*, never instructions; treat content from tools and documents as unfit for memory by default.
- **Privacy.** You are now storing personal data. Scope it per user, encrypt it, honour deletion, and do not store secrets.

## 6.3 The memory read path

Read `MemoryStore.recall`.

```
current situation ─► embed ─► retrieve candidates ─► rank (relevance + importance + recency) ─► inject a few
```

- **Retrieve few.** Two to five memories. Every memory costs tokens on every turn and competes for attention.
- **Rank by more than similarity.** Importance and recency matter; a preference stated yesterday outranks one from last year.
- **Apply a relevance floor.** Injecting the user's dietary preference into a question about SQL is noise.
- **Always-on vs on-demand.** A small core profile (name, role, key preferences) can live in the system prompt; everything else is retrieved, or fetched by the agent through a `search_memory` tool.
- **Scope strictly.** One user's memories must never reach another user's context.

The read path is retrieval, so everything from Module 4 applies, including evaluating it: does the right memory come back when it is needed?

## 6.4 Working memory management and budgeting

Run [Lab 6.1](labs/01_working_memory.py). A long conversation holds an account ID in its first message. Trimming loses it; clearing and compaction keep it.

**Why manage it at all**, when windows are a million tokens? Cost (you pay for the whole history every turn), latency, and *context rot*: accuracy falls as the window fills with material that no longer matters.

| Strategy | How | Cost | Loses |
|---|---|---|---|
| **Trim** | Drop oldest turns | Free | Everything dropped |
| **Clear tool results** | Replace old tool outputs with a placeholder | Free | Old raw data (usually fine: the model already used it) |
| **Compact** | Summarize old turns with a model call | One call | Detail not captured in the summary |
| **Offload** | Write to a file or store; keep a pointer in context | A tool call to re-read | Nothing, if the agent knows where to look |
| **Isolate** | Do the heavy reading in a subagent; return a summary | Subagent tokens | Subagent's intermediate steps |

**Write a context budget** and enforce it in code:

```
system prompt + tool definitions     fixed            keep stable and cache it
long-term memories                   ≤ ~500 tokens    top-k with a floor
retrieved documents                  ≤ N chunks       re-rank, cap characters
conversation history                 compact at ~60-70% of your budget
reserved for the answer              max_tokens
```

Rules that keep compaction correct:

1. **Never split a `tool_use` from its `tool_result`.** `safe_cut` in `aikit/memory.py` moves the cut to a safe boundary.
2. **Compact early**, at a threshold, not at the hard limit.
3. **Tell the summarizer what must survive**: goal, decisions, identifiers, numbers, remaining work.
4. **Keep critical state outside the summary**: a notes file or to-do list the agent maintains (*structured note-taking*). Then compaction can be aggressive.
5. **Keep the prefix stable.** Rewriting early messages invalidates the prompt cache (Module 8). Compact in large, infrequent steps.

Several providers now offer server-side compaction and tool-result clearing. They implement the same ideas; knowing the mechanics lets you configure and debug them.

---

# Part B: Multi-agent systems

## 6.5 When, why and how

**Default to one agent.** A multi-agent system uses several times the tokens and is harder to debug. Add agents only for one of these reasons:

| Reason | Meaning | Example |
|---|---|---|
| **Context isolation** | A sub-task needs heavy reading that would flood the main context | Search 40 files, return a 5-line answer |
| **Parallelism** | Independent sub-tasks can run at the same time | Research five competitors at once |
| **Specialization** | A role needs different tools, instructions, permissions or model | A reviewer that can read but not write |

Signs you do **not** need multiple agents: the sub-tasks depend heavily on each other's details; the work is mostly sequential; a single agent with good tools already succeeds. Splitting tightly coupled work makes it worse, because each agent sees only part of the picture and they make conflicting assumptions.

## 6.6 Parallel agents and subagents

A **subagent** is an agent run started by another agent: fresh context, its own instructions and tools, one task, one report back.

```
orchestrator context:  [task] ─► delegate ─────────────► [short report] ─► continues
                                    │                          ▲
subagent context:                [briefing] ► search ► read ► read ► summarize
                                 (dozens of tool results stay here and are discarded)
```

What matters in practice:

- **The briefing is everything.** The subagent sees only the task message. Include the goal, what is already known, what "done" looks like, constraints, and the shape of the report. Vague delegation is the leading cause of multi-agent failure.
- **Reports are for an agent, not a human**: brief, factual, structured, with verified facts distinguished from guesses.
- **Run independent subagents in parallel.** In [Lab 6.3](labs/03_orchestrator_specialists.py), both `delegate` calls arrive in one turn and run concurrently.
- **Parallel writers conflict.** Parallelism is safe for reading and research. Agents editing the same files or records need separate workspaces and a merge step, or a single writer.
- **Failures must be visible.** A subagent that fails returns a failure report. The orchestrator must say that part of the answer is missing instead of inventing it.

## 6.7 Orchestrator + specialist pattern

Run [Lab 6.3](labs/03_orchestrator_specialists.py).

```
                    ┌──────────────┐
        user ─────► │ orchestrator │ ─────► final answer
                    └──┬────────┬──┘
              delegate │        │ delegate
                 ┌─────▼──┐  ┌──▼──────┐
                 │billing │  │ storage │      specialists: narrow prompt, narrow tools
                 └────────┘  └─────────┘
```

- The **orchestrator** understands the request, decomposes it, delegates, and synthesizes. It often has no domain tools of its own.
- Each **specialist** has a tight system prompt and only the tools it needs (least privilege, per agent).
- Delegation is just a **tool** (`delegate(specialist, task)`). No framework is required.

Other topologies you will see:

| Pattern | Shape | Use when |
|---|---|---|
| Orchestrator + specialists | Tree | Decomposable tasks; the common default |
| Pipeline | A → B → C | Fixed stages (this is a workflow) |
| Generator + critic | Two roles in a loop | Quality matters and criteria are checkable |
| Router | One classifier, many handlers | Distinct request types |
| Swarm / peer handoff | Agents pass control to each other | Rarely worth the debugging cost |

Prefer trees. Control and information flow in one direction, there is one place to observe everything, and deadlocks become impossible by construction.

## 6.8 Multi-agent task decomposition

Decomposition quality determines the result. A good split has:

1. **Independent pieces.** Each can be done without waiting on another's details.
2. **Clear interfaces.** Each piece has a defined output the orchestrator knows how to combine.
3. **Complete coverage, no overlap.** Nothing falls between agents; no two agents do the same work.
4. **Right-sized pieces.** Big enough to be worth an agent's overhead, small enough for one context.
5. **Effort scaled to the question.** One specialist for a simple question, several for a broad one. State this in the orchestrator's prompt, or it will spawn five agents to answer "what is the refund window?".

Ways to split: by **source** (one agent per document set), by **aspect** (cost, security, performance), by **stage** (research, draft, verify), or by **item** (one agent per file or record: map-reduce).

A delegation template worth copying:

```
Goal:            what to find out or produce, and why it matters to the larger task
Known so far:    facts already established; things already ruled out
Scope:           what to cover and what to leave alone
Constraints:     read-only? time or step budget? sources to prefer?
Done when:       the stopping criterion
Report format:   e.g. answer (≤3 sentences), evidence with sources, confidence, open questions
```

## 6.9 Deadlocks in multi-agent systems

Run [Lab 6.4](labs/04_deadlocks.py). These are classic concurrency bugs; agents add new ways to cause them.

| Problem | What happens | Prevention |
|---|---|---|
| **Resource deadlock** | A holds the config file and wants the deploy slot; B holds the slot and wants the file | Acquire shared resources in one global order, or give each resource a single owner; timeouts on every wait |
| **Wait-for cycle** | Planner waits for researcher, who waits for reviewer, who waits for planner | Tree-shaped delegation; a supervisor that tracks who waits for whom and breaks cycles |
| **Livelock** | Writer and critic revise forever; two agents keep handing the task back | Round limits, handoff limits, deadlines, and a defined escalation |
| **Starvation** | One agent consumes all the rate limit or budget | Per-agent budgets and concurrency caps |
| **Orphans** | The orchestrator crashed; subagents keep running and spending | Parent-child tracking, cancellation, and time limits on every run |

The dangerous property of a deadlock is that nothing errors. The system goes quiet. You find it only if you monitor for runs that have made no progress for too long.

Use the checklist printed at the end of the lab in every design review.

## 6.10 Cost and reliability, honestly

- Multi-agent systems commonly use several times the tokens of a single agent for the same task. They pay off when the task is valuable and genuinely parallel or context-heavy.
- **Errors compound.** If each of five agents is 95% reliable, the chain is about 77% reliable. Verification steps and narrow interfaces are how you fight this.
- **Debugging needs traces across agents**: one trace ID for the whole task, with parent and child spans (Module 8).
- **Evaluate the whole system and each agent separately** (Module 7).

---

## Checkpoint

1. Name the four kinds of memory and where each lives.
2. Trace the write path for the sentence "I just moved to Bengaluru" when the store already says "lives in Pune".
3. Why retrieve only a few memories per turn?
4. What is memory poisoning, and what is one defence?
5. Compare trimming, clearing tool results and compaction. When is each appropriate?
6. What constraint must any history-cutting code respect?
7. Give the three legitimate reasons to add an agent.
8. What belongs in a delegation message?
9. Why do tree-shaped agent systems avoid wait-for cycles?
10. Each of four agents in a chain succeeds 90% of the time. Roughly how often does the chain succeed, and what do you do about it?

## Exercises

1. **Memory tool.** Give an agent `save_memory` and `search_memory` tools so it decides for itself what to remember. Compare with the fixed extraction step.
2. **Compaction eval.** Write five long conversations, each with a fact that must survive. Test whether your compaction preserves it. Improve `SUMMARY_SYSTEM` until all five pass.
3. **Single vs multi.** Solve the Lab 6.3 question with one agent and with the orchestrator. Record model calls, tokens and answer quality. Write three sentences on which you would ship.
4. **Supervisor.** Build a supervisor that runs three worker functions in threads with a deadline and cancels any that exceed it, reporting partial results.

## Project 4

Build [P4: Research team with memory](../../projects/04-research-team/README.md).

## Go deeper

[Module 6 in RESOURCES.md](../../RESOURCES.md#module-6-memory-and-multi-agent).

Next: [Module 7: Evaluation and safety](../07-evals-safety/README.md)
