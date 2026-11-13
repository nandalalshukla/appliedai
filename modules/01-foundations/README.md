# Module 1: Foundations - how LLMs actually behave

**Weeks 1-2.** By the end you can explain what a model is doing when it answers, predict several ways it will fail, and call one from code with full control over cost and errors.

Labs: [`labs/`](labs/) · Project unlocked: none yet (first project comes after Module 2)

---

## 1.1 What an AI engineer does

Three jobs are easy to confuse:

| Role | Works on | Typical day |
|---|---|---|
| ML researcher | New model architectures and training methods | Papers, experiments on GPUs |
| ML engineer | Training and serving models | Data pipelines, training runs, model servers |
| **AI engineer** | **Products built on top of existing models** | Prompts, retrieval, agents, evals, latency, cost |

An AI engineer treats the model as a powerful, unreliable component and builds a reliable system around it. Most of the work is ordinary software engineering (APIs, data, testing, monitoring) plus a new set of skills this course teaches: getting consistent behaviour from a probabilistic component, and *measuring* whether you succeeded.

You do not need to know how to train a neural network. You do need an accurate mental model of what the thing does. That is the rest of this module.

## 1.2 The mental model: a next-token predictor

A large language model (LLM) does one thing: **given a sequence of tokens, it outputs a probability for every possible next token.** Everything else is built on that.

Generating a reply is a loop:

```
text so far ──► model ──► probabilities for the next token ──► pick one ──► append ──► repeat
```

Hold on to five consequences. Each one explains a class of bugs you will meet.

1. **It predicts plausible text, not true text.** When the model lacks a fact, the most plausible continuation is still a confident, fluent sentence. This is a *hallucination*. It is not a glitch you can patch; it is the default behaviour whenever the answer is not well supported by the prompt or by training. You reduce it by giving the model the facts (Module 4) and by checking its work (Module 7).
2. **It has no memory between calls.** Each request starts from zero. A "conversation" exists only because your code resends the history every time ([Lab 1.4](labs/04_chat_loop.py)).
3. **It only knows its training data plus what you put in the prompt.** Training data stops at a *knowledge cutoff* date. It does not know today's date, your company's documents, or last week's news unless you provide them.
4. **It is not deterministic.** The "pick one" step samples from the probabilities, so the same prompt can produce different outputs ([Lab 1.2](labs/02_sampling.py)).
5. **Everything is tokens, and tokens cost money and time.** Input and output are both billed per token, and output is generated one token at a time, so long answers are slow.

> **A useful picture.** Think of the model as a brilliant new colleague with amnesia: wide knowledge, no context about your company, no memory of yesterday, and a habit of answering confidently even when unsure. Your job is to write the briefing, hand over the right documents, give them tools, and review their work.

## 1.3 Tokens

Models do not read characters or words. Text is first split into **tokens** by a *tokenizer*; common words become one token, rare words are split into pieces.

Run [Lab 1.1](labs/01_tokens.py). It trains a byte-pair-encoding (BPE) tokenizer: start with one token per byte, then repeatedly merge the most frequent adjacent pair into a new token. After 25 merges on a tiny corpus, `the` is a single token and `xylophone` is still eight.

What this means in practice:

- **Rule of thumb:** 1 token ≈ 4 characters ≈ ¾ of an English word. Code, rare words and many non-English scripts use more tokens per character, so they cost more.
- **Models are weak at character-level tasks** (counting letters, reversing strings, exact arithmetic on long numbers) because they never see characters. When you need exactness, give the model a tool that computes (Module 3).
- **Never estimate tokens with another provider's tokenizer.** Each model family has its own. Use the provider's token-counting endpoint when the number matters.

### The context window

The **context window** is the maximum number of tokens the model can consider at once: your system prompt, the whole conversation, any documents, tool definitions *and* the reply it is writing. Current models offer hundreds of thousands to a million tokens.

A big window does not remove the need to choose what goes in:

- You pay for every token on every call.
- More tokens means slower responses.
- Quality drops as context fills with irrelevant material; important details get less attention. Practitioners call this *context rot*.

