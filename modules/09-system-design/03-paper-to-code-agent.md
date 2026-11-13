# Design 3: Paper-to-code agent

## Problem

Given a research paper (PDF), produce a working code repository that implements its method and reproduces a key result.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| What counts as done? | The code runs, and a small-scale experiment produces a result consistent with the paper's claim |
| How long may it run? | Hours. This is a long-horizon background task |
| Compute? | A sandbox with a time and GPU budget |
| Human involvement? | Approves the plan; reviews the final repository |
| Risk? | It executes generated code, so isolation is mandatory |

This is a true **agent** problem: the steps cannot be listed in advance, and success is checkable by running code.

## Why it is hard

- Papers are long, with equations, tables and figures. Critical details are in appendices, or missing.
- The task takes hundreds of steps: far beyond one context window.
- "It runs" is not "it is correct". The agent can produce plausible code that implements something else.

## Architecture

```
PDF ─► 1. PARSE      text + equations + tables + figure captions, by section
     ─► 2. UNDERSTAND structured spec: method, architecture, hyperparameters, datasets,
     │                metrics, claimed results, and an explicit list of AMBIGUITIES
     ─► 3. PLAN       repo layout, file-by-file plan, milestones, a reduced experiment
     │                └─► human approves or edits the plan
     ─► 4. BUILD      coding agent in a sandbox: write file ► run ► read error ► fix
     │                one milestone at a time, tests at each milestone
     ─► 5. REPRODUCE  run the reduced experiment; compare with the paper's claim
     ─► 6. REPORT     README: what was implemented, deviations, assumptions, results
```

State lives **on disk**, not in the context: `spec.md`, `plan.md` with checkboxes, `notes.md` (decisions and dead ends), and the repository itself with git commits. After a context compaction or a crash, the agent re-reads these and continues.

## Key decisions

**Extract a spec before writing code (step 2).** A structured document the rest of the run depends on. Hyperparameters go in a table with the page each came from. Anything the paper does not state goes in an *ambiguities* list with the chosen default and the reason. This keeps guesses visible.

**Plan with milestones that are individually testable.** Data loading → model forward pass with shape checks → loss → training loop on a tiny batch (can it overfit ten examples?) → evaluation. Overfitting a tiny batch is a cheap, strong correctness check.

**The build loop is Lab 5.5 with stronger rails.** Tools: read, edit (exact replace), search, run command, run tests. The agent verifies after every change. A step limit and budget per milestone prevent it from grinding on one bug forever; when the limit is hit, it records the blocker and escalates.

**Context management for a long run.** Read the paper by section on demand, not all at once every turn. Keep the spec in a cached prefix. Use subagents for reading-heavy sub-tasks ("find every hyperparameter in the appendix") so the main context holds summaries only. Compact with the plan and notes files as the durable memory (Module 6).

**Sandbox.** Generated code runs in an isolated container: no credentials, restricted network (package index and dataset hosts only), CPU, memory and time limits. Papers and downloaded repositories are untrusted input.

**Reduced-scale reproduction.** Full reproduction may need days of GPUs. Define a small experiment whose expected behaviour follows from the paper (a trend, a relative ordering, a sanity value) and check that.

**Guard against shortcut "success".** State the real goal, forbid editing tests to make them pass, and have a separate reviewer step compare code against the spec section by section (does the loss match equation 4?).

## Failure modes

| Failure | Mitigation |
|---|---|
| Implements a simpler method than the paper | Spec-versus-code review by a separate call; equation-level checklist |
| Silent numerical bugs | Shape assertions, tiny-batch overfit test, known-value unit tests |
| Loses track after many steps | Plan file with checkboxes; notes file; periodic re-read |
| Hard-codes the expected result | Reviewer step; results must come from executed code with logged commands |
| Dependency hell | Pinned environment; a base image with common libraries |
| Runaway compute | Budgets per milestone and per run; kill switch |
| Missing details in the paper | Ambiguities list; stated assumptions; ask the human at plan approval |

## Evaluation

- A benchmark of papers with known reference implementations. Score: does it run, do unit tests written from the reference pass, does the reduced experiment match within tolerance.
- Rubric-based grading of the repository by a judge validated against expert review: components present, faithful to the spec.
- Track steps, cost and human interventions per paper.
- Run several trials per paper; agent success rates vary between runs.

## Build the core

Use a short, simple paper or a well-specified algorithm description. Extend Lab 5.5: add `spec.md` and `plan.md` handling, a `write_file` tool, a milestone loop with checkpoints (Lab 5.3), and a final reviewer call. Reproducing a classic algorithm from its original description is a good first target.
