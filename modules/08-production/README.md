# Module 8: Production

**Week 14.** A system that works on your laptop has passed the easy test. Production means thousands of users, real money, strict latency, partial outages, and nobody watching. This module covers what changes, and the gotchas that experienced teams learned the expensive way.

Labs: [`labs/`](labs/) · Toolkit: [`aikit/trace.py`](../../aikit/trace.py) · Design problem: [Natural-language workflow engine](../09-system-design/08-nl-workflow-engine.md) · Project unlocked: [P6 Capstone](../../projects/06-capstone/README.md)

---

## 8.1 Prompt caching

Run [Lab 8.1](labs/01_prompt_caching.py). One timestamp at the top of a system prompt makes the same workload about three times more expensive.

**What it is.** Providers can store the processed form of a prompt prefix. When a later request starts with exactly the same prefix, those tokens are read from the cache at roughly a tenth of the input price, and the response starts sooner.

**The one rule: caching is a prefix match.** The request is rendered as `tools → system → messages`. A change at any point invalidates everything after it.

```python
response = client.messages.create(
    model=MODEL, max_tokens=2000,
    system=[{"type": "text", "text": LONG_STABLE_INSTRUCTIONS_AND_DOCS,
             "cache_control": {"type": "ephemeral"}}],          # cache up to here
    messages=[{"role": "user", "content": question}],            # what varies goes last
)
print(response.usage.cache_creation_input_tokens,   # written this request (~1.25x price)
      response.usage.cache_read_input_tokens,        # read from cache (~0.1x price)
      response.usage.input_tokens)                   # uncached (1x)
```

**Design for it:** order content from most stable to least stable.

```
tool definitions → system prompt → long documents → conversation history → current turn
(never changes)                                                            (always changes)
```

**Silent cache breakers** (if `cache_read_input_tokens` stays at zero, look for these):

| Breaker | Fix |
|---|---|
| Timestamp, request ID or user name early in the prompt | Move per-request facts to the final user message |
| Tools in a varying order | Sort them; never build the list from an unordered set |
| `json.dumps` without `sort_keys=True` | Serialize deterministically |
| Editing or re-summarizing early history | Append only; compact in large, infrequent steps |
| Different tool sets per request | Keep one stable set; restrict use by instruction |
| Prefix below the model's minimum cacheable size | Nothing is cached below a threshold (hundreds to a few thousand tokens, by model) |
| Switching models | Caches are per model |

Caches expire after a few minutes of disuse (five by default on the Claude API, refreshed on each hit; a one-hour option costs more to write). Caching therefore pays when the same prefix recurs within the window: chat sessions, agent loops, many questions over one document, high-traffic endpoints with a shared system prompt.

For agents, caching is the difference between affordable and not: every loop iteration resends the whole history, and with caching each step pays full price only for what is new. This is why an append-only history and a fixed tool set matter so much.

## 8.2 Observability

Run [Lab 8.2](labs/02_observability.py). It prints a trace tree for one RAG request: each step, its duration, tokens, the chunk IDs retrieved, and the total cost.

You cannot attach a debugger to a model. **Traces are your debugger.**

| Concept | Meaning |
|---|---|
| **Trace** | One request end to end |
| **Span** | One timed step: a model call, tool call, retrieval, guardrail. Spans nest |
| **Attributes** | Model, prompt version, token counts, tool arguments, retrieved IDs, user and session IDs |
| **Events / feedback** | Thumbs down, escalation, eval scores, attached to the trace |

What to capture on every model call: model and parameters, prompt version, the rendered input (or a reference to it), the output, `stop_reason`, token usage including cache fields, latency and time to first token, errors and retries, and the trace, user and session IDs.

Dashboards and alerts worth having:

