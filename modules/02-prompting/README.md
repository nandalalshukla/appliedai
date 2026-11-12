# Module 2: Prompting LLMs reliably

**Weeks 3-4.** A demo needs a prompt that works once. A product needs a prompt that works on the ten-thousandth input written by a stranger. This module is about the second kind.

Labs: [`labs/`](labs/) · Design problem: [Fact-checking agentic system](../09-system-design/01-fact-checking-system.md) · Project unlocked: [P1 Support triage service](../../projects/01-support-triage/README.md)

---

## 2.1 The mental model for building around LLMs

Module 1 gave you the model of the *model*. This is the model of the *system*:

> **The LLM is an unreliable function inside a reliable program.** Code owns control flow, validation, state and side effects. The model owns judgment over language.

Four working rules follow.

1. **The model only knows what is in the context.** If a new hire would need a piece of information to do the task, the model needs it too. Most "the model is dumb" bugs are missing-context bugs.
2. **Do in code what code can do.** Dates, arithmetic, lookups, sorting, format checks: none of these belong in a prompt. Every responsibility you remove from the model is one that can no longer fail randomly.
3. **Assume every output can be wrong, and decide in advance what happens then.** Validate, retry, fall back, or hand off to a human. Design the failure path before the happy path.
4. **You cannot improve what you do not measure.** A prompt change that fixes your one test input may break twenty others. Keep a set of test inputs from day one (five is fine); it grows into your eval suite in Module 7.

A quick decision ladder. Always start at the top and move down only when the simpler rung measurably fails:

```
1. Single prompt                      cheapest, fastest, easiest to debug
2. Prompt + examples / structure
3. Prompt chain (fixed steps in code)
4. Retrieval (Module 4)
5. Tools (Module 3)
6. Agent loop (Module 5)
7. Multiple agents (Module 6)         most expensive, hardest to debug
```

## 2.2 Drafting reliable prompts

Run [Lab 2.1](labs/01_prompt_anatomy.py). The vague prompt and the specific prompt do the same task; only one is safe to put behind an API.

### The anatomy

| Part | Question it answers | Example |
|---|---|---|
| Role and purpose | Who are you, and who uses the output? | "You write one-line summaries for support agents who scan hundreds per hour." |
| Task | What exactly do I do? | "Lead with the main problem, then what the customer intends to do." |
| Constraints | What are the limits? | "One sentence, at most 20 words. Only facts from the review." |
| Edge cases | What about the awkward inputs? | "If no problem is mentioned, write `No issue reported.`" |
| Examples | What does good look like? | 3-5 varied input/output pairs |
| Output format | What shape do I return? | "Plain text, no preamble" or a JSON schema |
| Data | What am I working on? | `<review>...</review>` |

### Techniques that consistently help

- **Explain why, not just what.** "At most 20 words, because agents scan these on a phone" lets the model handle cases your rules did not cover. Bare commands get followed literally and brittlely.
- **Say what to do, not what to avoid.** "Write in plain paragraphs" works better than "no markdown". Naming the unwanted thing can pull the model toward it.
- **Separate instructions from data with tags** such as `<document>...</document>`. It prevents confusion and is your first (partial) defence against prompt injection.
- **Put long documents first and the question last.** The model reads top to bottom; a question after the material is answered better.
- **Give the model an exit.** "If the answer is not in the document, reply `NOT_IN_DOCUMENT`." Without one, it will produce *something*.
- **Do not shout.** `CRITICAL: YOU MUST ALWAYS...` made older models pay attention. Current models over-apply shouted rules. State the rule calmly, once.
- **The colleague test.** Hand your prompt to a person with no context. Could they do the task well? Whatever they would ask, add to the prompt.

### System prompt vs user message

Put the stable parts (role, rules, examples, format) in `system`, and the per-request data in the `user` message. It keeps your template clean, and Module 8 shows it also makes prompt caching work, which can cut cost by up to 90%.

## 2.3 Few-shot prompting and chain-of-thought

Run [Lab 2.2](labs/02_few_shot_cot.py).

**Few-shot prompting** means putting worked examples in the prompt. It is the most reliable way to communicate fuzzy rules, tone and format. Examples are strong medicine:

- Aim them at the **boundaries**, where two labels are easy to confuse. Easy examples teach nothing.
- **Vary them.** The model copies whatever is constant across examples: length, phrasing, even which label appears most.
- Keep them **correct**. One wrong example is worse than none.
- 3-5 well-chosen examples usually beat 20 random ones.

**Chain-of-thought (CoT)** means asking the model to reason before it answers. It helps because generation is left to right: an answer written *after* reasoning can depend on it; an answer written *before* cannot.

