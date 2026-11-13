# Syllabus

**16 weeks at 8-10 hours a week.** Each week lists what to read, which labs to run, and what you should have at the end. If you have less time, stretch the calendar and keep the order.

| Phase | Weeks | Modules | Outcome |
|---|---|---|---|
| Foundations | 0-2 | 0, 1 | You understand what a model does and can call one with control over cost and errors |
| Core building blocks | 3-7 | 2, 3, 4 | You can prompt reliably, build tools, and build retrieval that you can measure |
| Agents | 8-11 | 5, 6 | You can build single agents and multi-agent systems, with memory and safety rails |
| Engineering discipline | 12-14 | 7, 8 | You can evaluate, secure, observe and pay for what you build |
| Design and career | 15-16 | 9, 10 | You can design systems on a whiteboard and present your work |

---

## Week by week

### Week 0: Setup
- **Read:** [Module 0](modules/00-setup/README.md)
- **Do:** install, run the tests, run the first lab; get an API key if you can
- **You have:** a working environment

### Week 1: How LLMs behave
- **Read:** [Module 1](modules/01-foundations/README.md), sections 1.1-1.5
- **Labs:** 1.1 tokens, 1.2 sampling, 1.3 first call
- **Watch:** Karpathy, "Intro to Large Language Models"
- **You have:** a mental model that predicts failures before you see them

### Week 2: The API in depth
- **Read:** Module 1, sections 1.5-1.9
- **Labs:** 1.4 chat loop, 1.5 streaming, 1.6 embeddings
- **Exercises:** the robust caller with retries; the history trimmer
- **You have:** a chatbot, an embedding search, and retry logic you wrote yourself

### Week 3: Reliable prompts
- **Read:** [Module 2](modules/02-prompting/README.md), sections 2.1-2.4
- **Labs:** 2.1 anatomy, 2.2 few-shot and reasoning, 2.3 structured outputs
- **You have:** extractors that return validated, typed data

### Week 4: Failure modes and prompt infrastructure
- **Read:** Module 2, sections 2.5-2.7
- **Labs:** 2.4 failure modes, 2.5 prompt registry, 2.6 System One gate
- **Design:** [Fact-checking system](modules/09-system-design/01-fact-checking-system.md) (attempt it first)
- **Project:** [P1 Support triage](projects/01-support-triage/README.md)
- **You have:** your first portfolio project, with an accuracy table

### Week 5: Tool use
- **Read:** [Module 3](modules/03-tool-use/README.md)
- **Labs:** 3.1 one call by hand, 3.2 registry, 3.3 tool loop
- **Exercises:** safe calculator, idempotent write, loop detector
- **You have:** a tool layer that survives bad input

### Week 6: Retrieval
- **Read:** [Module 4](modules/04-rag/README.md), sections 4.1-4.4
- **Labs:** 4.1 naive RAG, 4.2 hybrid search, 4.3 re-ranking, 4.6 retrieval eval
- **You have:** a retrieval system with recall and MRR numbers

### Week 7: RAG that holds up
- **Read:** Module 4, sections 4.5-4.9
- **Labs:** 4.4 query rewriting, 4.5 semantic cache
- **Design:** [RAG over 10M documents](modules/09-system-design/02-rag-over-10m-docs.md)
- **Project:** [P2 Ask My Docs](projects/02-ask-my-docs/README.md)
- **You have:** a cited Q&A system over your own documents

### Week 8: Agent loops
- **Read:** [Module 5](modules/05-agents/README.md), sections 5.1-5.4
- **Labs:** 5.1 agent loop, 5.2 ReAct from scratch
- **You have:** an agent with step, budget and loop limits

### Week 9: Agents you can trust
- **Read:** Module 5, sections 5.5-5.8
- **Labs:** 5.3 checkpoint and resume, 5.4 human in the loop, 5.5 mini coding agent
- **Design:** [Paper-to-code agent](modules/09-system-design/03-paper-to-code-agent.md)
- **Project:** [P3 Coding agent](projects/03-coding-agent/README.md) (start)
- **You have:** an agent that survives crashes and asks before risky actions