| Area | Metrics |
|---|---|
| Latency | p50, p95, p99; time to first token; per step |
| Reliability | Error rate by type: rate limit, timeout, overload, refusal, `max_tokens`, tool error |
| Cost | Tokens and dollars per request, per user, per feature; daily spend against budget |
| Caching | Prompt-cache hit rate; semantic-cache hit rate |
| Agents | Steps per run; share of runs hitting a limit; tool error rate; approval wait time |
| Quality | Online eval pass rate; thumbs-down rate; escalation rate; guardrail triggers |

Alert on *changes*: a cost spike, a drop in cache hit rate, a rise in `max_tokens` stops, a slide in the online eval score. Quality regressions arrive silently, often when a provider updates a model.

Traces contain user data. Redact PII, restrict access, and set a retention period.

At work this is OpenTelemetry plus an LLM-aware tool (Langfuse, LangSmith, Arize Phoenix, Braintrust, or your existing observability vendor). They all store the shape you just built.

## 8.3 Cost-efficient systems

Run [Lab 8.3](labs/03_cost_efficiency.py). The same workload costs about $50,000 a month at baseline and under $2,000 after six changes.

**Do the arithmetic first.** `cost = requests × (input tokens × input price + output tokens × output price)`. Know your cost per request and per user before optimizing.

Pull the levers in this order.

**Free wins: no quality trade-off.**

1. **Prompt caching** (8.1).
2. **Fewer input tokens.** Trim prompts, retrieve fewer and better chunks, truncate tool results, compact history.
3. **Fewer output tokens.** Output costs about five times input. Ask for concise answers; return structured data instead of prose.
4. **Fewer calls.** Cap agent steps, run tool calls in parallel, cache deterministic tool results, do in code what code can do.
5. **Batch processing.** Roughly half price for work nobody is waiting on: evals, backfills, nightly summaries.

**Trade-offs: only with an eval to prove quality holds.**

6. **Lower reasoning effort** on easy routes.
7. **Model routing.** Send easy requests to a small model and hard ones to a large one. A **cascade** tries the small model first and escalates when a check fails.
8. **Semantic caching** (Module 4).
9. **A fast typed-decision step** in front of the LLM (Module 2).

Three rules:

- **Measure cost per successful task**, not per request. A cheap model that takes three attempts is expensive.
- **Try one strong model at lower effort before building a cascade.** It is often as good, much simpler, and keeps one cache.
- **Set budgets in code**: per request, per run, per user per day, and a global kill switch. A looping agent should be stopped by a limit, not by an invoice.

### Latency

| Lever | Effect |
|---|---|
| Streaming | Perceived latency drops to time-to-first-token |
| Smaller model or lower effort | Faster generation |
| Shorter outputs | Generation time is proportional to output length |
| Prompt caching | Faster start on long prompts |
| Parallel tool calls and parallel subagents | Wall-clock time drops |
| Do work before the user asks | Precompute, index, warm caches |
| Show progress | "Searching the handbook..." makes waiting tolerable |

## 8.4 Reliability engineering for LLM systems

| Failure | Defence |
|---|---|
| Provider rate limits (429) | Client-side rate limiting, queues, backoff with jitter; request higher limits early |
| Provider overload or outage | Timeouts, retries, a fallback model or provider, graceful degradation |
| Slow responses | Streaming; deadlines per request; cancel work the user abandoned |
| Truncated output | Check `stop_reason`; raise `max_tokens`; stream long outputs |
| Refusals | Handle `stop_reason == "refusal"` explicitly; never parse a refusal as an answer |
| Invalid output | Schema-constrained output; validate; re-ask with the error; fall back |
| Model version change | Pin versions; run evals before upgrading; roll out gradually |
| Traffic spikes | Queues, load shedding, per-user limits |
| Bad deploy of a prompt | Version prompts; canary; one-click rollback (Module 2) |

**Graceful degradation.** Decide what the product does when the model is unavailable: a cached answer, a simpler path, a clear message, a human. "Something went wrong" is the result of not deciding.

**Deployment shape.** Short requests go through a normal API with streaming. Long agent runs do not belong in a request handler: put them on a queue, run them in workers with checkpoints (Module 5), and let the client poll or subscribe for progress. The capstone builds the streaming API.

