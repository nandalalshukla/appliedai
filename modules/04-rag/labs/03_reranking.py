"""Lab 4.3 - Re-ranking: bi-encoders retrieve, cross-encoders decide.

BI-ENCODER   (what vector search uses): embeds the query and each document
             SEPARATELY, then compares vectors. Documents are embedded ahead
             of time, so search is fast - but the query and document never
             "see" each other.
CROSS-ENCODER: reads the query and ONE document TOGETHER and outputs a
             relevance score. Much more accurate, far too slow to run over a
             whole corpus.

So production search is two stages:
    stage 1: cheap retrieval pulls ~50-100 candidates  (optimise for RECALL)
    stage 2: a re-ranker reorders them, keep the top 5 (optimise for PRECISION)

This lab re-ranks with an LLM (it runs anywhere). The same function shape
works for a cross-encoder model or a hosted re-rank API; see the bottom.

Run:  python modules/04-rag/labs/03_reranking.py
"""

import json

from aikit import MODEL, get_client, text_of
from aikit.rag import Chunk, HybridRetriever, load_corpus

chunks = load_corpus("data/handbook")
retriever = HybridRetriever(chunks)

RERANK_SYSTEM = """You rank documents by how well they answer a question.
Return a JSON list of document indexes, most useful first. Include only documents
that help answer the question; leave out the rest. Reply with the JSON list only."""


def llm_rerank(client, query: str, candidates: list[Chunk], keep: int = 3) -> list[Chunk]:
    listing = "\n".join(f"[{i}] {c.text}" for i, c in enumerate(candidates))
    response = client.messages.create(
        model=MODEL, max_tokens=2000, system=RERANK_SYSTEM,
        messages=[{"role": "user", "content": f"Question: {query}\n\nDocuments:\n{listing}"}],
    )
    try:
        order = [int(i) for i in json.loads(text_of(response))]
    except (ValueError, TypeError):
        return candidates[:keep]  # re-ranker failed: fall back to the stage-1 order
    seen, ranked = set(), []
    for i in order:  # never trust indexes from a model: range-check and de-duplicate
        if 0 <= i < len(candidates) and i not in seen:
            seen.add(i)
            ranked.append(candidates[i])
    return ranked[:keep]


if __name__ == "__main__":
    query = "My card was charged two times this month, what happens now?"
    candidates = [c for c, _ in retriever.search(query, k=8)]
    print("stage 1 (hybrid, top 8):", [c.id for c in candidates])

    target = next(i for i, c in enumerate(candidates) if "Double charges" in c.text)
    client = get_client(script=[json.dumps([target, (target + 2) % len(candidates)])])
    top = llm_rerank(client, query, candidates)
    print("stage 2 (re-ranked):     ", [c.id for c in top])
    print("\ntop result:\n ", top[0].text[:200], "...")

# Using a real cross-encoder instead (pip install sentence-transformers):
#
#   from sentence_transformers import CrossEncoder
#   model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
#   scores = model.predict([(query, c.text) for c in candidates])
#   ranked = [c for _, c in sorted(zip(scores, candidates), key=lambda x: -x[0])]
#
# Trade-offs:        latency        cost         quality
#   cross-encoder    ~10-100 ms     tiny         good
#   re-rank API      ~100-300 ms    per request  very good
#   LLM re-rank      ~1-5 s         highest      very good, and can follow instructions
#
# Try it:
# 1. Re-ranking cannot rescue a document stage 1 never retrieved. Set k=2 in
#    stage 1 and see whether the right chunk is still a candidate.
# 2. Make the fake re-ranker return [99, "x", 0, 0]. Does llm_rerank survive?