### Week 10: Memory
- **Read:** [Module 6](modules/06-memory-multi-agent/README.md), Part A
- **Labs:** 6.1 working memory, 6.2 long-term memory
- **Project:** finish P3
- **You have:** a coding agent in your portfolio; a memory store with write and read paths

### Week 11: Multi-agent systems
- **Read:** Module 6, Part B
- **Labs:** 6.3 orchestrator and specialists, 6.4 deadlocks
- **Design:** [Incident auto-remediation](modules/09-system-design/04-incident-auto-remediation.md)
- **Project:** [P4 Research team](projects/04-research-team/README.md)
- **You have:** a multi-agent system, and data on whether it beat a single agent

### Week 12: Evals
- **Read:** [Module 7](modules/07-evals-safety/README.md), sections 7.1-7.4
- **Labs:** 7.1 first eval, 7.2 LLM judge
- **Exercise:** error analysis on 30 outputs
- **You have:** an eval suite with a regression gate

### Week 13: Adversarial evals and safety
- **Read:** Module 7, sections 7.5-7.6
- **Labs:** 7.3 adversarial suite
- **Designs:** [AI code reviewer](modules/09-system-design/05-ai-code-reviewer.md), [Self-updating docs platform](modules/09-system-design/06-self-updating-docs-platform.md)
- **Project:** [P5 Eval harness](projects/05-eval-harness/README.md)
- **You have:** evals running in CI on every push

### Week 14: Production
- **Read:** [Module 8](modules/08-production/README.md)
- **Labs:** 8.1 prompt caching, 8.2 observability, 8.3 cost, 8.4 self-evolving agents
- **Design:** [Natural-language workflow engine](modules/09-system-design/07-nl-workflow-engine.md)
- **Project:** [P6 Capstone](projects/06-capstone/README.md) (start)
- **You have:** a traced, budgeted, cached service running locally

### Week 15: System design
- **Read:** [Module 9](modules/09-system-design/README.md); revisit all seven designs
- **Do:** the five practice prompts, 40 minutes each, unaided
- **Project:** finish and deploy the capstone
- **You have:** a deployed capstone and a repeatable design method

### Week 16: Career
- **Read:** [Module 10](modules/10-career/README.md)
- **Do:** polish three project READMEs, write one post, do two mock interviews, start applying
- **You have:** a portfolio, a CV, and an interview plan

---

## Assessment: how to know you are ready

There is no certificate. There is this checklist, which is harder to fake:

- [ ] All module checkpoint questions answered without notes
- [ ] Six projects built, each with an eval and numbers in its README
- [ ] The capstone deployed at a public URL
- [ ] Seven designs attempted before reading the worked versions
- [ ] One project uses your own data or solves your own problem
- [ ] You can explain, for any project: what fails, how you know, and what it costs

---

## Mapping to Arpit Bhayani's Applied AI syllabus

