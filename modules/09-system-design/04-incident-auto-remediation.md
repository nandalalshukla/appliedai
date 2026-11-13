# Design 4: Incident auto-remediation system

## Problem

When a production alert fires, an AI system should investigate, find the likely cause, and fix it or propose a fix, so that on-call engineers are woken less often and incidents end sooner.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| What may it do without a human? | Only pre-approved, reversible actions on a runbook allowlist (restart a pod, scale out, roll back the latest deploy) |
| Everything else? | Proposed to the on-call engineer for approval |
| Time pressure? | Useful output within 2 minutes of the alert |
| Cost of error? | Very high. A wrong action can turn a small incident into an outage |
| Volume? | Hundreds of alerts per day, many of them noise or duplicates |

The defining constraint is **blast radius**. The system has production access, reads untrusted data (logs can contain anything), and acts under time pressure. Design the permissions first, the intelligence second.

## Success metrics

- Mean time to resolution, and mean time to a correct diagnosis.
- Share of incidents auto-resolved, and share where the proposal was accepted.
- **Harmful action rate: target zero.** Track near misses.
- Pages avoided; engineer trust (do they read the summary?).

## Architecture

Multi-agent is justified here: investigation is parallel (metrics, logs, deploys, dependencies), each area floods context, and the *acting* role needs different permissions from the *reading* roles.

```
alert ─► DEDUPE & TRIAGE (code + small model): duplicate? known noise? severity?
              │
              ▼
        INCIDENT COMMANDER (orchestrator) ── owns the incident record, budget and deadline
          │ delegates in parallel, READ-ONLY specialists:
          ├─► metrics agent      what changed, when, on which services
          ├─► logs agent         error signatures around the start time
          ├─► change agent       deploys, config and flag changes in the window
          └─► dependency agent   upstream and downstream health
          │
          ▼ reports
        DIAGNOSE: ranked hypotheses, each with evidence and confidence
          │
          ▼
        REMEDIATION PLANNER: match a hypothesis to a runbook action
          │
          ├─ on the allowlist AND reversible AND high confidence ─► EXECUTOR (the only agent with write access)
          │        pre-checks ► act ► verify the metric recovered ► else roll back
          └─ otherwise ─► page the human with summary, evidence, proposed action, one-click approve
          ▼
        POSTMORTEM DRAFT + new eval case + runbook suggestion
```

## Key decisions

**Triage before agents.** Most alerts are duplicates or known noise. Group by service and time window in code; attach new alerts to an open incident instead of starting a new investigation. This is also your main cost control.

**Strict role separation.** Investigators hold read-only credentials. One executor holds write access, and only to allowlisted runbook actions exposed as narrow tools (`restart_deployment(name)`, `rollback_deploy(service, to_version)`), never a general shell. An investigator that is manipulated by a malicious log line cannot act.

**Actions are runbooks, not improvisation.** The planner chooses among vetted, parameterized, tested procedures. Free-form commands in production are for humans.

**Every action is a transaction:** pre-check (is the target what we think it is?), act, verify (did the error rate fall within N minutes?), and roll back automatically if not. Idempotency keys prevent a retry from restarting something twice.

**Approval tiers** (Module 5): read → always; allowlisted reversible actions on a single service → automatic with notification; anything wider, irreversible, or low confidence → human approval. Start with *everything* requiring approval, and move actions to automatic only as they earn trust in the data.

**Concurrency control.** Two incidents may touch the same service; two executors must not act on it at once. Use a per-resource lock with a timeout, held only by the executor, and acquire locks in a fixed order. This is exactly Lab 6.4. Also guard against *remediation loops*: restart, alert fires again, restart again. Cap automatic actions per resource per hour, then escalate.

**Deadlines travel with tasks.** Each specialist gets a time budget. The commander proceeds with whatever reports arrive and states what is missing. A slow logs query must not stall the whole incident.

**Memory.** Past incidents are indexed (symptoms → cause → fix). Retrieval of similar incidents is often the strongest diagnostic signal. Resolved incidents write back, after human confirmation of the cause.

**The human hand-off.** A page should contain: what is broken, since when, the leading hypothesis with evidence links, what was already tried, and the proposed action. This summary is valuable even when automation does nothing else.

## Failure modes

| Failure | Mitigation |
|---|---|
| Wrong diagnosis, confident action | Verify-after-act with auto-rollback; confidence thresholds; allowlist |
| Injection via logs or ticket text | Read-only investigators; executor accepts only structured runbook parameters; humans approve the rest |
| The fix causes a second incident | Blast-radius limits (one service, one region at a time); rate limits per resource |
| Deadlock or flapping between executors | Locks with timeouts and ordering; action caps; single executor per resource |
| The system itself is down during an outage | It must never be on the critical path; fall back to normal paging; independent infrastructure |
| Observability tools slow or failing | Timeouts; partial reports; state uncertainty explicitly |
| Alert storm | Deduplication; a concurrency cap; a global budget |
| Automation complacency | Always notify; weekly review of automatic actions |

## Evaluation

- Replay historical incidents with recorded telemetry: was the true cause in the top three hypotheses? Was the proposed action the one the humans took?
- A staging environment with injected faults (kill a pod, bad config, slow dependency): end-to-end success and time.
- Safety suite: scenarios where the correct behaviour is to *not act* and escalate; poisoned logs; conflicting incidents.
- Shadow mode in production first: propose only, compare with what engineers did.

## Build the core

Simulate a small system as Python dicts (services, metrics, a deploy log). Build the orchestrator and three read-only specialists from Lab 6.3, an executor with two runbook tools behind the approval policy from Lab 5.4, a verify-then-rollback step, and five fault scenarios as an eval.
