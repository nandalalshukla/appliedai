"""Lab 1.1 - Build a tokenizer (byte-pair encoding) from scratch.

Models never see letters or words. They see integers called tokens. This lab
trains a tiny BPE tokenizer so you can watch tokens being invented.

Run:  python modules/01-foundations/labs/01_tokens.py
"""

from collections import Counter

CORPUS = (
    "the cat sat on the mat. the cat ate the rat. "
    "tokenization turns text into tokens. tokens are the units a model reads. "
) * 20


def most_common_pair(ids: list[int]) -> tuple[int, int]:
    return Counter(zip(ids, ids[1:])).most_common(1)[0][0]


def merge(ids: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    """Replace every occurrence of `pair` with the single token `new_id`."""
    out, i = [], 0
    while i < len(ids):
        if i + 1 < len(ids) and (ids[i], ids[i + 1]) == pair:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out


def train(text: str, num_merges: int):
    ids = list(text.encode("utf-8"))  # start: one token per byte (0..255)
    vocab = {i: bytes([i]) for i in range(256)}
    merges: dict[tuple[int, int], int] = {}
    for step in range(num_merges):
        pair = most_common_pair(ids)
        new_id = 256 + step
        ids = merge(ids, pair, new_id)
        merges[pair] = new_id
        vocab[new_id] = vocab[pair[0]] + vocab[pair[1]]
        print(f"merge {step + 1:>2}: {vocab[pair[0]]!r} + {vocab[pair[1]]!r} -> {vocab[new_id]!r}")
    return merges, vocab


def encode(text: str, merges) -> list[int]:
    ids = list(text.encode("utf-8"))
    for pair, new_id in merges.items():  # apply merges in the order they were learned
        ids = merge(ids, pair, new_id)
    return ids


def decode(ids: list[int], vocab) -> str:
    return b"".join(vocab[i] for i in ids).decode("utf-8", errors="replace")


if __name__ == "__main__":
    merges, vocab = train(CORPUS, num_merges=25)

    for sample in ["the cat sat", "tokens", "xylophone", "नमस्ते"]:
        ids = encode(sample, merges)
        pieces = [vocab[i].decode("utf-8", errors="replace") for i in ids]
        print(f"\n{sample!r}: {len(sample)} chars -> {len(ids)} tokens\n  {pieces}")
        assert decode(ids, vocab) == sample

    # Try it:
    # 1. Raise num_merges to 100. What happens to the token count of "the cat sat"?
    # 2. Why does "xylophone" cost more tokens than "tokens"? What does that tell
    #    you about the cost of rare words, code, and non-English text?
    # 3. Real tokenizers have ~100k-200k tokens. Roughly: 1 token ~ 4 characters
    #    of English ~ 0.75 words. Estimate the tokens in a 10-page document.
