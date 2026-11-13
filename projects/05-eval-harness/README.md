# Project 5: Eval harness with a CI gate

**After Module 7 · 8-10 hours · Skills: eval datasets, scorers, baselines, regression gating, CI, judge validation**

## What you will build

One command that evaluates your earlier projects and decides whether a change may ship:

```
suite         baseline     now
triage             88%     94%
retrieval         100%    100%
safety            100%     75%

GATE FAILED
  - safety: must be 100%, got 75%
  - safety: newly failing cases ['s2']
```

It runs automatically on every push through GitHub Actions.

This is the project that most clearly separates you from people who have only built demos. In interviews, "how do you know it works?" is the question; this project is your answer.

## Before you start

- Finish Module 7. You need Projects 1 and 2 (yours or the reference solutions).
- Working file: `projects/05-eval-harness/my_evals.py`.
- Read [`aikit/evals.py`](../../aikit/evals.py). It is about 150 lines; you will use all of it.

---

## Step 1: Turn Project 1 into a suite

**Goal:** the triage service evaluated per field.

**Do:** write `suite_triage() -> Report`:

1. Load `tickets.jsonl` into `Case` objects. Put the full labelled row in `expected`. Add tags: the category, and `injection` or `normal`.
2. Write a scorer factory `field_matches(name)` returning a scorer that compares one field.
3. Call `run_eval("triage", cases, system, scorers)` where `system` is `lambda message: triage(client, message)`.

**Check:** `suite_triage().print()` shows a pass rate and a breakdown by tag.

**If it fails:** to import a solution from a folder with a hyphen in its name, load it by path with `importlib.util.spec_from_file_location` (see the reference).

## Step 2: A retrieval suite

**Do:** write `suite_retrieval()` with at least eight `(question, text the right chunk contains)` cases. The system under test is a search function returning the top three chunk texts. Scorers: `recall@3`, and `no_stale_docs` (no superseded document in the results).

**Check:** the suite prints a pass rate. Remove the metadata filter from the search and watch `no_stale_docs` fail. Put it back.

> A scorer that has never failed has never been tested. Break the system on purpose once, for every scorer you write.

## Step 3: A safety suite

**Do:** write `suite_safety()` with at least four attack cases against the triage service: two injections that try to raise urgency, an empty message, and a 5,000-character message. Scorers assert **properties**: urgency was not escalated; a valid ticket always comes back.

**Check:** 100% in mock mode. In live mode, add five more attacks and see what holds.

## Step 4: Store a baseline

**Goal:** remember what "good" looked like.

**Do:** with `--update-baseline`, write `baseline.json`:

```json
{"triage": {"pass_rate": 0.875, "failing": ["t07"]}, "retrieval": {...}}
```

Commit this file. It is now part of the repository's history: every change to it is a visible, reviewable decision.

**Check:** the file exists and lists the currently failing case IDs.

## Step 5: The gate

**Do:** write `gate(name, report, baseline) -> list[str]` returning reasons to fail:

1. The pass rate dropped more than a small tolerance below the baseline.
2. Any case that passed in the baseline now fails (a regression), even if the average went up.
3. Suites in `MUST_BE_PERFECT` (safety) are below 100%.

`main()` runs the suites, prints a comparison table, prints reasons, and returns exit code 1 if there are any.

**Check:** deliberately break something (for example, change a rule in the triage prompt, or in mock mode edit the mock responder). Run the script; it prints `GATE FAILED` with the specific cases, and `echo $?` prints `1`.

**If it fails:** if the gate passes when it should fail, print both sets of failing IDs and compare by hand.

> **Why per-case regressions and not just the average?** A change that fixes three cases and breaks two raises the average while making two real users' problems worse. Someone should decide that deliberately.

## Step 6: Run it in CI

**Do:** create `.github/workflows/ci.yml` that checks out the code, installs dependencies, runs `pytest`, then runs your eval script with `AIKIT_MOCK=1`.

**Check:** push a branch. The workflow appears under the repository's Actions tab and passes. Push a commit that breaks a case; the workflow fails and names it.

**About mock mode in CI.** Mock-mode evals test your *code* (parsing, checks, retrieval, gating logic) for free on every push. They do not test the model. For that, add a second workflow that runs in live mode with an API key stored as a repository secret, triggered manually or nightly, with its own `baseline.live.json`. Never print secrets in logs, and set a spending limit on that key.

## Step 7: Add a model-graded scorer and validate it

**Do:**

1. For the Project 2 assistant, collect 20 question/answer pairs. Label each by hand: is every claim supported by the cited passage?
2. Add a suite that scores the same pairs with `llm_judge(client, criterion, name="faithful")`.
3. Report judge-versus-human agreement, and how many of the truly unfaithful answers the judge caught.

**Check:** you have two numbers for your judge. If it misses bad answers, add one of them to the judge prompt as an example of a fail, and re-measure.

## Step 8: Repeat trials

**Do (live mode):** run each case three times. Report the pass rate per case. Mark cases that pass sometimes as *flaky* and list them separately.

**Check:** you can answer "is this failure consistent or intermittent?". Decide and document your gate rule for flaky cases (for example: a case counts as passing at 3/3 only for the safety suite, 2/3 elsewhere).

## Step 9: Make failures easy to read

**Do:** save each run to `runs/evals/<suite>-<timestamp>.jsonl` with input, output, scores and reasons. Write a small `show_failures.py` that prints the failures of the latest run in a readable form.

**Check:** given a failing gate, you can see the input, the wrong output and the reason within ten seconds.

## Step 10: Close the loop

**Do:** write a short `EVALS.md`: what each suite covers, how to add a case, how to update the baseline and who should approve that, and the rule "every production bug becomes a case before it is fixed".

Then practise it: find one real failure in any of your projects, add it as a case, watch the gate fail, fix it, watch it pass, and update the baseline.

---

## Done when

- [ ] Three suites: task quality, retrieval, safety
- [ ] A committed baseline, and a gate that fails on drops, regressions and imperfect safety
- [ ] The gate runs in GitHub Actions on every push
- [ ] One model-graded scorer, validated against 20 human labels
- [ ] Failures are saved and easy to inspect
- [ ] `EVALS.md` documents the process

## Compare with the reference

[`solution/run_evals.py`](solution/run_evals.py) and [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml):

```bash
python projects/05-eval-harness/solution/run_evals.py
python projects/05-eval-harness/solution/run_evals.py --suite safety
```

## Stretch goals

1. **Agent evals.** Add the five seeded-bug tasks from Project 3 as a suite graded by running the tests.
2. **Prompt comparison.** A `--compare v1 v2` mode that prints fixed and regressed cases between two prompt versions.
3. **Cost and latency as gated metrics.** Fail if cost per case rises more than 20%.
4. **Held-out set.** Split your cases; tune on one part, report the other only at release time.
5. **Synthetic cases.** Generate 30 candidate cases with a model, review them by hand, keep the good ones. Note how many you rejected and why.

## How to talk about this in an interview

"Every change to a prompt, a tool description or a model version goes through an eval gate in CI. It compares against a committed baseline, blocks per-case regressions even when the average improves, and requires 100% on the safety suite. My model-graded scorer was validated against hand labels before I trusted it; the first version missed a third of the bad answers."
