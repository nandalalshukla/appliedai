# Module 5: Single-agent loops and systems

**Weeks 8-9.** An agent is a model that decides its own next step, in a loop, using tools. This module builds one from the loop up, then adds what it needs to run unattended: limits, checkpoints and human approval. It ends by taking apart how a real coding agent works.

Labs: [`labs/`](labs/) · Toolkit: [`aikit/agent.py`](../../aikit/agent.py) · Design problem: [Paper-to-code agent](../09-system-design/03-paper-to-code-agent.md) · Project unlocked: [P3 Build your own coding agent](../../projects/03-coding-agent/README.md)

---

## 5.1 Workflow or agent?

Two kinds of system get called "agentic":

| | Workflow | Agent |
|---|---|---|
| Who decides the next step | Your code, on a fixed path | The model, at run time |
| Example | extract → classify → draft → review | "Fix the failing test" |
| Predictability, cost, latency | High, low, low | Lower, higher, higher |
| Use when | The steps are known in advance | The steps depend on what is discovered along the way |

**Use an agent only when you cannot write the steps down.** Check four things first:

1. **Complexity:** is the task open-ended, with an unknown number of steps?
2. **Value:** does the result justify 10-100x the cost of a single call?
3. **Capability:** can current models actually do each step?
4. **Cost of error:** can mistakes be caught (tests, review) and undone?

If any answer is no, build a workflow. Many products described as agents are, correctly, workflows with one or two model-driven decisions.

## 5.2 Anatomy of an agent

Run [Lab 5.1](labs/01_agent_loop.py) with [`aikit/agent.py`](../../aikit/agent.py) open.

| Part | What it is | In the lab |
|---|---|---|
| **Model** | Chooses the next action | `client.messages.create(...)` |
| **Instructions** | Goal, procedure, limits | `SYSTEM` |
| **Tools** | What it can observe and do | `get_ticket`, `list_charges`, `add_note` |
| **State** | The message history: its entire memory of the run | `result.messages` |
| **Loop** | Calls the model, runs tools, feeds results back | `Agent.run` |
| **Stopping rule** | When to end | No tool call, or a limit is hit |
| **Environment** | What the tools touch: files, APIs, databases | The dicts in the lab |

The agent's **harness** is everything except the model: the loop, the tools, the context management, the permissions. Two products using the same model can differ enormously in quality because of their harness. Building harnesses is the job.

## 5.3 The observe-think-act loop

```
        ┌──────────────────────────────────────────────┐
        ▼                                              │
   OBSERVE  read history + latest tool results         │
        ▼                                              │
   THINK    model picks the next action or finishes ───┼──► final answer
        ▼                                              │
   ACT      your code runs the tool calls ─────────────┘
```

In code, this is the loop from Module 3 with rails added:

```python
for step in range(start_step + 1, self.max_steps + 1):
    response = self.client.messages.create(...)             # THINK
    messages.append({"role": "assistant", "content": response.content})
    calls = tool_calls(response)
    if not calls:
        return AgentResult(text_of(response), "done", ...)  # finished
    results = self.registry.run_calls(response, approve=self.approve)   # ACT
    messages.append({"role": "user", "content": results})   # OBSERVE next turn
    self._save(messages, step)                              # checkpoint
```

Every unattended loop needs these rails. `Agent` has all of them:

| Rail | Protects against |
|---|---|
| Step limit (`max_steps`) | Wandering forever |
| Budget limit (`max_usd`) | A surprise bill |
| Repeated-call detection | Being stuck retrying one failing action |
| Tool timeouts (Module 3) | A hung dependency |
| `stop_reason` checks | Acting on truncated or refused output |
| Event hook (`on_event`) | Not knowing what happened |

Every stop that is not `done` needs a product decision: retry, resume, hand to a human, or tell the user. "The agent hit its step limit" is not an error message a user can act on.

### The feedback loop is what makes agents work

In Lab 5.1 the agent is told to *verify* the customer's claim, and it has a tool to do so. In Lab 5.5 the coding agent *runs the tests* after editing. An agent that can check its own work corrects its own mistakes; one that cannot simply produces confident output. When you design an agent, ask first: **how will it know whether it succeeded?** Give it that tool.

