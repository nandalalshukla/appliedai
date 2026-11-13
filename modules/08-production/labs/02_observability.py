"""Lab 8.2 - Observability: trace every request, or debug blind.

When a user says "the bot gave a wrong answer yesterday", you need to open
that exact request and see every step: what was retrieved, what prompt was
sent, what the model returned, how long each part took, and what it cost.

Run:  python modules/08-production/labs/02_observability.py
"""

import time

from aikit import MODEL, get_client, text_of
from aikit.llm import PRICES
from aikit.rag import HybridRetriever, format_context, load_corpus
from aikit.trace import Tracer

retriever = HybridRetriever(load_corpus("data/handbook"))
client = get_client(script=[
    '{"queries": ["refund window annual plan"]}',
    "Annual plans can be refunded within 30 days of purchase [1].",
])


def answer(question: str, tracer: Tracer) -> str:
    with tracer.span("handle_request", user="u_42", prompt_version="rag-v3") as root:

        with tracer.span("rewrite_query") as s:
            r = client.messages.create(model=MODEL, max_tokens=4000,
                                       system="Rewrite as a search query. Return JSON.",
                                       messages=[{"role": "user", "content": question}])
            tracer.record_usage(s, r, MODEL)

        with tracer.span("retrieve", k=3) as s:
            time.sleep(0.02)  # stands in for a search-engine round trip
            hits = [c for c, _ in retriever.search("refund window annual plan", 3, {"updated": "2026"})]
            s.set(chunks=[c.id for c in hits])  # log WHAT was retrieved, not just how many

        with tracer.span("generate") as s:
            r = client.messages.create(model=MODEL, max_tokens=4000,
                                       system="Answer from the documents and cite them.",
                                       messages=[{"role": "user", "content": f"{format_context(hits)}\n\n{question}"}])
            tracer.record_usage(s, r, MODEL)
            reply = text_of(r)

        with tracer.span("output_guard") as s:
            s.set(cited="[1]" in reply)

        p_in, p_out = PRICES.get(MODEL, PRICES["claude-opus-5-5"])
        cost = (tracer.total("input_tokens") * p_in + tracer.total("output_tokens") * p_out) / 1e6
        root.set(usd=round(cost, 6))
        return reply


if __name__ == "__main__":
    tracer = Tracer(path="runs/traces.jsonl")
    print(answer("can I get my money back on a yearly plan?", tracer), "\n")
    tracer.print_tree()
    print("\nspans appended to runs/traces.jsonl (one JSON object per line)")

# What a trace must let you answer:
#   WHAT happened?     every model call, tool call and retrieval, in order, nested
#   WITH WHAT?         prompt version, model, retrieved chunk ids, tool arguments
#   HOW LONG?          per step - is the time in retrieval or in generation?
#   HOW MUCH?          tokens and dollars per step and per request
#   FOR WHOM?          user / tenant / session ids, so you can find it again
#   DID IT WORK?       stop_reason, errors, guardrail results, user feedback
#
# The dashboard numbers that come out of traces:
#   latency p50 / p95 / p99, time to first token
#   error rate, by type (rate limit, timeout, refusal, max_tokens, tool error)
#   tokens and cost per request, per user, per feature
#   cache hit rate (prompt cache and semantic cache)
#   steps per agent run; share of runs hitting a limit
#   quality: online eval pass rate, thumbs-down rate, escalation rate
#
# Privacy: traces contain user data. Redact PII, restrict access, set retention.
#
# At work you will use OpenTelemetry plus an LLM observability tool (Langfuse,
# LangSmith, Arize Phoenix, Braintrust, Datadog...). They all store this shape.
#
# Try it:
# 1. Make retrieve raise an exception. Look at the tree: is the failing step obvious?
# 2. Feed Agent's on_event hook into a Tracer so each tool call becomes a span.
# 3. Write a 10-line script that reads runs/traces.jsonl and prints p50/p95
#    latency for the "generate" span.