Choosing what to put in the window is called **context engineering**, and it is the thread that runs through this whole course: prompts (Module 2), retrieval (Module 4), agent history (Module 5), memory (Module 6).

## 1.4 Sampling, and why "temperature = 0" is not a reliability plan

Run [Lab 1.2](labs/02_sampling.py). The model's scores become probabilities through *softmax*; **temperature** rescales the scores first. Low temperature concentrates probability on the top token; high temperature spreads it out.

Two things beginners get wrong:

- **Temperature 0 does not make outputs correct**, only repeatable-ish. A wrong answer at temperature 0 is wrong every time.
- **You often cannot set it.** Many current models, including current Claude models, manage sampling internally and reject `temperature`/`top_p` parameters. Reasoning models think before answering, and that thinking varies between runs.

So treat variation as a fact of life. Reliability comes from structure (Module 2), grounding (Module 4), validation and retries (Module 3), and measurement (Module 7).

## 1.5 The API: one endpoint to understand deeply

Run [Lab 1.3](labs/03_first_call.py). Here is the whole request:

```python
import anthropic

client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY from the environment

response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1000,
    system="You are a patient tutor. Answer in one sentence.",
    messages=[{"role": "user", "content": "What is a token?"}],
)
```

| Part | What it is | Notes |
|---|---|---|
| `model` | Which model answers | Bigger = smarter, slower, pricier |
| `system` | Standing instructions: role, rules, context | Not part of the conversation turns |
| `messages` | The conversation: alternating `user` and `assistant` | You send all of it every time |
| `max_tokens` | Hard cap on reply length | The model is not told about it; too low cuts the reply mid-sentence |

And the response:

| Field | Why you care |
|---|---|
| `content` | A **list of blocks** (`text`, `thinking`, `tool_use`). Never assume `content[0].text` exists |
| `stop_reason` | `end_turn`, `max_tokens`, `tool_use`, `refusal`. **Check it on every call.** A silent `max_tokens` cut is one of the most common production bugs |
| `usage` | `input_tokens`, `output_tokens`, plus cache counters. This is your bill |

### Thinking and effort

Modern models can reason privately before answering ("extended thinking"). On current Claude models this is on by default and adapts to the task; you steer how hard the model works with an *effort* setting (`low` to `max`). More effort means better answers on hard problems, with more tokens and time. For simple, high-volume tasks, use low effort or a small model. Thinking tokens count toward `max_tokens` and are billed as output, so leave headroom: a cap that is too tight can be used up before the visible answer starts. You will measure this trade-off in Module 8 rather than guess.

### Statelessness, in code

Run [Lab 1.4](labs/04_chat_loop.py). The entire "memory" of a chatbot is this line:

```python
history.append({"role": "assistant", "content": reply})
```

Every turn resends the full history, so the cost of a conversation grows with the *square* of its length: turn 50 pays again for turns 1-49. Managing that is Module 6.

### Streaming

Run [Lab 1.5](labs/05_streaming.py). Streaming returns tokens as they are produced. It does not speed up generation, but users start reading in under a second instead of staring at a spinner. Two numbers matter: **time to first token (TTFT)** and **total latency**. Stream anything a human waits for, and anything with a long output (long non-streamed requests can hit HTTP timeouts).

## 1.6 Errors you must handle from day one

A model API is a network service that is sometimes slow, overloaded, or rate-limited.

| Error | Meaning | What to do |
|---|---|---|
| 400 Bad Request | Your request is malformed | Fix the code. **Do not retry** |
| 401 / 403 | Bad key or no permission | Fix config. Do not retry |
| 429 Rate limit | Too many requests or tokens per minute | Wait (`retry-after` header), then retry with backoff |
| 500 / 529 | Provider error or overload | Retry with exponential backoff and jitter |
| Timeout | Request took too long | Retry; stream long requests |

```python
import anthropic

try:
    response = client.messages.create(...)
except anthropic.RateLimitError as e:
    wait = int(e.response.headers.get("retry-after", "30"))   # back off, then retry
except anthropic.APIStatusError as e:
    if e.status_code >= 500: ...                               # transient: retry
    else: raise                                                # your bug: fix it
except anthropic.APIConnectionError:
    ...                                                        # network: retry
```