## 5.4 The ReAct loop

Run [Lab 5.2](labs/02_react_from_scratch.py). **ReAct** (Reason + Act) is the 2022 research idea that started this: have the model interleave reasoning with actions and feed observations back.

```
Thought: I need the capital first.
Action: search[capital of Australia]
Observation: Canberra                 ← inserted by your code
Thought: Now I can answer.
Final Answer: Canberra
```

The lab implements it with string parsing so you can see that an agent is nothing more than a prompt format plus a loop. Today's tool-calling APIs are ReAct with the fragile parts replaced:

| Text ReAct | Native tool calling |
|---|---|
| `Thought:` lines | Thinking blocks, or text before the tool call |
| `Action: search[...]` parsed by regex | Typed `tool_use` block validated against a schema |
| Model might write its own fake `Observation:` | Generation stops at the tool call; only you supply results |

Related loop shapes you will see named:

- **Plan-then-execute:** write a plan first, then carry it out. Good for long tasks; many agents keep a to-do list they update as they go.
- **Reflection:** after acting, critique the result and revise. Running tests is the grounded version of this.
- **Evaluator-optimizer:** one call produces, another judges against criteria, repeat until it passes.

## 5.5 Checkpoint and resume

Run [Lab 5.3](labs/03_checkpoint_resume.py). The process is killed during step 3; a new process resumes at step 3 and every region is fetched exactly once.

Why you need it: long runs are interrupted by deploys, crashes and timeouts. Starting over wastes money and **repeats side effects**.

How it works: an agent's entire state is its message list (plus anything in its environment). Persist the list after every completed step and you can continue from it.

Getting it right:

1. **Write atomically** (temp file, then rename), or a crash mid-write corrupts the checkpoint.
2. **Save only valid histories.** Every `tool_use` must have its `tool_result`. Save after results are appended.
3. **Assume the interrupted step may run again.** Write tools must be idempotent (Module 3).
4. **Store checkpoints in a database** keyed by run ID in production, so any worker can resume any run.
5. **Record the configuration** (prompt version, tool versions, model) with the checkpoint. Resuming an old run under a new prompt can confuse the model.
6. **The environment is state too.** If the agent edited files, the checkpoint must be consistent with them (same working directory, or a snapshot).

This is the idea behind *durable execution* engines such as Temporal, and behind the checkpointers in agent frameworks. Now you know what they do underneath.

## 5.6 Human in the loop

Run [Lab 5.4](labs/04_human_in_the_loop.py). A $20 refund is auto-approved by policy; a $900 refund is blocked and the agent explains that it needs review.

Principles:

- **Gate in code, at the tool boundary.** A rule in the prompt can be argued away by a malicious input. A check in `run_calls` cannot.
- **Classify actions by reversibility and blast radius.**

  | Class | Examples | Policy |
  |---|---|---|
  | Read-only | search, read file | Always allow |
  | Reversible, local | edit a file in a branch | Allow, log |
  | Costly or external | send email, small payment | Allow by policy, else ask |
  | Irreversible, high impact | delete data, large payment, deploy | Always ask |

- **Show the exact action and arguments.** Approving "send an email" is meaningless; approving *this* email to *this* address is not.
- **A denial is information.** Return it to the model as a tool result so it can change course.
- **Avoid approval fatigue.** People asked fifty times a day stop reading. Ask rarely and make each request easy to judge.
- **Pause is checkpoint, approve is resume.** Real approvals take hours. The run is persisted at the approval point and resumed when a person responds.

Other places a human belongs: clarifying an ambiguous goal *before* starting, reviewing a plan before execution, and receiving an escalation when the agent is stuck. An agent that asks one good question up front often saves twenty wasted steps.

## 5.7 How Claude Code works

Run [Lab 5.5](labs/05_mini_coding_agent.py). In about 100 lines an agent explores a project, runs the tests, finds a bug, edits the file and confirms the fix. Coding agents such as Claude Code are this loop, engineered carefully. The following describes the publicly documented design; treat it as a study of patterns you can reuse, not an internal specification.