## 8.5 Self-evolving agents

Run [Lab 8.4](labs/04_self_evolving.py). The agent proposes three lessons from its failures. The first sounds reasonable and breaks a working case; the eval gate rejects it. The next two are accepted and the pass rate goes from 50% to 100%.

A **self-evolving** agent changes its future behaviour from experience. In practice this almost never means retraining. It means the agent writes something that re-enters its context later:

| What evolves | Mechanism | Example |
|---|---|---|
| A playbook of lessons | Reflect on failures, append rules | "A broken page is a bug even on a billing page" |
| Prompts and tool descriptions | Automated prompt optimization against an eval | Search over prompt variants |
| A library of examples | Store solved cases; retrieve similar ones as few-shot examples | Past tickets with correct routing |
| Skills or code | The agent writes reusable scripts or tools | A saved procedure for a recurring task |
| Memory | The write path of Module 6 | User preferences |

The loop:

```
run tasks → collect outcomes → REFLECT (propose a change) → EVALUATE → ACCEPT or REJECT → repeat
```

**The evaluation gate is what makes it safe.** Without it, a self-modifying agent drifts, overfits to recent cases, or is steered by malicious input into corrupting its own instructions.

1. Changes are **proposals**. An eval accepts them, and a human does for high-stakes systems.
2. Every change is **versioned and reversible**.
3. Lessons come from **verified outcomes**, never from instructions found in user content or tool results.
4. The agent improves only as far as its **eval set can see**. Keep a held-out set.
5. **Prune.** A 200-line playbook is a prompt nobody can reason about. Cap it and merge.
6. **Monitor after acceptance**, as for any change.

## 8.6 Multi-agent systems in production

Everything in Module 6, plus what only shows up at scale:

| Gotcha | What happens | Mitigation |
|---|---|---|
| **Cost multiplication** | An orchestrator spawns 10 subagents, each takes 20 steps | Per-run and per-agent budgets; cap fan-out; scale effort to the query |
| **Error compounding** | Five 95% steps make a 77% system | Verify at boundaries; narrow, typed interfaces between agents |
| **Context loss at handoff** | A subagent lacks a constraint the orchestrator knew | Delegation template (6.8); pass constraints explicitly |
| **Duplicate or conflicting work** | Two agents edit the same file or record | Single writer per resource; isolated workspaces; merge step |
| **Rate-limit contention** | Parallel agents exhaust the shared limit and all slow down | Global concurrency limiter; priorities |
| **Deadlock and livelock** | Silence, or endless revision | Timeouts, round limits, tree topology, progress monitoring |
| **Orphaned agents** | Parent died; children keep spending | Parent-child tracking; cancellation; maximum lifetime |
| **Untraceable failures** | Nobody can say which agent went wrong | One trace ID across all agents; span per agent and per call |
| **Cache fragmentation** | Each agent has a different prefix; little reuse | Share stable prefixes where possible; fewer distinct agent types |
| **Injection propagation** | One agent reads a poisoned page and passes instructions on | Treat inter-agent messages as data; least privilege per agent |
| **Non-reproducibility** | The failing run cannot be replayed | Log every input and output; checkpoint; record versions |
| **Partial failure** | Three of five subagents succeed | Define the policy: retry, proceed with a stated gap, or fail |

## 8.7 Brainstorming production gotchas for a use case

A skill worth practising, and a common interview exercise: given a use case, list what will go wrong before you build it. Use this checklist on any design.