The official SDK already retries 429 and 5xx twice with backoff. Know that it does, so you do not stack three layers of retries and turn one slow call into twenty.

## 1.7 Embeddings: meaning as numbers

Run [Lab 1.6](labs/06_embeddings.py). An **embedding model** is a different kind of model: text in, a fixed-length vector out (a few hundred to a few thousand numbers). It is trained so that texts with similar meaning get nearby vectors. Closeness is measured with **cosine similarity** (1 = same direction, 0 = unrelated).

This gives you *semantic search*: embed your documents once, embed the query, return the nearest documents. It finds "how to get your money back" for the query "refund" even with no shared words, which keyword search cannot do. It is the base of retrieval-augmented generation in Module 4.

The lab uses a dependency-free `HashEmbedder` so it runs anywhere; it only captures word overlap. Set `AIKIT_EMBEDDER=st` (after `pip install sentence-transformers`) to see a real semantic model fix the cases it misses. Seeing both is the point.

## 1.8 Other providers: what changes and what does not

Everything in this course transfers. The names differ:

| Concept | Claude API | OpenAI API | Gemini API |
|---|---|---|---|
| Standing instructions | `system` parameter | `developer`/`system` message, or `instructions` | `system_instruction` |
| Model's turn | role `assistant` | role `assistant` | role `model` |
| Tool call in reply | `tool_use` content block | `tool_calls` / function call item | `function_call` part |
| JSON-schema output | `output_config.format` | `response_format` / `text.format` | `response_schema` |
| Embeddings | Use a separate provider or open model | Built in | Built in |

If your employer uses a different provider, read its quickstart and port two labs. That takes an afternoon, and being able to do it is itself a job skill. Avoid hiding providers behind a "universal" wrapper while learning; the differences are exactly the things that bite in production.

## 1.9 Where LLMs are strong and weak

| Reliable | Unreliable without help |
|---|---|
| Rewriting, summarizing, translating | Facts not in the prompt (recent, private, niche) |
| Classifying and extracting from text | Exact arithmetic, counting, long precise copying |
| Writing and explaining code | Knowing what it does not know |
| Following clear, specific instructions | Following vague or conflicting instructions |
| Reasoning over material you provide | Staying consistent over very long contexts |

Almost every technique in the remaining modules moves a task from the right column to the left: retrieval supplies facts, tools supply exactness, evals reveal what the model does not know, context management keeps long work on track.

---

## Checkpoint

Answer without looking. If one is hard, re-read that section.

1. Why does a chatbot's cost per turn grow as the conversation gets longer?
2. A user reports that answers sometimes end mid-sentence. Which response field tells you why, and what are two fixes?
3. Why can an LLM not reliably count the letter "r" in "strawberry"?
4. Your manager says "set temperature to 0 so it stops making things up." Give two reasons this will not work.
5. What does an embedding model return, and how do you compare two results?
6. Which HTTP errors should you retry, and which should you never retry?
7. What three things besides the user's message consume context-window tokens?

## Exercises

1. **Token budget.** Write `estimate_cost(text, model)` using the 4-characters rule and the price table in `aikit/llm.py`. Estimate the cost of summarizing a 300-page book with each model.
2. **Robust caller.** Write `call_with_retry(client, **kwargs)` that retries 429/5xx/connection errors with exponential backoff and jitter, never retries 4xx, and raises a clear error when `stop_reason == "max_tokens"`. Test it with a `FakeClient` responder that fails twice and then succeeds.
3. **Trim the history.** Extend Lab 1.4 so the history never exceeds N messages. Find a conversation where trimming makes the bot give a wrong answer. Keep that example; you will fix it in Module 6.

## Go deeper

See [Module 1 in RESOURCES.md](../../RESOURCES.md#module-1-foundations). If you watch one thing: Andrej Karpathy's "Intro to Large Language Models".

Next: [Module 2: Prompting LLMs reliably](../02-prompting/README.md)