**1. One simple loop.** A single agent loop, like `Agent.run`. No elaborate graph. The model decides what to do next; the sophistication is in the tools and the context management.

**2. A small set of sharp tools.**

| Tool | Design lesson |
|---|---|
| Read file | Read before edit; results carry line numbers |
| Edit (exact string replacement) | Safer and cheaper than rewriting a file; a failed match is a correctable error |
| Search by content (grep) and by name (glob) | **Agentic search:** the agent searches the code the way a developer does, in several rounds, instead of relying on a pre-built embedding index |
| Shell | One general tool gives access to everything (tests, git, build tools), behind permission checks |
| To-do list | The agent writes and updates its own plan, which keeps long tasks on track |
| Subagent | Hands a sub-task to a fresh agent with its own context; only the summary returns (Module 6) |

**3. Context is treated as a scarce resource.**

- A project memory file (`CLAUDE.md`) is loaded at the start: conventions, commands, architecture. Persistent memory in a plain file.
- Large tool outputs are truncated or kept out of the main thread.
- When the conversation nears the limit, older turns are **compacted** into a summary.
- Subagents explore in separate contexts so that reading fifty files does not fill the main one.
- Prompt caching keeps the long, stable prefix (system prompt, tools) cheap (Module 8).

**4. Verification is built in.** The agent runs tests, linters and builds, reads the output, and iterates. The system prompt pushes it to verify before claiming success.

**5. Permissions are enforced by the harness.** Reads are allowed; edits and shell commands go through allow, ask and deny rules; some modes require a plan to be approved before any change. Hooks let teams run their own checks on every tool call.

**6. It is extensible.** MCP servers add tools; skills add instructions and scripts loaded on demand; custom commands package repeatable workflows.

What to take away for your own agents: keep the loop simple, invest in tool design, give the agent a way to check its work, manage context deliberately, and put safety in code.

## 5.8 Common agent failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Loops on one failing call | Unhelpful error message | Improve the error; repeated-call guard |
| Declares success without doing the work | No verification step | Add a checking tool; require evidence in the final answer |
| Forgets the goal late in a long run | Context filled with tool output | Truncate, compact, to-do list, subagents |
| Takes a destructive shortcut (deletes the failing test) | Goal stated as "make tests pass" | State the real goal and the constraints |
| Works on easy cases, fails on real ones | Never evaluated on real tasks | Build a task set (Module 7) |
| Too slow | Sequential calls; too large a model for simple steps | Parallel read calls; smaller model or lower effort |
| Follows instructions found in a file or web page | Prompt injection through tool results | Least privilege; approval for risky actions; isolate untrusted content |

---

## Checkpoint

1. What is the difference between a workflow and an agent? Give a task suited to each.
2. Name the seven parts of an agent.
3. List four reasons an agent loop should stop other than "task complete".
4. What did native tool calling fix about text-based ReAct?
5. Why is the message list sufficient to resume an agent? What else might you need to restore?
6. After a crash and resume, a customer was emailed twice. What went wrong, and how do you fix it?
7. Why must approval gates live in code rather than in the prompt?
8. Why do coding agents use exact-string edits and iterative search instead of whole-file rewrites and an embedding index?

## Exercises

1. **Budget stop.** Use `max_usd` with a scripted client that reports large token usage. Make the run stop with `budget` and print a user-facing message.
2. **Plan first.** Add a `write_plan(steps: list[str])` tool and a rule that it must be called before any write tool. Enforce the rule in code.
3. **Durable approval.** Combine Labs 5.3 and 5.4: when approval is needed, save a checkpoint and exit. A second script approves and resumes the run.

## Project 3

Build [P3: Your own coding agent](../../projects/03-coding-agent/README.md).

## Go deeper

[Module 5 in RESOURCES.md](../../RESOURCES.md#module-5-agents).

Next: [Module 6: Memory and multi-agent systems](../06-memory-multi-agent/README.md)
