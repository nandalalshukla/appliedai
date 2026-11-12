# Applied AI Masterclass

**From zero to shipping production AI systems.** A free, project-based course for people who want to work as AI engineers: the people who build the AI products that millions use.

You will not memorize definitions here. Every idea is introduced with a problem, built from scratch in a few dozen lines of Python, broken on purpose so you see the failure, and then used in a real project.

```
16 weeks  ·  11 modules  ·  40+ runnable labs  ·  6 guided projects  ·  8 system designs
```

## Who this is for

- You can write basic Python (functions, loops, dictionaries). That is the only hard requirement.
- You want a job building AI products, or you are a software engineer moving into AI.
- You do **not** need machine learning, deep learning, or math beyond school level. This course is about *using* models to build systems, not training them.

## What you will be able to do at the end

| Skill | Proof you will have |
|---|---|
| Prompt models reliably and get structured data out | A ticket-triage service with validated outputs |
| Build tools and retrieval (RAG) that hold up on real data | A cited question-answering system over your own documents |
| Build agents: loops, checkpoints, human approval | A working coding agent, a small version of Claude Code |
| Design memory and multi-agent systems | A research team of agents with long-term memory |
| Measure quality with evals instead of vibes | An eval harness that gates changes in CI |
| Run AI in production: caching, cost, observability, safety | A deployed, streamed, traced, budgeted capstone service |
| Reason about AI system design in interviews | Eight worked designs, from "RAG over 10M docs" to a workflow engine |

## How the course is organized

| # | Module | Weeks | You build |
|---|---|---|---|
| 0 | [Setup](modules/00-setup/README.md) | 0 | A working environment |
| 1 | [Foundations: how LLMs actually behave](modules/01-foundations/README.md) | 1-2 | A tokenizer, an embedding search, a chatbot |
| 2 | [Prompting LLMs reliably](modules/02-prompting/README.md) | 3-4 | Structured extractors, a prompt registry |
| 3 | [Tool use](modules/03-tool-use/README.md) | 5 | A tool registry with validation and retries |
| 4 | [Retrieval-augmented generation](modules/04-rag/README.md) | 6-7 | BM25, vector search, hybrid search, re-ranking, a semantic cache |
| 5 | [Single-agent loops and systems](modules/05-agents/README.md) | 8-9 | An agent loop with checkpoints and human approval |
| 6 | [Memory and multi-agent systems](modules/06-memory-multi-agent/README.md) | 10-11 | A memory store, an orchestrator with specialists |
| 7 | [Evaluation and safety](modules/07-evals-safety/README.md) | 12-13 | An eval harness, an LLM judge, a red-team suite |
| 8 | [Production](modules/08-production/README.md) | 14 | Caching, tracing, cost control, a streaming API |
| 9 | [AI system design](modules/09-system-design/README.md) | 15 | Eight design documents |
| 10 | [Career: portfolio, interviews, job search](modules/10-career/README.md) | 16 | A portfolio and an interview plan |

Projects live in [`projects/`](projects/README.md). The full week-by-week plan is in [`SYLLABUS.md`](SYLLABUS.md), and hand-picked external material for every module is in [`RESOURCES.md`](RESOURCES.md).

### Coverage of Arpit Bhayani's Applied AI syllabus

Every topic in [Arpit Bhayani's Applied AI masterclass](https://arpitbhayani.me/applied-ai/) is covered, including all eight of his system-design problems. [`SYLLABUS.md`](SYLLABUS.md#mapping-to-arpit-bhayanis-applied-ai-syllabus) has a line-by-line map from each of his topics to the lesson here that teaches it. This course adds the fundamentals before that syllabus (Modules 0-1) and the career material after it (Module 10), so a beginner can start from nothing.

This is an independent course. It follows the topic list he publishes; it does not contain his lectures, slides, or code.

## Quick start

```bash
git clone https://github.com/nandalalshukla/appliedai.git
cd appliedai
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt && pip install -e .
python modules/01-foundations/labs/01_tokens.py
```

That last command works with **no API key and no money**. See below.

## You can do the whole course for free

Every lab runs in two modes:

- **Mock mode** (default when no API key is set). The lab replays a scripted model response, so you can read the code, run it, step through it in a debugger, and see the full flow offline. All tests run this way.
- **Live mode** (when `ANTHROPIC_API_KEY` is set). The same code talks to a real model.

Mock mode teaches you the mechanics. Live mode teaches you how models really behave, which is the part employers pay for, so do switch to it when you can. To keep it cheap, set `AIKIT_MODEL=claude-haiku-5-5` in your `.env`; the whole course then costs a few dollars at most. Setup details are in [Module 0](modules/00-setup/README.md).

The code uses the Claude API through the official `anthropic` Python SDK. The ideas are the same on every provider; Module 1 shows what changes if you use OpenAI or Gemini instead.

## How to study

1. **Read the lesson** (`README.md` in each module). Each section starts with the problem it solves.
2. **Run every lab** and change something. Each lab ends with "Try it" tasks. Do them; that is where the learning is.
3. **Answer the checkpoint questions** at the end of a module without looking. If you cannot, re-read that section.
4. **Build the project** the module points to. Guides are step by step, each step has a way to check that it works, and each project ships a reference solution to compare against *after* you try.
5. **Write about what you built.** One short post per project. Module 10 explains why this matters more than certificates.

Plan for 8-10 hours a week. If you have less time, keep the order and stretch the calendar; do not skip the projects.

## Repository layout

```
aikit/       shared toolkit: client factory, mock client, cost meter, embedder
modules/     lessons and labs, in order
projects/    six guided projects with reference solutions
tests/       tests for the toolkit, labs and solutions (run: pytest)
```

## When you get stuck

- Every project step has a **"Check"** and a **"If it fails"** box. Start there.
- Run the tests: `pytest -q`. They run offline and tell you whether your environment is healthy.
- Read [`modules/00-setup/README.md`](modules/00-setup/README.md#troubleshooting) for the ten most common errors.
- Compare with the reference solution only after a real attempt. Reading a solution feels like learning and mostly is not.
