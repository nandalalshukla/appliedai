"""Lab 4.2 - Keyword vs vector vs hybrid search, and metadata filtering.

Keyword search (BM25) is exact: great for IDs, error codes, names.
Vector search is fuzzy: great for paraphrases. Each fails where the other wins.
Hybrid search runs both and merges the rankings.

Run:  python modules/04-rag/labs/02_hybrid_search.py
"""

from aikit.rag import HybridRetriever, load_corpus

chunks = load_corpus("data/handbook")
retriever = HybridRetriever(chunks)


def show(query: str, where=None):
    print(f"\nquery: {query!r}" + (f"   filter: {where}" if where else ""))
    rows = {
        "bm25  ": retriever.bm25.search(query, 3, where),
        "vector": retriever.vectors.search(query, 3, where),
        "hybrid": retriever.search(query, 3, where),
    }
    for name, hits in rows.items():
        print(f"  {name}: {[c.id for c, _ in hits]}")


# 1. An exact identifier. BM25 nails it: the token "507" appears in one chunk.
show("what does STG-507 mean")

# 2. A natural question. Both do fine; hybrid agrees with both.
show("how do I reset my password")

# 3. STALE DATA. Two documents describe the refund policy: the current one and
#    a superseded 2023 one. Similarity search cannot tell which is current -
#    they are both "about refunds". A metadata filter can.
show("refund window for monthly plans")
show("refund window for monthly plans", where={"updated": "2026"})

# Metadata filtering is how you enforce things similarity cannot express:
#   - freshness      (updated >= 2026)
#   - permissions    (tenant_id == this user's tenant)   <- a SECURITY requirement
#   - scope          (product == "billing")
# Filter BEFORE ranking (as aikit.rag does) so the top-k are all eligible.
#
# Try it:
# 1. Open aikit/rag.py and read rrf(). Why combine ranks rather than scores?
# 2. Give BM25 a weight of 2 in the fusion (add its ranking twice). When would
#    you want that?
# 3. Add `tenant: acme` to one file's front matter and filter on it. Now imagine
#    forgetting that filter in a multi-customer product. That is a data leak.
