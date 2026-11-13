# Module 9: AI system design

**Week 15.** You can build the parts. This module is about combining them into systems, and explaining your choices under questioning, which is what senior interviews and real design reviews test.

It contains seven worked designs, covering every design problem in Arpit Bhayani's syllabus:

| # | Design | Main ideas exercised |
|---|---|---|
| 1 | [Fact-checking agentic system](01-fact-checking-system.md) | Claim decomposition, evidence retrieval, verdicts with citations |
| 2 | [RAG over 10M documents](02-rag-over-10m-docs.md) | Ingestion at scale, hybrid search, ANN, permissions, caching |
| 3 | [Paper-to-code agent](03-paper-to-code-agent.md) | Long-horizon agent, planning, sandboxed execution, verification |
| 4 | [Incident auto-remediation system](04-incident-auto-remediation.md) | Multi-agent, approvals, blast radius, deadlocks |
| 5 | [AI code reviewer](05-ai-code-reviewer.md) | Precision over recall, evals from human feedback |
| 6 | [Self-updating AI docs + externalized platform](06-self-updating-docs-platform.md) | Change-driven pipelines, multi-tenancy, platform APIs |
| 7 | [Natural-language workflow engine](07-nl-workflow-engine.md) | Compile-then-execute, durable execution, cost control |

## How to use these

For each design: **read only the problem statement, set a 40-minute timer, and write your own design first.** Then compare. Reading a solution without attempting one teaches very little.

The FAQ of the course this syllabus comes from recommends implementing the core of each system. Each design ends with a "Build the core" section: a weekend-sized version using the `aikit` pieces you already have.

## A framework for any AI system design

Use it in interviews, in the same order. It takes about 40 minutes.

### 1. Clarify (5 min)

- **Who uses it and for what?** One sentence.
- **What does a wrong output cost?** This sets how much verification and human review you need.
- **Scale:** users, requests per day, corpus size, document size.
- **Latency:** interactive (seconds), or background (minutes to hours)?
- **Freshness:** how quickly must new information appear?
- **Actions:** read-only, or does it change things? Which changes are irreversible?
- **Constraints:** budget, privacy, data residency, existing systems.

### 2. Define success (3 min)

Name the metrics before the architecture: a quality metric (and how it is measured), latency, and cost per request or task. If you cannot say how you would evaluate it, you are not ready to design it.

### 3. Choose the simplest shape that could work (5 min)

Walk the ladder from Module 2: single call → chain → retrieval → tools → agent → multiple agents. Say out loud why you stop where you stop. Interviewers reward "this is a workflow, not an agent, because the steps are known".

### 4. Draw the data flow (10 min)

Separate the **offline path** (ingestion, indexing, precomputation) from the **online path** (per request). Mark for every box: is it code, a model call, or a human?

### 5. Go deep on two or three hard parts (10 min)

The parts specific to this problem: the retrieval strategy, the tool design, the context budget, the approval flow, the state model.

### 6. Failure modes and safety (5 min)

Use the lenses in [Module 8.7](../08-production/README.md#87-brainstorming-production-gotchas-for-a-use-case). Always cover: hallucination, prompt injection, runaway cost, partial failure, and what the human sees when it fails.

### 7. Evaluation and rollout (5 min)

Dataset source, scorers, the CI gate, online monitoring, gradual rollout, and the feedback loop.

### Signals of a strong answer

- Code handles what code can; the model handles judgment.
- Every model output is validated or verified somewhere.
- Numbers: rough token counts, cost per request, latency budget per stage.
- Explicit trade-offs: "I chose X over Y because..., and I would revisit if...".
- An evaluation plan that exists before launch.
- The failure path is designed, not an afterthought.

## Checkpoint

After studying all seven, you should be able to do these in 40 minutes each, unaided:

1. Design a customer-support agent that can look up orders and issue refunds.
2. Design "chat with your codebase" for a 5-million-line monorepo.
3. Design a meeting assistant that joins calls and files action items into a tracker.
4. Design an AI data analyst that answers questions over a company warehouse in SQL.
5. Design a content-moderation pipeline for 100 million posts per day.

Next: [Module 10: Career](../10-career/README.md)