- With today's reasoning models, built-in thinking does most of this for you. A high-level "think carefully about the root problem" beats a rigid step-by-step script.
- Visible reasoning is still worth having in a `reasoning` field or tag: when an answer is wrong, the reasoning usually shows which piece of context was missing.
- **Order matters.** Reasoning first, answer second, in tags and in JSON schemas alike.
- Caveat: stated reasoning is a helpful trace, not a guaranteed-faithful account of what happened inside the model. Use it for debugging, not as proof.

**Prompt chaining** is the code-level version: split a task into steps, each a separate call whose output feeds the next (extract → classify → draft → review). Each step gets a simpler prompt and can be tested alone. A reviewing step, where a second call critiques the first call's draft, is the single most useful chain.

## 2.4 Structured outputs and their gotchas

Run [Lab 2.3](labs/03_structured_outputs.py). Programs need data. There are three ways to get it, in increasing reliability:

| Method | How | Reliability |
|---|---|---|
| Ask nicely | "Reply in JSON" | Often valid; sometimes wrapped in prose or code fences |
| Tags | "Put the answer in `<answer>` tags" | Good for one or two fields; easy to parse |
| **Schema-constrained output** | Send a JSON schema; the provider restricts generation to it | Shape is guaranteed |

Use the third for anything your code consumes. With the Claude SDK:

```python
response = client.messages.parse(model=MODEL, max_tokens=2000, messages=[...], output_format=Ticket)
ticket = response.parsed_output      # a validated Pydantic object
```

Constrained output guarantees the **shape**. It guarantees nothing about the **content**. The gotchas:

1. **Field order is reasoning order.** Put `reasoning` before `category`. Decisions that come first are made without the reasoning.
2. **Required fields invite invention.** If the text has no order ID and `order_id` is a required string, you will get a plausible fake. Make it `Optional` and say when to use `null`.
3. **Field names and descriptions are prompt text.** `summary` is vague; `summary: "At most 15 words, for a support agent"` is an instruction.
4. **Truncation and refusal still happen.** If `stop_reason` is `max_tokens`, the JSON is cut off; if `refusal`, there is none. Check before parsing.
5. **Valid is not correct.** Verify what you can in code: does the extracted ID appear in the source? Is the date in range? Does the total equal the sum of the lines?
6. **Schemas have limits.** No recursion, limited numeric and string constraints, varying by provider. Keep schemas flat; enforce ranges in code.
7. **Large schemas lower quality.** Twenty nested fields in one call is worse than two calls with ten each.
8. **Prefer enums** for anything your code branches on. Free text means string-matching bugs.
9. **A schema is part of the prompt.** Changing it changes behaviour. Version and test it.
10. **Old tricks may be gone.** "Prefilling" the start of the assistant reply with `{` is rejected by current Claude models. Use schema-constrained output instead.

## 2.5 Prompt failure modes

Run [Lab 2.4](labs/04_failure_modes.py). Learn to recognize these by their symptoms:

| Failure | Symptom | Fix |
|---|---|---|
| **Prompt injection** | Text inside the *data* changes the model's behaviour | Tag untrusted data, tell the model it is data, and above all limit what the model is allowed to do |
| **Hallucination** | Fluent, specific, unsupported answer | Supply the facts; add an "I don't know" path; require quotes or citations; verify |
| **Conflicting instructions** | Behaviour flips between runs | One rule per topic; state which rule wins |
| **Lost in the middle** | A rule buried in a long prompt is ignored | Shorten; move key rules to the start or end; structure with headings or tags |
| **Example over-fitting** | Outputs mimic the examples too closely | More varied examples; say "these are illustrations, not templates" |
| **Silent truncation** | Half an answer parsed as whole | Check `stop_reason`; raise `max_tokens` |
| **Instruction drift** | Rules forgotten late in a long conversation | Restate key rules near the end of the context; trim history |
| **Sycophancy** | Model agrees with a wrong premise in the question | Ask it to check the premise first; ask neutrally worded questions |
| **Format drift** | "Here is the JSON you asked for: ..." | Schema-constrained output |
| **Over-literal compliance** | Follows the words, misses the intent | Explain the purpose of the task |

**Prompt injection deserves special respect.** Any text the model reads (a web page, an email, a PDF, a tool result) can contain instructions, and the model has no built-in way to tell your instructions from an attacker's. Delimiters and warnings lower the odds; they are not a security boundary. The real defences are architectural: least-privilege tools, human approval for risky actions, and never letting untrusted content and dangerous capabilities meet in one context. Modules 3, 5 and 7 build these.

### Debugging a prompt

When output is wrong, work through this in order:

1. **Read the exact prompt that was sent** (the rendered one, with variables filled). Half of all prompt bugs are template bugs: an empty variable, the wrong document, a stray instruction.
2. **Was the needed information actually in the context?**
3. **Is the instruction ambiguous or contradicted elsewhere?**
4. **Read the model's reasoning**, if you asked for it.
5. **Add the failing input to your test set**, then fix the prompt, then re-run *all* test inputs.

