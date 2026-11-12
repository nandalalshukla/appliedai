"""Lab 4.6 - Measure retrieval before you touch the prompt.

If the right chunk is not retrieved, no prompt can produce the right answer.
So you evaluate retrieval on its own, with a small labelled set:
question -> the chunk(s) that contain the answer.

Metrics:
  recall@k  - in what fraction of questions is a correct chunk in the top k?
  MRR       - mean reciprocal rank: 1/position of the first correct chunk
              (1.0 = always first, 0.5 = typically second, ...)

Run:  python modules/04-rag/labs/06_retrieval_eval.py
"""

from aikit.rag import HybridRetriever, load_corpus

chunks = load_corpus("data/handbook")
retriever = HybridRetriever(chunks)

# (question, text that the correct chunk must contain)
# Labelling by content instead of chunk id means the set survives re-chunking.
GOLD = [
    ("What does error STG-507 mean?", "STG-507 means"),
    ("How many failed logins before an account locks?", "5 failed login attempts"),
    ("How long is the password reset email valid?", "valid for 60 minutes"),
    ("What is the API rate limit on the Free plan?", "60 per minute"),
    ("How long do refunds take to arrive?", "5 to 10 business days"),
    ("Can I move my workspace to another region?", "cannot change region"),
    ("How are webhook deliveries signed?", "HMAC-SHA256"),
    ("I got billed twice, what now?", "duplicate is refunded"),            # paraphrase
    ("Can I get my money back on a yearly plan?", "within 30 days of purchase"),  # paraphrase
    ("I lost my phone with the authenticator app", "recovery codes"),      # paraphrase
]


def evaluate(search, k: int = 3) -> tuple[float, float]:
    hits, reciprocal = 0, 0.0
    for question, needle in GOLD:
        results = [c for c, _ in search(question, k)]
        ranks = [i for i, c in enumerate(results, start=1) if needle in c.text]
        if ranks:
            hits += 1
            reciprocal += 1 / ranks[0]
    return hits / len(GOLD), reciprocal / len(GOLD)


if __name__ == "__main__":
    systems = {
        "bm25": lambda q, k: retriever.bm25.search(q, k),
        "vector": lambda q, k: retriever.vectors.search(q, k),
        "hybrid": lambda q, k: retriever.search(q, k),
        "hybrid + filter(2026)": lambda q, k: retriever.search(q, k, {"updated": "2026"}),
    }
    print(f"{'system':<24}{'recall@3':>10}{'MRR':>8}")
    for name, search in systems.items():
        recall, mrr = evaluate(search)
        print(f"{name:<24}{recall:>10.2f}{mrr:>8.2f}")

    print("\nhybrid: questions where the correct chunk is NOT ranked first:")
    for question, needle in GOLD:
        top = retriever.search(question, 1)
        if not top or needle not in top[0][0].text:
            print("  -", question)

# This table is how retrieval work gets done. Change one thing (chunk size, the
# embedder, fusion weights, add rewriting), re-run, keep it only if the number
# moves. Ten questions is a toy; fifty real ones is a genuinely useful start.
#
# Try it:
# 1. Add 10 harder questions of your own (paraphrases, typos, two-part questions)
#    until hybrid recall drops below 1.0. Then run with AIKIT_EMBEDDER=st and compare.
# 2. Change max_words in load_corpus(...) to 30, then 400. Plot recall@3.
# 3. Plug the rewriter from Lab 4.4 in front of hybrid search and measure it.
