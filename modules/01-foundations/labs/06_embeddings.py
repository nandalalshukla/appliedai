"""Lab 1.6 - Embeddings: turning meaning into numbers you can search.

An embedding model maps text to a vector (a list of numbers). Texts with
similar meaning land close together. "Close" is measured by cosine similarity.

Run:  python modules/01-foundations/labs/06_embeddings.py
      AIKIT_EMBEDDER=st python ...   (real semantic model; needs sentence-transformers)
"""

import numpy as np

from aikit.embed import get_embedder

DOCS = [
    "How do I reset my password?",
    "Steps to change your account password",
    "Our refund policy lasts 30 days",
    "How to get your money back after a purchase",
    "Best pizza dough recipe",
]

embedder = get_embedder()
doc_vectors = embedder.embed(DOCS)  # shape: (5, dim). Each row has length 1.
print(f"embedder: {type(embedder).__name__}, vector size: {doc_vectors.shape[1]}\n")


def search(query: str, k: int = 3):
    q = embedder.embed([query])[0]
    scores = doc_vectors @ q  # dot product of unit vectors = cosine similarity
    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), DOCS[i]) for i in top]


for query in ["forgot my password", "I want a refund"]:
    print(f"query: {query!r}")
    for score, doc in search(query):
        print(f"  {score:.3f}  {doc}")
    print()

# What to notice:
# - "forgot my password" finds the password docs: shared words.
# - With the default HashEmbedder, "I want a refund" may NOT rank "How to get
#   your money back" first: no shared words, and this embedder only sees
#   spelling. A real embedding model gets it right, because it was trained to
#   place paraphrases close together. Run with AIKIT_EMBEDDER=st to see it.
#
# This gap (meaning vs. exact words) is the central theme of Module 4.
#
# Try it:
# 1. Add 5 documents from your own life and search them.
# 2. Print the similarity between "bank of a river" and "bank account".
#    One vector per text cannot separate senses without context. Remember this
#    when you choose chunk sizes in Module 4.