Every topic listed on the [Applied AI course page](https://arpitbhayani.me/applied-ai/) is covered. Topic names below are his; the right-hand column is where this course teaches it.

### Week 1 - Session 1: Prompt LLMs Reliably

| His topic | Covered in |
|---|---|
| Mental Model While Building Around LLMs | [Module 1.2](modules/01-foundations/README.md#12-the-mental-model-a-next-token-predictor), [Module 2.1](modules/02-prompting/README.md#21-the-mental-model-for-building-around-llms) |
| Chain-of-Thought Prompting and Few-shot Prompting | [Module 2.3](modules/02-prompting/README.md#23-few-shot-prompting-and-chain-of-thought), Lab 2.2 |
| Gotchas Using Structured Outputs | [Module 2.4](modules/02-prompting/README.md#24-structured-outputs-and-their-gotchas), Lab 2.3 |
| Prompt Failure Modes | [Module 2.5](modules/02-prompting/README.md#25-prompt-failure-modes), Lab 2.4 |
| Drafting Reliable Prompts | [Module 2.2](modules/02-prompting/README.md#22-drafting-reliable-prompts), Lab 2.1 |
| Infrastructure Around Prompts | [Module 2.6](modules/02-prompting/README.md#26-infrastructure-around-prompts), Lab 2.5 |
| System One Models - Jev and Clairic | [Module 2.7](modules/02-prompting/README.md#27-system-one-models-jev-and-clairic), Lab 2.6 |
| Prototypes and Demos | Labs 2.1-2.6, Project 1 |
| Design: Fact Checking Agentic System | [Design 1](modules/09-system-design/01-fact-checking-system.md) |

### Week 1 - Session 2: Tool Use and RAG

| His topic | Covered in |
|---|---|
| Tool Use and Tool Schema Design | [Module 3.1-3.2](modules/03-tool-use/README.md#32-tool-schema-design), Lab 3.1 |
| Tool Infrastructure | [Module 3.3](modules/03-tool-use/README.md#33-tool-infrastructure), Lab 3.2, `aikit/tools.py` |
| Tool Use Production Gotchas | [Module 3.5](modules/03-tool-use/README.md#35-production-gotchas), Lab 3.3 |
| Hybrid Search and Metadata Filtering | [Module 4.3](modules/04-rag/README.md#43-hybrid-search-and-metadata-filtering), Lab 4.2 |
| Re-ranking - Cross Encoders and Bi-encoders | [Module 4.4](modules/04-rag/README.md#44-re-ranking-bi-encoders-and-cross-encoders), Lab 4.3 |
| Query Rewriting | [Module 4.5](modules/04-rag/README.md#45-query-rewriting), Lab 4.4 |
| Semantic Caching | [Module 4.8](modules/04-rag/README.md#48-semantic-caching), Lab 4.5 |
| Prototypes and Demonstrations | Labs 3.1-3.3 and 4.1-4.6, Project 2 |
| Design: RAG over 10M docs | [Design 2](modules/09-system-design/02-rag-over-10m-docs.md) |

### Week 2 - Session 1: Single Agent Loops and Systems

| His topic | Covered in |
|---|---|
| Anatomy of an Agent | [Module 5.2](modules/05-agents/README.md#52-anatomy-of-an-agent), Lab 5.1 |
| Observe-Think-Act Loop | [Module 5.3](modules/05-agents/README.md#53-the-observe-think-act-loop), `aikit/agent.py` |
| ReAct Loop | [Module 5.4](modules/05-agents/README.md#54-the-react-loop), Lab 5.2 |
| Checkpoint and Resume | [Module 5.5](modules/05-agents/README.md#55-checkpoint-and-resume), Lab 5.3 |
| Human in the Loop | [Module 5.6](modules/05-agents/README.md#56-human-in-the-loop), Lab 5.4 |
| How Claude Code Works | [Module 5.7](modules/05-agents/README.md#57-how-claude-code-works), Lab 5.5 |
| Prototypes and Demonstrations | Labs 5.1-5.5, Project 3 |
| Design: Paper to Code Agent | [Design 3](modules/09-system-design/03-paper-to-code-agent.md) |

### Week 2 - Session 2: Multi-Agent Systems and Memory

| His topic | Covered in |
|---|---|
| Memory Architecture | [Module 6.1](modules/06-memory-multi-agent/README.md#61-memory-architecture) |
| Memory Write and Read Path | [Module 6.2-6.3](modules/06-memory-multi-agent/README.md#62-the-memory-write-path), Lab 6.2, `aikit/memory.py` |
| Working Memory Management and Budgeting | [Module 6.4](modules/06-memory-multi-agent/README.md#64-working-memory-management-and-budgeting), Lab 6.1 |
| When, Why, and How - Multi-agent | [Module 6.5](modules/06-memory-multi-agent/README.md#65-when-why-and-how) |
| Parallel Agents and Subagents | [Module 6.6](modules/06-memory-multi-agent/README.md#66-parallel-agents-and-subagents), Lab 6.3 |
| Orchestrator + Specialist Pattern | [Module 6.7](modules/06-memory-multi-agent/README.md#67-orchestrator--specialist-pattern), Lab 6.3 |
| Multi-agent Task Decomposition | [Module 6.8](modules/06-memory-multi-agent/README.md#68-multi-agent-task-decomposition) |
| Deadlocks in Multi-agent Systems | [Module 6.9](modules/06-memory-multi-agent/README.md#69-deadlocks-in-multi-agent-systems), Lab 6.4 |
| Prototypes and Demonstrations | Labs 6.1-6.4, Project 4 |
| Design: Incident Auto-remediation System | [Design 4](modules/09-system-design/04-incident-auto-remediation.md) |

### Week 3 - Session 1: Evaluation, Safety, and Systems

| His topic | Covered in |
|---|---|
| Why Evals and Good Evals | [Module 7.1](modules/07-evals-safety/README.md#71-why-evals) |
| Scoring Methods and Pitfalls | [Module 7.3](modules/07-evals-safety/README.md#73-scoring-methods-and-pitfalls), Lab 7.2 |
| Placing and Plugging Evals | [Module 7.4](modules/07-evals-safety/README.md#74-placing-and-plugging-evals), Lab 7.1, Project 5 |
| Building an Eval Dataset | [Module 7.2](modules/07-evals-safety/README.md#72-building-an-eval-dataset) |
| Exploratory and Adversarial Evals | [Module 7.5-7.6](modules/07-evals-safety/README.md#75-exploratory-and-adversarial-evals), Lab 7.3 |
| Prototypes and Demonstrations | Labs 7.1-7.3, Project 5 |
| Design: AI Code Reviewer System | [Design 5](modules/09-system-design/05-ai-code-reviewer.md) |
| Design: Self-Updating AI Doc + Externalized Platform | [Design 6](modules/09-system-design/06-self-updating-docs-platform.md) |

### Week 3 - Session 2: Production Gotchas and Systems

| His topic | Covered in |
|---|---|
| Self-evolving Agents | [Module 8.5](modules/08-production/README.md#85-self-evolving-agents), Lab 8.4 |
| Prompt Caching | [Module 8.1](modules/08-production/README.md#81-prompt-caching), Lab 8.1 |
| Observability | [Module 8.2](modules/08-production/README.md#82-observability), Lab 8.2, `aikit/trace.py` |
| Cost Efficient Systems | [Module 8.3](modules/08-production/README.md#83-cost-efficient-systems), Lab 8.3 |
| Multi-agent Systems Prod Gotchas | [Module 8.6](modules/08-production/README.md#86-multi-agent-systems-in-production) |
| Brainstorming Prod Gotchas in Usecases | [Module 8.7](modules/08-production/README.md#87-brainstorming-production-gotchas-for-a-use-case) |
| Prototypes and Demonstrations | Labs 8.1-8.4, Project 6 |
| Design: Natural Language Workflow Engine | [Design 7](modules/09-system-design/07-nl-workflow-engine.md) |

### What this course adds

| Addition | Why |
|---|---|
| Modules 0-1: setup, tokens, sampling, the API, embeddings | His course assumes working engineers; this one starts from basic Python |
| Six guided projects with reference solutions | Project-based learning with a check at every step |
| Module 4.2 and 4.7: chunking and retrieval evaluation | You cannot improve RAG without them |
| Module 8.4: reliability engineering | Rate limits, fallbacks, degradation |
| Module 10: portfolio, interviews, job search | The goal is a job |

### A note on two topics

- **"System One Models - Jev and Clairic"** refers to models announced in September and October 2026. Module 2.7 explains them from public sources and flags that vendor performance claims were unverified at the time of writing. The lab teaches the architecture they enable with a stand-in, because their APIs are new and may change.
- **"Self-Updating AI Doc + Externalized Platform"** is one line in his outline. Design 6 reads it as a self-updating documentation agent that is then offered to outside organizations as a multi-tenant platform, and says so at the top.

This course follows his published topic list. It was written independently and contains none of his lectures, slides or code.
