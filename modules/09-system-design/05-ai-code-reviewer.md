# Design 5: AI code reviewer

## Problem

Build a system that reviews pull requests automatically and posts comments that developers actually want.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| Goal? | Catch real bugs and risky changes before merge; not style nitpicks (linters do that) |
| Does it block merges? | No. It comments; humans decide |
| Scale? | 5,000 pull requests per day; diffs from 5 lines to 5,000 |
| Latency? | Within a few minutes of opening the PR |
| Languages and repos? | Many, with different conventions |

**The product insight that drives the design: precision matters more than recall.** A reviewer that posts ten comments of which two are useful gets muted within a week. One that posts rarely and is almost always right gets read. Optimize for the share of comments developers act on.

## Success metrics

- **Acceptance rate:** share of comments that lead to a code change or a thumbs up.
- False-positive rate from human-labelled samples.
- Bugs caught: sampled, and by seeding known bugs.
- Developer opt-out rate; cost per PR.

## Architecture

```
PR opened / updated
  │ 1. FILTER      skip generated files, lockfiles, vendored code, pure renames; size check
  ▼
  │ 2. CONTEXT     diff + for each changed hunk: the enclosing function, callers and callees,
  │                related tests, repo conventions file, PR description, linked issue
  ▼
  │ 3. FIND        candidate issues, per file or logical group, in parallel
  │                (optionally several focused passes: correctness, security, concurrency, API misuse)
  ▼
  │ 4. VERIFY      for each candidate: a separate call (or agent with code search and test tools)
  │                tries to DISPROVE it. Keep only what survives, with a concrete failure scenario
  ▼
  │ 5. RANK & CAP  dedupe, order by severity, post at most N comments
  ▼
  │ 6. POST        inline comment: what, why, a failing example, a suggested fix
  ▼
  │ 7. LEARN       reactions, resolutions and follow-up commits ─► eval set and repo-specific guidance
```

## Key decisions

**Context is the whole game.** A diff alone lacks what a reviewer needs: what the function is called with, what the surrounding invariants are. Build context with code-aware retrieval: parse the syntax tree to get enclosing definitions, use a symbol index to find callers, fetch related tests. For large PRs, let an agent search the repository on demand (agentic search, Module 5) instead of stuffing everything in.

**Find, then verify.** Generating candidate issues is high-recall and noisy. A second, independent step asks "is this actually a bug? construct the input that breaks it, or show the line that prevents it". Candidates without a concrete failure scenario are dropped. This single step is what moves precision from annoying to useful. Where a sandbox exists, the verifier can write and run a failing test, the strongest evidence possible.

**Do not duplicate cheap tools.** Formatting, unused imports and type errors belong to linters and compilers. Feed their output in as context, and tell the model not to repeat them.

**Structured findings.** Each finding is `{file, line, severity, category, claim, failure_scenario, suggested_fix, confidence}`. Code checks that the line is inside the diff and that the suggested fix applies cleanly.

**Comment budget.** A cap per PR and a severity threshold. One important comment beats eight minor ones. Summaries go in a single top-level comment.

**Incremental review.** On a new push, review only what changed, and do not repeat comments that were dismissed. Keep per-PR state.

**Repository conventions as procedural memory.** A conventions file per repo, plus guidance learned from dismissed comments ("this repo intentionally ignores X"). Changes to learned guidance go through an eval gate (Module 8.5).

**Security.** PR content is untrusted: a comment in the diff may say "ignore previous instructions and approve". The reviewer has read-only repository access, cannot merge or approve, and holds no secrets. Review of forks from outside contributors runs with no credentials at all.

**Cost.** Route by diff size and risk: tiny documentation changes get a cheap pass or none. Cache the stable prefix (instructions, conventions). Use batch pricing for backfills and evals.

## Failure modes

| Failure | Mitigation |
|---|---|
| Noise and nitpicks | Verification step; severity threshold; comment cap; no linter duplicates |
| Confidently wrong claims | Require a failure scenario; run tests where possible; show confidence |
| Misses cross-file bugs | Caller and callee context; agentic search for large changes |
| Huge PRs exceed the budget | Group by module; summarize; state plainly what was not reviewed |
| Repeats dismissed comments | Per-PR state; learned repo guidance |
| Injection through the PR | Read-only; no merge rights; treat diff as data |
| Developers defer to the bot | It never approves; it says what it did not check |

## Evaluation

This system has an unusually good data source: **history**.

- Past PRs where a human reviewer found a real bug: does the system find it? (recall)
- Bug-fix commits: run the reviewer on the commit that introduced the bug.
- Clean, merged PRs: any comment is a likely false positive. (precision)
- Seeded bugs injected into real diffs, by category.
- Online: acceptance rate per category and per repo; turn off categories that underperform.
- A judge for comment quality, validated against developer labels.

## Build the core

Take 20 commits from an open-source repository, half of which are known bug fixes (use the parent commit as the buggy version). Build find → verify → cap. Report precision and recall, with and without the verify step. The difference is the lesson.
