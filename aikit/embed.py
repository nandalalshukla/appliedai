"""aikit.embed - turn text into vectors.

Two embedders with the same interface (`.embed(list[str]) -> np.ndarray`):

HashEmbedder   - zero dependencies, deterministic, instant. It hashes words and
                 character n-grams into a fixed-size vector. It captures word
                 overlap and spelling similarity, NOT meaning: "car" and
                 "automobile" look unrelated to it. It exists so every lab runs
                 anywhere. Do not ship it.
STEmbedder     - a real semantic model (sentence-transformers). Used
                 automatically if the package is installed and
                 AIKIT_EMBEDDER=st is set.

In production you would call an embedding API (Voyage AI, OpenAI, Gemini,
Cohere) or host an open model. The code around the embedder does not change.
"""

from __future__ import annotations

import hashlib
import os
import re

import numpy as np

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens. Shared by the embedder and the BM25 lab."""
    return _WORD.findall(text.lower())


def _bucket(token: str, dim: int) -> tuple[int, float]:
    h = int.from_bytes(hashlib.md5(token.encode()).digest()[:8], "little")
    return h % dim, 1.0 if (h >> 63) & 1 else -1.0


class HashEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in tokenize(text):
                idx, sign = _bucket("w:" + word, self.dim)
                out[row, idx] += sign
                padded = f"#{word}#"
                for i in range(len(padded) - 2):  # character trigrams
                    idx, sign = _bucket("c:" + padded[i : i + 3], self.dim)
                    out[row, idx] += 0.3 * sign
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-9)  # unit length -> dot product == cosine


class STEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def get_embedder():
    if os.getenv("AIKIT_EMBEDDER", "").lower() == "st":
        return STEmbedder()
    return HashEmbedder()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
