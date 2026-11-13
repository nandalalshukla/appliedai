# Projects

Six projects, in order. Each one is unlocked by a module and builds on the previous ones. Together they are your portfolio.

| # | Project | After | Time | What it proves you can do |
|---|---|---|---|---|
| 1 | [Support triage service](01-support-triage/README.md) | Module 2 | 6-8 h | Reliable structured outputs with validation and fallbacks |
| 2 | [Ask My Docs](02-ask-my-docs/README.md) | Module 4 | 10-12 h | RAG with rewriting, citations and separate retrieval evals |
| 3 | [Your own coding agent](03-coding-agent/README.md) | Module 5 | 12-15 h | Agent loops, tool design, sandboxing, approvals, resume |
| 4 | [Research team with memory](04-research-team/README.md) | Module 6 | 12-15 h | Orchestration, subagents, verification, long-term memory |
| 5 | [Eval harness with a CI gate](05-eval-harness/README.md) | Module 7 | 8-10 h | Measuring quality and blocking regressions automatically |
| 6 | [Capstone: production support copilot](06-capstone/README.md) | Module 8 | 20-25 h | Shipping: streaming API, guardrails, caching, tracing, budgets, deployment |

## How every guide works

Each project is a sequence of small steps. Every step has:

- **Goal:** what this step achieves and why it matters.
- **Do:** exactly what to write.
- **Check:** a concrete way to confirm it works before moving on.
- **If it fails:** the usual causes and fixes.

Follow the steps in order and do not move on until the check passes. If a check fails and the hints do not help:

1. Read the error message from the bottom up. The last line usually says what is wrong.
2. Print the exact prompt and the exact response. Most bugs are visible there.
3. Run the matching lab from the module; it shows the same idea in isolation.
4. Only then open the reference solution, find the relevant function, close it, and write your own.

## Rules for getting value from these

- **Type the code yourself.** Copying a solution produces a working folder and no skill.
- **Write the eval before you tune.** Every project includes one for a reason.
- **Keep a log.** A few lines per session: what you tried, what failed, what you learned. It becomes your write-up and your interview stories.
- **Use your own data** where the guide suggests it. A project on your own documents or repository is far more convincing than one on the sample corpus.
- **Publish each project** in its own repository with a README that has numbers. See [Module 10](../modules/10-career/README.md).

## Running the reference solutions

All run offline in mock mode:

```bash
python projects/01-support-triage/solution/triage.py
python projects/02-ask-my-docs/solution/ask.py --eval
python projects/03-coding-agent/solution/agent.py
python projects/04-research-team/solution/research.py
python projects/05-eval-harness/solution/run_evals.py
pytest projects/06-capstone/solution -q
```

Mock mode replays scripted model behaviour, so the numbers there show that the machinery works, not how good a model is. Run with an API key to see real behaviour.
