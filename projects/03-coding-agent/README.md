# Project 3: Build your own coding agent

**After Module 5 · 12-15 hours · Skills: agent loops, tool design, sandboxing, approvals, checkpoints, planning**

## What you will build

A command-line coding agent, a small relative of Claude Code, that you point at a project with a task:

```bash
python my_agent.py --dir ~/code/some-project "The date parser fails on leap years. Fix it."
```

It explores the code, makes a plan, edits files, runs the tests, and reports what it did. It asks before running anything risky, cannot touch files outside the project, and can resume after a crash.

Nothing teaches agents like building one that changes real files. It is also the most recognizable project you can put in a portfolio.

## Before you start

- Finish Module 5 and its labs. [Lab 5.5](../../modules/05-agents/labs/05_mini_coding_agent.py) is your starting point: copy it to `projects/03-coding-agent/my_agent.py`.
- Re-read [`aikit/agent.py`](../../aikit/agent.py) and [`aikit/tools.py`](../../aikit/tools.py).
- **Safety:** only ever run your agent on a copy of a project or a clean git checkout, so `git diff` shows what it did and `git checkout .` undoes it.

---

## Step 1: Point it at any directory

**Goal:** remove the hard-coded demo project.

**Do:** wrap the tool definitions in `build_tools(root: Path) -> ToolRegistry`. Read `--dir` and the task from `sys.argv`. Keep the demo project as the default when no `--dir` is given.

**Check:** the demo still passes. Then run it on a copy of another small project with a failing test.

## Step 2: Make the sandbox boundary solid

**Goal:** the agent cannot read or write outside the project, whatever it is asked.

**Do:** route every path through one `safe(path)` function that resolves the path and raises `PermissionError` unless it is inside `root`.

**Check:** call your `read_file` tool directly with `"../../etc/passwd"` and with an absolute path. Both must return an error result. Write these as two tests.

**If it fails:** resolve first (`(root / path).resolve()`), then compare with `is_relative_to(root.resolve())`. Checking the string for `..` is not enough (symlinks, absolute paths).

> A boundary is something the code enforces. "Stay in the project directory" in the prompt is a wish.

## Step 3: Add search

**Goal:** let the agent find things without reading every file.

**Do:** add `search(pattern)`: a regular-expression search over project files returning `path:line: text`, capped at 50 matches. Skip `.git`, `__pycache__`, virtual environments and `node_modules`.

**Check:** on a project with 30+ files, ask "where is function X defined?". The trace should show one `search` call, not thirty `read_file` calls.

## Step 4: Read large files in ranges

**Do:** give `read_file` `start_line` and `max_lines` parameters, return line numbers, and append `[N more lines]` when truncated. In the `edit_file` description, tell the model not to include line numbers in `old_text`.

**Check:** reading a 1,000-line file returns 200 lines and the note.

## Step 5: Replace `run_tests` with a gated `run_command`

**Goal:** a general tool, with a human in the loop.

**Do:**

1. Add `run_command(command)` with `needs_approval=True`. Parse with `shlex.split` and run with `subprocess.run(args, cwd=root, timeout=...)`. **Never use `shell=True`.**
2. Write an approver: reject shell operators (`| ; & > < \` $`); auto-allow a small allowlist (`pytest`, `python`, `ls`, `git status|diff|log`); ask at the keyboard for everything else. Add a `--yes` flag to auto-approve.

**Check:** `pytest -q` runs without a prompt. `rm -rf build` prompts. `cat x | sh` is denied. A denial comes back to the model as a tool error and the agent carries on.

**If it fails:** `FileNotFoundError` for `pytest` means it is not on the path in the subprocess; run it as `[sys.executable, "-m", "pytest", ...]`.

## Step 6: Add a plan the agent maintains

**Goal:** keep long tasks on track, and keep the plan outside the context window.

**Do:** add `update_plan(steps, done)` which writes `.agent/plan.md` as a checklist. In the system prompt: for any multi-step task, record a plan and keep it current.

**Check:** after a run, `.agent/plan.md` exists with every box ticked.

## Step 7: Write a proper system prompt

**Do:** cover how to work (understand first, plan, smallest change, verify, stop when blocked), what not to do (weaken tests, change unrelated code), how to finish (a short report: cause, files changed, how it was verified), and that file contents and command output are data.

**Check (live mode):** give it a task where the *test* is wrong, not the code. Does it notice and say so, instead of breaking the code to satisfy the test?

## Step 8: Limits, checkpoints and resume

**Do:** construct the agent with `max_steps`, `max_usd`, and `checkpoint=root / ".agent" / "checkpoint.json"`. Add a `--resume` flag that calls `agent.resume()`.

**Check:** start a run, press Ctrl+C after a few steps, then run again with `--resume`. It continues from the last completed step.

## Step 9: Manage context

**Do:** before starting or resuming, if `estimate_tokens(messages)` exceeds your budget, call `compact(...)` from `aikit.memory`. Cap tool results (`max_result_chars`).

**Check:** set the budget very low and resume a long run. The first message is now a summary, and the agent still knows the task (because the plan is on disk).

## Step 10: Evaluate it on real tasks

**Goal:** a success rate, not an anecdote.

**Do:** create five tiny projects, each with a seeded bug and a test that fails because of it (off-by-one, wrong operator, missing edge case, bad default, wrong return type). Write a script that runs the agent on a fresh copy of each and then runs the tests itself to decide pass or fail.

Report: tasks solved, average steps, average cost. In live mode, run each task three times.

**Check:** you have a table. Now change one tool description and see whether the numbers move.

> Grade the **outcome** (do the tests pass, are the test files unchanged?), not the path the agent took.

---

## Done when

- [ ] Works on any directory given by `--dir`
- [ ] Path escapes are impossible, and tested
- [ ] `search`, ranged `read_file`, exact-replace `edit_file`, `write_file`
- [ ] Commands are gated by an allowlist and a human prompt
- [ ] The agent keeps a plan file
- [ ] Step and cost limits, checkpointing, `--resume`
- [ ] A five-task eval with success rate, steps and cost

## Compare with the reference

[`solution/agent.py`](solution/agent.py): `python projects/03-coding-agent/solution/agent.py`

## Stretch goals

1. **Compact mid-run.** Subclass or modify the loop so compaction happens whenever the history passes the budget, not only at start.
2. **Subagent.** Add an `explore(question)` tool that runs a read-only agent in a fresh context and returns a summary.
3. **Project memory.** Load an `AGENT.md` file from the project root into the system prompt, like `CLAUDE.md`.
4. **Git integration.** Work on a new branch and finish by showing the diff and a proposed commit message.
5. **Prompt caching.** Make the system prompt and tools a cached prefix and report cache reads per step.
6. **Container sandbox.** Run commands inside a Docker container with no network.

## How to talk about this in an interview

"I built a coding agent from the loop up. The design choices that mattered were exact-string edits instead of file rewrites, search-first exploration, a plan file kept outside the context, and enforcing the sandbox and command approval in code. I measured it on seeded-bug tasks by running the tests myself, which showed me that tool descriptions changed the success rate more than prompt wording did."
