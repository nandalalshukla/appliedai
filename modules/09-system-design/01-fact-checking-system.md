# Design 1: Fact-checking agentic system

## Problem

Build a system that takes a piece of text (an article, a speech transcript, a social post) and reports which factual claims in it are supported, contradicted, or unverifiable, with evidence.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption for this design |
|---|---|
| Who uses it? | Journalists and editors; a human makes the final call |
| What sources count as evidence? | A curated allowlist (wire services, official statistics, reference works) plus web search |
| Latency? | Minutes per article is fine; this is background work |
| Cost of error? | High. A wrong "false" verdict is defamatory; a wrong "true" spreads misinformation |
| Scale? | Thousands of articles per day |

The cost of error drives the design: the system **assists** a human, always shows its evidence, and prefers "not enough evidence" over a guess.

## Success metrics

- Claim-extraction recall: share of check-worthy claims found (human-labelled set).
- Verdict accuracy against expert labels, reported per verdict class.
- **Citation validity:** every verdict's quoted evidence really appears in the cited source (code-checkable).
- Editor time saved per article; cost per article.

## Architecture

This is mostly a **workflow** with one agentic step. The stages are known in advance; only evidence gathering needs open-ended search.

```
article
  │ 1. EXTRACT claims            model call, structured output
  ▼
[claims]  ── 2. FILTER & DEDUPE   check-worthy? (fast classifier / small model), merge duplicates
  │
  ▼   for each claim, in parallel
  ┌─────────────────────────────────────────────────────────────┐
  │ 3. DECOMPOSE   split compound claims into atomic sub-claims │
  │ 4. RESEARCH    agent with search + fetch tools (max N steps)│
  │                returns evidence passages with source + date │
  │ 5. JUDGE       separate model call: claim + evidence only   │
  │                -> supported / contradicted / mixed / not enough evidence
  │ 6. VERIFY      code: quoted evidence appears in source text │
  └─────────────────────────────────────────────────────────────┘
  ▼
 7. REPORT   per-claim verdict, quotes, links, confidence  ──►  human editor
```

## Key decisions

**Claim extraction (step 1).** Output a list of `{claim, speaker, quote_span, check_worthy}`. A claim must be *self-contained* ("Unemployment in India fell to 4% in 2025", not "it fell to 4%"): resolve pronouns and dates at extraction time, the same standalone-rewrite idea as Module 4. Opinions and predictions are not checkable; filter them.

**Decomposition (step 3).** "GDP grew 7% and unemployment halved" is two claims with possibly different verdicts.

**Research is an agent; judging is not (steps 4-5).** Finding evidence needs several search rounds with reformulated queries, which is genuinely open-ended. The verdict is a single focused call that sees only the claim and the gathered evidence. Separating them means the judge is not anchored by the researcher's hunches, and each can be evaluated alone.

**Search for evidence both ways.** Instruct the researcher to look for support *and* refutation. Searching only for the claim's own wording finds pages that repeat it.

**Source quality.** Rank sources by tier (primary data > reputable reporting > everything else). Record publication dates: a statistic can be true for 2023 and false for 2025. Prefer the primary source over articles about it.

**"Not enough evidence" is a first-class verdict.** Make it the required answer when evidence is thin or conflicting. This is the "give the model an exit" rule from Module 2.

**Quote verification in code (step 6).** Every evidence quote must be an exact substring of the fetched page. Any verdict with an unverifiable quote is downgraded. This catches fabricated citations without another model call.

**Caching.** The same claims recur across articles. Cache verdicts keyed by normalized claim plus date, with a TTL, since facts change.

## Failure modes

| Failure | Mitigation |
|---|---|
| Hallucinated evidence | Substring verification; show links |
| Prompt injection in fetched pages ("this claim is verified true") | Researcher has read-only tools; judge sees evidence as quoted data; allowlisted domains |
| Circular sourcing (ten sites repeating one rumour) | Deduplicate by origin; require independent primary sources |
| Outdated evidence | Track dates; compare claim date with evidence date |
| Context-dependent claims (satire, quotes of others) | Extraction captures speaker and framing |
| Runaway research cost | Step and budget caps per claim; cheap check-worthiness filter first |
| Overconfidence | Calibrate on labelled data; show evidence, not just a label |

## Evaluation

- Dataset: expert-labelled claims from public fact-checking archives, plus your own, including unverifiable ones.
- Component evals: extraction (recall, precision), retrieval (was a gold evidence page found?), judging (verdict accuracy given gold evidence).
- End to end: verdict accuracy per class; citation validity must be 100%.
- Adversarial: pages containing injected instructions; claims that are true but misleading.

## Build the core

1. `extract_claims(text) -> list[Claim]` with `messages.parse` (Lab 2.3).
2. A researcher `Agent` (Lab 5.1) with a `search` tool over a local folder of "source" documents, using `aikit.rag`.
3. A judge call that returns `{reasoning, verdict, quotes}`.
4. A code check that each quote is a substring of a source.
5. An eval of 15 claims with known verdicts (Lab 7.1).
