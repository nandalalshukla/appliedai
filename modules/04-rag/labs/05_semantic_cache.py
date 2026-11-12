"""Lab 4.5 - Semantic caching: do not pay twice for the same question.

An exact-match cache misses "How do I reset my password?" vs "how can i reset
my password". A semantic cache embeds the question and reuses a stored answer
when a previous question is close enough.

It is also an easy way to serve the WRONG answer to someone, so most of this
lab is about the guard rails.

Run:  python modules/04-rag/labs/05_semantic_cache.py
"""

import time
from dataclasses import dataclass

import numpy as np

from aikit.embed import get_embedder


@dataclass
class Entry:
    vector: np.ndarray
    question: str
    answer: str
    scope: str  # who may see this answer
    created: float


class SemanticCache:
    def __init__(self, threshold: float = 0.9, ttl_s: float = 3600):
        self.embedder = get_embedder()
        self.threshold, self.ttl_s = threshold, ttl_s
        self.entries: list[Entry] = []
        self.hits = self.misses = 0

    def get(self, question: str, scope: str = "public") -> str | None:
        q = self.embedder.embed([question])[0]
        now = time.time()
        best, best_score = None, 0.0
        for e in self.entries:
            if e.scope != scope or now - e.created > self.ttl_s:  # guard rails 1 and 2
                continue
            score = float(e.vector @ q)
            if score > best_score:
                best, best_score = e, score
        if best is not None and best_score >= self.threshold:
            self.hits += 1
            return best.answer
        self.misses += 1
        return None

    def put(self, question: str, answer: str, scope: str = "public") -> None:
        self.entries.append(Entry(self.embedder.embed([question])[0], question, answer, scope, time.time()))


def expensive_answer(question: str) -> str:
    time.sleep(0.2)  # stands in for retrieval + a model call
    return f"(generated answer to: {question})"


if __name__ == "__main__":
    cache = SemanticCache(threshold=0.9)
    questions = [
        "How do I reset my password?",
        "how do i reset my password",          # same question -> should hit
        "How do I reset my password please?",  # near-duplicate -> should hit
        "How do I delete my account?",         # similar WORDS, different meaning -> must miss
    ]
    for q in questions:
        start = time.perf_counter()
        answer = cache.get(q)
        source = "HIT " if answer else "MISS"
        if answer is None:
            answer = expensive_answer(q)
            cache.put(q, answer)
        print(f"{source} {1000 * (time.perf_counter() - start):6.1f} ms | {q}")
    print(f"\nhit rate: {cache.hits}/{cache.hits + cache.misses}")

# Guard rails, in order of how badly they bite:
# 1. SCOPE. "What is my balance?" has a different answer per user. Key the cache
#    by tenant/user/permissions, or do not cache personalised answers at all.
# 2. FRESHNESS. Cached answers go stale when documents change. Use a TTL and
#    clear entries when the underlying source is re-indexed.
# 3. THRESHOLD. Too low: "reset password" returns the answer for "delete
#    account". Too high: no hits. Tune it on real question pairs, and note the
#    right value depends on the embedding model.
# 4. NEGATION AND NUMBERS. "plans with 2FA" vs "plans without 2FA" embed almost
#    identically. So do "limit for 5 users" and "limit for 50 users".
# 5. Do not cache failures, refusals or low-confidence answers.
#
# Try it:
# 1. Lower the threshold until the "delete my account" question wrongly hits.
# 2. Add a second user scope and show their questions never hit each other's entries.
# 3. What should the hit-rate dashboard look like in a healthy system? (Module 8)
