# Project 6 (Capstone): Production support copilot

**After Module 8 · 20-25 hours · Skills: everything, plus API design, streaming, guardrails, caching, tracing, budgets, deployment**

## What you will build

A deployed HTTP service that answers support questions from a knowledge base, the way a real team would ship it:

```
POST /ask ─► auth ─► rate limit ─► budget ─► input guard ─► semantic cache
          ─► rewrite ─► retrieve ─► generate (streamed) ─► citation check ─► trace + accounting
GET /metrics   requests, cache hit rate, p50/p95 latency, spend per tenant
```

```bash
curl -N -X POST localhost:8000/ask -H "x-api-key: demo-key" \
     -H "content-type: application/json" -d '{"question": "What does STG-507 mean?"}'

event: status
data: {"message": "Searching the handbook"}

event: token
data: {"text": "Error code STG-507 means the workspace has reached its storage quota. [1]"}

event: done
data: {"sources": [{"index": 1, "source": "storage.md", ...}], "trace_id": "049c5a29..."}
```

This is the project you lead with on your CV. It shows that you can take an AI feature from an idea to something that has limits, logs, tests and a URL.

## Before you start

- Finish Modules 7 and 8. You need Project 2 (retrieval and answering) and Project 5 (evals).
- Working folder: `projects/06-capstone/my_app/`.
- New tools: [FastAPI](https://fastapi.tiangolo.com/) (web framework) and `uvicorn` (server). Both are in `requirements.txt`. If you have never used FastAPI, do its official tutorial's first three pages (about 30 minutes).

Build it in mock mode with tests, then switch to live mode.

---

## Milestone A: A working API

### Step 1: Hello, service

**Do:** create `app.py` with a FastAPI app and `GET /health` returning `{"status": "ok"}`.

```bash
uvicorn app:app --app-dir projects/06-capstone/my_app --reload --port 8000
```

**Check:** `curl localhost:8000/health`. Open `localhost:8000/docs` for the generated API page.

**If it fails:** "Address already in use" means another server holds the port; use `--port 8001`.

### Step 2: A non-streaming `/ask`

**Do:** define a request model `AskRequest(question: str, session_id: str = "default")`. Load the corpus and build the retriever **once at startup** (module level), not per request. Implement `POST /ask`: retrieve, build the prompt, call the model, return `{"answer": ..., "sources": [...]}`.

**Check:** a `curl` POST returns a cited answer.

**Step 2b:** write your first test with `fastapi.testclient.TestClient`, asserting status 200 and a citation in the answer. From now on, every step adds a test.

### Step 3: Authentication

**Do:** require an `x-api-key` header. Look it up in a dict of accounts (`tenant`, `daily_budget_usd`, `requests_per_minute`). Return 401 otherwise. Use a FastAPI dependency so every route can reuse it.

**Check:** a test that a request without a key gets 401.

> In a real deployment, keys live in a database or secret manager, hashed. The dict is a stand-in; say so in your README.

### Step 4: Streaming

**Goal:** the user sees words within a second.

**Do:** return a `StreamingResponse` with media type `text/event-stream`. Inside a generator, use `client.messages.stream(...)` and yield one server-sent event per text piece:

```python
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
```

Send `status` events ("Searching the handbook") before generation, `token` events during it, and a final `done` event carrying the sources and a trace ID.

**Check:** `curl -N` shows events arriving one by one. Update your test to parse events.

**If it fails:** if everything arrives at once, your client is buffering; `curl` needs `-N`. If a proxy sits in front, it may need buffering disabled.

## Milestone B: Guard it

### Step 5: Input guardrails

**Do:** before any model call: reject empty or over-long questions (422), and redact card numbers and email addresses with regular expressions, so they reach neither the model nor your logs.

**Check:** tests for the empty case and for redaction.

### Step 6: Output check and retraction

**Goal:** never leave an unverified answer standing.

**Do:** after the stream finishes, check `stop_reason` and verify citations in code (as in Project 2). Tokens are already on the user's screen, so on failure send a `retract` event with a safe replacement; the front end replaces the text.

**Check:** a test that forces a bad citation (in mock mode, a question containing a trigger word) and asserts a `retract` event and no sources.

> **The trade-off you just made:** streaming means you show text before you can verify it. The alternatives are to buffer the whole answer (slow first token, fully verified) or to stream and retract (fast, occasionally visibly corrected). Know which one your product needs, and be able to defend it.

### Step 7: Rate limits and budgets

**Do:**

- A sliding-window rate limiter per API key. Over the limit → 429 with a `Retry-After` header.
- Track spend per tenant per day from each response's `usage`. At the daily budget → 402 with a clear message.
- Run these checks **before** spending any tokens.

**Check:** tests for 429 and 402.

> A budget enforced in code is the difference between a bug and an incident.

### Step 8: Errors inside a stream

**Do:** wrap the generator body in `try/except`. On an exception, yield an `error` event with a friendly message and the trace ID, and count it. Use `finally` to record latency and spend even when things fail.

**Check:** make retrieval raise deliberately; the client receives an `error` event, not a hung connection.

## Milestone C: Make it efficient and observable

### Step 9: Conversation state and rewriting

**Do:** keep per-session history keyed by `tenant:session_id`. Rewrite follow-ups into standalone queries (Project 2, Step 5), with a fallback to the original question.

**Check:** a two-request test where the second question is "and for annual plans?".

> In-memory sessions vanish on restart and do not work with more than one server process. Note Redis or a database as the production choice.

### Step 10: Prompt caching

**Do:** put all stable instructions in a `system` block with `cache_control`, and everything that varies (documents, question) in the user message. Never put the time, the user's name or a request ID in the system block.

**Check (live mode):** make two requests and log `usage.cache_read_input_tokens`. If the stable prefix is long enough for your model's minimum, the second shows cache reads. If it is zero, read Module 8.1's list of cache breakers. (Short system prompts fall below the minimum; that is expected, and worth stating.)

### Step 11: Semantic cache

**Do:** cache grounded answers by question embedding, **keyed by tenant**, with a TTL. Use it only for the first turn of a session, because follow-ups depend on history. Never cache retracted or not-found answers.

**Check:** a test that the same question in a new session returns `"cached": true`.

### Step 12: Tracing and metrics

**Do:**

- Wrap the request in a `Tracer` with spans for `rewrite`, `retrieve`, `generate` and `citation_check`. Record model, tokens, retrieved chunk IDs, prompt version and cost. Write spans to a JSONL file. Return the `trace_id` to the client.
- `GET /metrics` returns request count, errors, blocked requests, retractions, cache hit rate, p50 and p95 latency, and spend per tenant.

**Check:** given a `trace_id` from a response, you can find every step of that request in the trace file.

## Milestone D: Prove it and ship it

### Step 13: Evals in CI

**Do:** add a suite to your Project 5 harness that calls your pipeline (not the HTTP layer) on 15+ questions, including unanswerable ones and injection attempts. Gate on it.

**Check:** the workflow runs your API tests and the eval gate on every push.

### Step 14: Load test

**Do:** write a script that sends 50 concurrent requests (mock mode) and reports p50 and p95 latency and error count.

**Check:** no errors; you can state your throughput. Then find the first thing that breaks as you raise concurrency.

### Step 15: Deploy

**Do:**

1. Write a `Dockerfile` (Python slim image, install requirements, run `uvicorn` on `0.0.0.0`).
2. Deploy to any host with a free or cheap tier (Render, Fly.io, Railway, Google Cloud Run, a small VM).
3. Set `ANTHROPIC_API_KEY` as a **secret in the host's settings**, never in the image or the repository. Set a low spending limit on the key.
4. Put a daily budget on the demo API key.

**Check:** `curl https://your-app/health` works from another network.

**If it fails:** the three usual causes are listening on `127.0.0.1` instead of `0.0.0.0`, the wrong port (many hosts provide a `PORT` variable), and a missing secret.

### Step 16: A small front end (optional, recommended)

**Do:** one HTML page with a text box that reads the event stream with `fetch` and appends tokens, shows sources under the answer, and handles `retract` and `error` events. People who review portfolios click links; give them something to click.

### Step 17: Write it up

**Do:** a README with: an architecture diagram, how to run it, the eval table, a cost-per-request estimate, latency numbers, three production gotchas you hit, known limitations, and what you would do next. A two-minute demo video helps.

---

## Done when

- [ ] `/ask` streams cited answers with status, token and done events
- [ ] Auth, rate limiting and a daily budget, all tested
- [ ] Input guardrails with PII redaction; output check with retraction
- [ ] Errors inside the stream reach the client cleanly
- [ ] Session history with query rewriting
- [ ] Cacheable prompt structure; tenant-scoped semantic cache
- [ ] Traces per request; a `/metrics` endpoint
- [ ] Tests and an eval gate in CI
- [ ] Deployed at a public URL with a budget
- [ ] A README with numbers

## Compare with the reference

[`solution/app.py`](solution/app.py) and [`solution/test_app.py`](solution/test_app.py):

```bash
pytest projects/06-capstone/solution -q
uvicorn app:app --app-dir projects/06-capstone/solution --port 8000
```

The reference stops at Step 12; deployment and the front end are yours.

## Stretch goals

1. **Actions.** Add an agent path with a `create_ticket` tool for questions the handbook cannot answer, behind an approval rule and an idempotency key.
2. **Background runs.** Long agent tasks on a queue with checkpoints; the client polls or subscribes for progress.
3. **Fallbacks.** On a provider overload, retry, then fall back to a second model, then to a clear degraded message.
4. **Feedback loop.** A `/feedback` endpoint storing thumbs up/down against the trace ID; a script that turns thumbs-down traces into candidate eval cases.
5. **OpenTelemetry.** Export your spans to a real tracing backend.
6. **Multi-tenant corpus.** Each tenant has its own documents; prove with a test that one tenant can never retrieve another's.

## How to talk about this in an interview

"I shipped a streaming RAG service. Requests are authenticated, rate limited and budgeted before any tokens are spent. Answers stream for a fast first token, and citations are verified after generation; if verification fails the client receives a retraction. Every request is traced with tokens and cost, an eval gate runs in CI, and the semantic cache is scoped per tenant so it cannot leak across customers. I can walk you through the trade-off between streaming and verifying before display."