## 2.6 Infrastructure around prompts

Run [Lab 2.5](labs/05_prompt_registry.py). Once a prompt matters, treat it as a production asset:

| Need | Minimal version | Why |
|---|---|---|
| **Templates** | Variables rendered with strict checks | A missing variable should crash, not send `{review}` to the model |
| **Versioning** | Name + version + content hash | "What changed?" is the first question in every incident |
| **Config-driven rollout** | Active version in config | Roll back in seconds without a deploy |
| **Logging** | Version, model, rendered input, output, tokens, latency per call | You cannot debug what you did not record |
| **Evaluation gate** | New version must match or beat the old on your test set | Stops regressions (Module 7) |
| **A/B testing** | Send a slice of traffic to the candidate | Offline tests miss real-user behaviour |

Other pieces you will meet at work: a **model gateway** (one internal service in front of all providers, for keys, rate limits, fallbacks and cost tracking), **prompt caching** (Module 8), and **guardrails** (input and output checks, Module 7).

One rule that saves careers: **a model upgrade is a prompt change.** A new model version reads the same prompt differently. Re-run your evals before switching, every time.

## 2.7 System One models: Jev and Clairic

Not every step in a pipeline needs a model that writes text. Many steps are **decisions** ("is this fraud?", "which queue?") or **extractions** ("what is the invoice total?"). Using a large generative model for these is like hiring a novelist to tick boxes: it works, slowly and expensively, and you then have to parse prose back into a value.

In late 2026 a class of non-generative models aimed at these steps appeared under the name **System One models**, after Daniel Kahneman's fast, automatic "System 1" thinking (as opposed to slow, deliberate "System 2"):

- **Jev** (TypeSafe AI, September 2026) is a *decision* model. You give it the current state and a list of questions; it evaluates them in parallel and returns typed decisions with confidence scores. No chat, no generated text.
- **Clairic** (Cloudflare, preview on Workers AI, October 2026) is an *extraction* model. It reads text and images and returns typed values (spans, numbers, dates, lists) in a single forward pass, with a confidence for each and `null` when the input does not determine a field.

The proposed division of labour is a pipeline: extraction models turn raw input into typed values, decision models turn values into decisions, and LLMs turn decisions into words.

> **Read this with care.** These models are new. At the time of writing, the published speed, cost and accuracy numbers come from the vendors themselves and have not been independently reproduced. Treat them as claims to test on your own data, not facts. Sources are listed in [RESOURCES.md](../../RESOURCES.md#system-one-models).

What will outlast any specific product is the **architecture**, which [Lab 2.6](labs/06_system_one_gate.py) builds with a stand-in classifier:

```
input ─► fast typed step (cheap, confidence score)
            ├─ confident ──────► act in code
            └─ not confident ──► escalate to an LLM (or a human)
```

The engineering questions are the same whatever sits in the fast slot (a System One model, a small fine-tuned classifier, or a cheap LLM):

- **Is the confidence calibrated?** If the model says 0.9, is it right about 90% of the time? Measure on labelled data.
- **Where do you set the threshold?** It trades cost against error rate. Choose it from data.
- **What share of traffic takes the fast path?** That is your saving.
- **Log disagreements** between the fast and slow paths; they are the best eval examples you will ever get.

---

## Checkpoint

1. Name the seven parts of a reliable prompt. Which three are most often missing?
2. Why should the `reasoning` field come before the `decision` field in a schema?
3. Your extraction returns valid JSON with an order ID that is not in the email. What caused it, and what are two fixes?
4. Why are delimiters not a complete defence against prompt injection? What is?
5. A prompt edit fixed the bug you were chasing. What must you do before shipping it?
6. When would you put a fast typed-decision step in front of an LLM, and how would you choose its threshold?
7. What five things should you log for every model call?

## Exercises

1. **Rewrite three prompts.** Take three prompts you have used with a chat assistant and rewrite them using the anatomy table. Run old and new five times each and count how many outputs you could use without editing.
2. **Retry on validation failure.** Extend Lab 2.3: when a code check fails (such as the invented order ID), call the model again with the error message appended, at most twice. This "validate and re-ask" loop is a production staple.
3. **Break your own prompt.** Write ten adversarial inputs for Lab 2.2 (empty message, another language, two problems at once, an injection attempt, 5,000 words). Record what happens. This file is the first draft of your eval set.

## Project 1

You now have everything needed for [P1: Support triage service](../../projects/01-support-triage/README.md). Build it before moving on.

## Go deeper

[Module 2 in RESOURCES.md](../../RESOURCES.md#module-2-prompting).

Next: [Module 3: Tool use](../03-tool-use/README.md)
