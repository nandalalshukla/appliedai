"""Lab 1.2 - Why the same prompt gives different answers.

A model outputs a score (a "logit") for every possible next token. Sampling
turns scores into one chosen token. This lab does that by hand.

Run:  python modules/01-foundations/labs/02_sampling.py
"""

import numpy as np

# Pretend the prompt is "The capital of France is" and these are the scores.
TOKENS = [" Paris", " a", " the", " Lyon", " beautiful", " not"]
LOGITS = np.array([9.0, 5.0, 4.5, 4.0, 3.5, 1.0])


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = logits / temperature
    z = z - z.max()  # numerical stability
    p = np.exp(z)
    return p / p.sum()


def sample(logits, temperature, rng) -> str:
    if temperature == 0:  # greedy: always the top token
        return TOKENS[int(np.argmax(logits))]
    return TOKENS[rng.choice(len(TOKENS), p=softmax(logits, temperature))]


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    for t in [0.2, 1.0, 2.0, 5.0]:
        probs = softmax(LOGITS, t)
        table = "  ".join(f"{tok.strip()}={p:.2f}" for tok, p in zip(TOKENS, probs))
        draws = [sample(LOGITS, t, rng).strip() for _ in range(12)]
        print(f"temperature={t}\n  probabilities: {table}\n  12 samples:    {draws}\n")

    # What to notice:
    # - Low temperature sharpens the distribution: almost always "Paris".
    # - High temperature flattens it: more variety, more nonsense.
    # - Even at temperature 1.0 the model sometimes picks an unlikely token, and
    #   every later token is conditioned on that choice. This is one root of
    #   hallucination and of run-to-run variation.
    #
    # Try it:
    # 1. Add top-k sampling: keep only the k highest logits before softmax.
    # 2. Add top-p ("nucleus") sampling: keep the smallest set of tokens whose
    #    probabilities add up to p.
    #
    # Practical note: many current models (including current Claude models) no
    # longer let you set temperature/top_p; they manage sampling themselves.
    # So you cannot rely on "temperature=0" for consistency. You get
    # consistency from structured outputs, clear prompts and evals instead.