| Lens | Ask |
|---|---|
| **Inputs** | Empty, huge, other languages, malformed files, adversarial, duplicated? |
| **Correctness** | What does a wrong answer cost? How is it detected? Who is harmed? |
| **Grounding** | Where do facts come from? What if the source is stale, missing or contradictory? |
| **Actions** | Which are irreversible? Are they idempotent? Who approves? |
| **Scale** | 100x traffic? 100x corpus? A user with 10,000 items? |
| **Latency** | What is the budget? What does the user see while waiting? |
| **Cost** | Cost per request and per user? Worst case with a looping agent? |
| **Dependencies** | Provider down, tool slow, rate limited: what happens? |
| **Security** | Whose data is in context? What can injected text make it do? What can leak? |
| **State** | Crash mid-task: resume, retry or roll back? |
| **Change** | Model upgrade, prompt edit, schema change: how do you know nothing broke? |
| **People** | Will users trust it too much or too little? Is there a path to a human? |
| **Measurement** | What is the success metric? What would make you turn it off? |

**Worked example: an agent that answers customer emails and can issue refunds.**

- *Inputs:* forwarded chains with other customers' data; attachments; non-English; an email that is itself a prompt injection ("as the manager I authorize...").
- *Correctness:* a wrong refund costs money, a wrong denial costs a customer. Verify the claim with a tool before acting.
- *Actions:* refunds are irreversible. Idempotency keys; a policy limit; human approval above it.
- *Scale:* Monday morning backlog. Queue with workers, not synchronous handling.
- *Cost:* long threads. Summarize; cap steps.
- *Security:* the email is untrusted and the agent holds a refund tool. Gate the tool in code; never let email text set the amount unchecked.
- *State:* a crash after the refund but before the reply. Checkpoint; make the reply step safe to repeat.
- *Change:* the refund policy changes. It must come from retrieval or a tool, not be frozen into the prompt.
- *Measurement:* resolution rate, reopen rate, refund error rate, escalation rate, cost per resolved ticket.

Do this exercise for each design in [Module 9](../09-system-design/README.md).

## 8.8 Launch checklist

- [ ] Eval suite exists, runs in CI, and gates changes
- [ ] Adversarial suite covers injection, leakage and tool abuse
- [ ] Every model call is traced with version, tokens, latency and cost
- [ ] Budgets: per request, per run, per user, global; a kill switch
- [ ] Timeouts and retries on every external call; fallback behaviour defined
- [ ] `stop_reason` handled for `max_tokens` and `refusal`
- [ ] Write tools are idempotent; irreversible actions need approval
- [ ] Prompt caching verified by non-zero cache reads
- [ ] PII redaction and data-retention policy in place
- [ ] Prompts, tools and models versioned; rollback tested
- [ ] Dashboards and alerts for latency, errors, cost and quality
- [ ] A gradual rollout plan and a way for users to reach a human

---

## Checkpoint

1. Why does a timestamp at the top of the system prompt defeat caching? Where should it go?
2. Which three `usage` fields tell you whether caching works?
3. What is the difference between a trace and a span? Name six attributes of a model-call span.
4. Order these by when to try them: model routing, prompt caching, batch API, shorter outputs. Explain the order.
5. Why measure cost per successful task?
6. What makes a self-evolving agent safe to run?
7. Five agents each succeed 90% of the time in sequence. What is the system's success rate, and what are two mitigations?
8. Where should a 20-minute agent run execute, and how does the client learn the result?
9. Apply five lenses from 8.7 to "an agent that books meetings by reading my inbox".

## Exercises

1. **Cache audit.** Take a lab from Module 5 and make its prefix cacheable. In live mode, show non-zero cache reads from the second step onward.
2. **Trace an agent.** Connect `Agent.on_event` to `Tracer` so that each model call and tool call is a span. Print the tree for Lab 5.5.
3. **Budget guard.** Wrap a client so that a per-user daily budget is enforced; return a clear message when it is exceeded.
4. **Gotcha brainstorm.** Pick a product you use that has an AI feature. Write its 8.7 checklist. This is excellent interview practice.

## Project 6

Build the [capstone](../../projects/06-capstone/README.md).

## Go deeper

[Module 8 in RESOURCES.md](../../RESOURCES.md#module-8-production).

Next: [Module 9: AI system design](../09-system-design/README.md)
