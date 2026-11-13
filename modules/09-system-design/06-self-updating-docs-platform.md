# Design 6: Self-updating AI documentation + externalized platform

## Problem

Part 1: documentation goes stale the moment code changes. Build a system that keeps product and engineering documentation current automatically.

Part 2: turn that internal system into a platform that external customers can use for their own repositories.

*How this design reads the brief:* the syllabus lists this as one line, "Self-Updating AI Doc + Externalized Platform". It is treated here as an internal docs agent first, then the changes needed to offer it to outside organizations. If your interviewer means something else by "externalized", the multi-tenancy section still applies.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| What docs? | API references, how-to guides, architecture overviews, runbooks |
| Source of truth? | The code and its merged changes. Docs live in the repository as markdown |
| Who approves changes? | Humans, through normal pull-request review |
| Cost of error? | Wrong docs are worse than missing docs: they are trusted |
| Part 2 scale? | Thousands of organizations, each with private code |

## Success metrics

- Doc freshness: time from a code change to a merged doc update.
- Acceptance rate of proposed doc PRs, and edit distance before merge.
- Accuracy: share of sampled doc statements that match the code.
- Coverage: share of public APIs and features documented.
- For readers: support tickets about documentation, search success.

## Part 1: architecture

Change-driven, not a nightly rewrite of everything.

```
merged PR / release
  │ 1. DETECT      what changed semantically? (signatures, config, behaviour, CLI flags)
  ▼
  │ 2. MAP         which doc sections depend on the changed code?
  │                doc ↔ code dependency index (explicit links + retrieval + symbol mentions)
  ▼
  │ 3. DECIDE      per section: no change / update / new section / remove; skip trivial changes
  ▼
  │ 4. DRAFT       docs agent: reads code, tests, PR description, existing doc and style guide;
  │                makes the MINIMAL edit that restores accuracy
  ▼
  │ 5. VERIFY      extract and run code examples; check links and referenced symbols exist;
  │                a judge checks each changed claim against the code
  ▼
  │ 6. PROPOSE     open a doc PR linked to the code PR, with a rationale per edit
  ▼
  │ 7. LEARN       reviewer edits and rejections ─► style guidance and eval cases
```

A scheduled **drift audit** complements this: sample doc sections, check them against the current code, and open issues for anything stale that the event path missed.

## Key decisions

**The doc-to-code map is the core data structure.** For each doc section, record which files and symbols it describes. Build it from explicit annotations where they exist, symbol names mentioned in the text, and embedding retrieval, then keep it updated as docs change. Without it you either miss stale sections or re-check everything on every commit.

**Minimal edits, not regeneration.** Rewriting a whole page destroys the author's voice, creates unreviewable diffs, and introduces new errors. Use exact-replace edits (Lab 5.5) and keep each PR small and attributable to one code change.

**Verification by execution.** Code samples in docs are extracted and run in a sandbox. API references are checked against the actual signatures in code. Anything checkable by code is checked by code; the judge handles prose claims.

**Humans stay in the loop through PR review.** The system never merges. Auto-merge can be earned later for narrow categories (regenerated API tables) once acceptance is consistently near 100%.

**Know what not to write.** Design rationale, trade-offs and "why" often cannot be derived from code. The agent flags these for a human instead of inventing a reason.

**"Self-updating" also applies to its own guidance.** Reviewer corrections become style rules and examples, accepted through an eval gate (Module 8.5).

## Part 2: externalizing it as a platform

Opening it to outside organizations changes the problem from "an agent" to "a multi-tenant product".

```
customer repo ─► GitHub App / webhook ─► API gateway (auth, rate limits, quotas per tenant)
                                           │
                                 job queue (per-tenant fairness)
                                           │
                    isolated workers: sandbox per job, short-lived scoped token
                                           │
              per-tenant stores: index, doc-code map, config, style guide, memory
                                           │
        outputs: PRs in the customer's repo · API + webhooks · dashboard · usage metering
```

| Concern | What it requires |
|---|---|
| **Tenant isolation** | Separate indexes or strict tenant keys enforced in the data layer; per-job sandboxes; no shared caches across tenants (including semantic caches); short-lived, least-privilege repository tokens |
| **Untrusted input** | Customer code and docs are untrusted. They can contain prompt injection and malicious build scripts. Never execute outside a sandbox; never let one tenant's content influence another's |
| **Configuration, not custom code** | Per-tenant config file: paths, style guide, tone, which docs to manage, approval rules, model tier |
| **Extensibility** | A stable API and webhooks; custom tools via MCP servers the customer registers; plug-in verifiers |
| **Fairness and limits** | Per-tenant queues, concurrency caps, rate limits and budgets, so one large customer cannot starve the rest |
| **Metering and billing** | Track tokens and jobs per tenant from traces; expose usage; enforce quotas |
| **Data handling** | Retention policy, deletion on request, region choice, a clear statement of what is sent to model providers, optional customer-supplied model keys |
| **Reliability** | Idempotent webhook handling (deliveries repeat), durable jobs with checkpoints, status page, retries |
| **Per-tenant quality** | Each tenant gets an eval set seeded from its own accepted and rejected PRs; global changes are gated on a cross-tenant suite |
| **Versioning** | Prompt and model upgrades roll out gradually per tenant, with rollback |
| **Trust features** | Audit log of every action, dry-run mode, explanation with each PR |

The hardest shift is mental: internally, a failure is a bad doc PR. Externally, the failures that end the company are a **data leak between tenants** and **executing a customer's malicious code outside a sandbox**. Design those out first.

## Failure modes

| Failure | Mitigation |
|---|---|
| Confidently wrong documentation | Execution checks; claim-level judge; human review |
| PR spam | Batch related changes; skip trivial diffs; per-repo caps |
| Docs drift the event path missed | Scheduled drift audit |
| Style damage | Minimal edits; style guide; learn from reviewer changes |
| Cross-tenant leakage | Isolation at the data layer; no shared caches; automated leak tests |
| Injection from repository content | Sandboxes; scoped tokens; the agent can only open PRs |
| Runaway cost on a monorepo | Budgets; incremental processing; change-driven scope |

## Evaluation

- Historical replay: for past code PRs that had accompanying doc changes by humans, does the system propose an equivalent update?
- Seeded staleness: change a signature, check that the right sections are flagged and fixed.
- Negative cases: refactors with no behaviour change must produce no doc PR.
- Platform: isolation tests, webhook replay tests, load tests with skewed tenants.

## Build the core

On a small repository of your own: build the doc-to-code map with `aikit.rag`, a detector that diffs function signatures between two commits, a drafting agent with exact-replace edits, a verifier that runs code blocks from the markdown, and an eval of ten seeded changes (including three that need no doc change).
