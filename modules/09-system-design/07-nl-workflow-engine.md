# Design 7: Natural-language workflow engine

## Problem

Let non-engineers describe automations in plain language ("When a new lead fills in the form, look up their company, score them, add them to the CRM, and message the sales channel if the score is above 80") and have the system run them reliably.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| Who writes workflows? | Operations and sales staff, not programmers |
| How often do they run? | A workflow is written once and runs thousands of times |
| Integrations? | Dozens of connectors (CRM, email, chat, sheets, HTTP) |
| Cost of error? | Workflows act on real systems: send messages, write records |
| Reliability? | Must behave the same way every run, survive crashes, and be auditable |

## The central decision: compile, do not improvise

Two possible designs:

| | A. Agent at run time | B. Compile to a workflow, then execute |
|---|---|---|
| How | Every trigger starts an agent that reads the description and decides what to do | The model translates the description **once** into a structured workflow; a deterministic engine runs it |
| Predictability | Varies between runs | Same every run |
| Cost per run | Many model calls | Zero or a few, only in steps that need judgment |
| Auditability | Read a transcript | Read a diagram |
| Flexibility | High | Limited to what the workflow language can express |

Choose **B**. The request is written once and executed many times, the steps are knowable in advance, and users need to trust it. Natural language is the *authoring interface*; a typed workflow is the *program*. Model calls remain available as explicit steps inside the workflow ("classify this email", "draft a reply"), where judgment is really needed.

## Architecture

```
AUTHORING (once)
 description ─► PLANNER (model) ─► workflow definition (typed graph, JSON)
                  │ sees: connector catalogue (retrieved), examples
                  ▼
              VALIDATOR (code): schema, types between steps, known connectors,
                  │             permissions, no cycles without limits, cost estimate
                  ▼ errors go back to the planner to repair (bounded retries)
              PREVIEW: diagram + plain-language explanation + dry run on sample data
                  ▼ user confirms or edits in conversation
              versioned, stored

EXECUTION (many times)
 trigger ─► DURABLE ENGINE: step by step, state persisted after each step
              ├─ deterministic steps: connector calls, conditions, transforms, loops
              ├─ LLM steps: classify / extract / draft, with schema-constrained output
              ├─ approval steps: pause until a human responds
              └─ retries, timeouts, idempotency keys, compensation on failure
            ─► run log + trace ─► monitoring, and plain-language failure explanations
```

## Key decisions

**The workflow language (IR).** A small, typed, declarative format: triggers, steps with typed inputs and outputs, references between steps, conditions, bounded loops, error handlers. Keep it small. Everything the model emits is validated against it, which is the structured-output discipline of Module 2 applied to a whole program.

```json
{"trigger": {"type": "form.submitted", "form": "lead"},
 "steps": [
   {"id": "enrich",  "use": "company.lookup", "in": {"domain": "{{trigger.email_domain}}"}},
   {"id": "score",   "use": "llm.classify",    "in": {"text": "{{enrich.summary}}"},
                     "out_schema": {"score": "int[0,100]", "reason": "string"}},
   {"id": "crm",     "use": "crm.create_lead", "in": {"email": "{{trigger.email}}", "score": "{{score.score}}"}},
   {"id": "notify",  "if": "{{score.score}} > 80",
                     "use": "chat.post",       "in": {"channel": "#sales", "text": "Hot lead: {{trigger.email}}"}}]}
```

**Connectors are tools with schemas.** Each has typed inputs, outputs, required permissions, and flags for side effects and idempotency. With hundreds of connectors, do not put them all in the prompt: retrieve the relevant ones for the description (tool search).

**Validate, then repair.** The planner's output is checked by code: do referenced steps exist, do types line up, does the user have access to each connector? Errors are returned to the planner with specifics, at most a few times, then to the user as a question.

**Resolve ambiguity by asking.** "Message the sales team" — which channel? "High score" — above what? The planner should ask rather than guess, and show its assumptions in the preview.

**Preview and dry run.** Before activation the user sees a diagram, a plain-language restatement, and the result of running on sample data with side effects stubbed. This is the human-in-the-loop step, placed where it is cheapest: once, at authoring time.

**Durable execution.** The engine persists state after each step (Module 5.5 at platform scale). Crashes resume from the last completed step. Each side-effecting step carries an idempotency key derived from run ID and step ID, so a retry cannot post the message twice. Waiting for an approval or a timer consumes nothing.

**LLM steps are contained.** They receive only the fields mapped into them, produce schema-validated output, and cannot call arbitrary tools. A failed validation retries, then routes to the error handler. Untrusted data flowing through (an inbound email body) therefore cannot redirect the workflow: control flow lives in the validated definition, not in model output.

**Agent steps as an escape hatch.** For tasks that really are open-ended ("research this company"), a workflow may include a bounded agent step with a restricted tool set, a budget and a typed result. The default is still deterministic.

**Self-healing, carefully.** When a connector's API changes and a step starts failing, the system can propose a repaired workflow version. It is a proposal, validated and dry-run, then confirmed by the owner (Module 8.5).

**Cost model.** Authoring costs a few model calls, once. Execution costs nothing for deterministic steps, and LLM steps can use a small model with a cached prefix. Compare with design A, which would pay for a full agent run on every trigger. Show users an estimated cost per run in the preview.

## Failure modes

| Failure | Mitigation |
|---|---|
| The workflow does not match what the user meant | Preview, restatement, dry run; clarifying questions |
| Hallucinated connector or field | Validator against the catalogue; repair loop |
| Duplicate side effects on retry | Idempotency keys; exactly-once bookkeeping per step |
| Partial failure mid-workflow | Persisted state; per-step retry; compensation steps; alert the owner |
| Infinite or expensive loops | Bounded loops; per-run step and cost limits; rate limits per connector |
| Injection through data | Model steps cannot alter control flow; typed outputs; least-privilege connectors |
| Privilege escalation | Workflows run with the author's permissions, checked at authoring and at run time |
| Silent breakage when an external API changes | Connector contract tests; failure alerts in plain language; proposed repairs |
| A trigger storm | Queues, per-tenant concurrency limits, backpressure |

## Evaluation

- **Authoring:** a dataset of descriptions paired with reference workflows. Score by validity, then by *behavioural equivalence*: run both on test inputs with mocked connectors and compare the side effects. Do not compare JSON text.
- **Clarification:** on deliberately ambiguous descriptions, does the planner ask?
- **Execution:** fault injection (kill the worker mid-step, fail a connector) and assert no duplicate effects and eventual completion.
- **LLM steps:** ordinary component evals.
- **Online:** share of workflows activated without manual edits; run success rate; edits after activation.

## Build the core

Define a five-step-type IR with Pydantic. Write three mock connectors with `aikit.tools`. Build the planner (`messages.parse` into the IR), the validator with a repair loop, and an executor that checkpoints after each step and uses idempotency keys. Write ten description-to-behaviour eval cases with mocked connectors.
