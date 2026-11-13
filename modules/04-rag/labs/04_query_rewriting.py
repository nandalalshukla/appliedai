"""Lab 4.4 - Query rewriting: fix the question before you search.

Users do not write search queries. They write:
   "what about yearly ones?"       <- meaningless without the conversation
   "can I get my money back"       <- different words from the handbook
   "refunds and also 2FA resets"   <- two questions in one

Three rewrites, all done by a cheap model call before retrieval:
  1. standalone   - resolve pronouns and context from the chat history
  2. multi-query  - several phrasings, search each, fuse the results
  3. decompose    - split a compound question into parts

Run:  python modules/04-rag/labs/04_query_rewriting.py
"""

import json

from aikit import MODEL, get_client, text_of
from aikit.rag import HybridRetriever, load_corpus, rrf

retriever = HybridRetriever(load_corpus("data/handbook"))

REWRITE_SYSTEM = """You prepare search queries for a company handbook search engine.

Given a conversation and the user's latest message, return JSON:
{"queries": ["...", "..."]}

Rules:
- Each query must be understandable on its own: replace "it", "that", "yearly" etc.
  with what they refer to in the conversation.
- If the message asks several things, write one query per thing.
- Add one alternative phrasing using the vocabulary a formal policy document would use
  (for example "refund" rather than "money back", "annual" rather than "yearly").
- At most 4 queries. Do not answer the question."""


def rewrite(client, history: list[str], message: str) -> list[str]:
    convo = "\n".join(history) or "(no earlier messages)"
    response = client.messages.create(
        model=MODEL, max_tokens=4000, system=REWRITE_SYSTEM,
        messages=[{"role": "user", "content": f"<conversation>\n{convo}\n</conversation>\n\nLatest message: {message}"}],
    )
    try:
        queries = json.loads(text_of(response))["queries"]
        return [q for q in queries if isinstance(q, str) and q.strip()][:4] or [message]
    except (ValueError, KeyError, TypeError):
        return [message]  # rewriting failed: search with the original


CURRENT = {"updated": "2026"}  # skip superseded documents (Lab 4.2)


def search_all(queries: list[str], k: int = 3):
    rankings = [[c for c, _ in retriever.search(q, k=8, where=CURRENT)] for q in queries]
    return [c for c, _ in rrf(rankings)[:k]]


if __name__ == "__main__":
    history = ["user: How long do I have to ask for a refund on a monthly plan?",
               "assistant: 14 days from the charge."]
    message = "and what about yearly ones?"

    print("WITHOUT rewriting ->", [c.id for c, _ in retriever.search(message, 3, CURRENT)])

    client = get_client(script=[json.dumps({"queries": [
        "refund window for annual plans",
        "annual plan refund policy how many days",
    ]})])
    queries = rewrite(client, history, message)
    print("rewritten queries ->", queries)
    print("WITH rewriting    ->", [c.id for c in search_all(queries)])

# Another technique to know: HyDE (hypothetical document embeddings). Ask the
# model to write a made-up ANSWER, then search with that text. Answers look
# more like documents than questions do, so they often retrieve better.
#
# Costs: every rewrite is an extra model call (latency + money) before the
# user sees anything. Use a small fast model, and measure whether it helps
# (Lab 4.6) before paying for it on every request.
#
# Try it:
# 1. Send a message that needs no rewriting. Does the rewriter leave it alone?
# 2. Implement HyDE and compare retrieval on five paraphrased questions.
