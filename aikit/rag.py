"""aikit.rag - retrieval building blocks, each small enough to read in one sitting.

    load_corpus(dir)        markdown files -> list[Chunk] (with metadata)
    chunk_markdown(...)     split by heading, then by size, with overlap
    BM25                    keyword search (exact words, weighted by rarity)
    VectorIndex             embedding search (similar meaning)
    rrf(...)                merge several rankings into one
    HybridRetriever         BM25 + vectors + metadata filter, merged with RRF
    format_context(...)     chunks -> the <document> blocks you put in a prompt
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .embed import get_embedder, tokenize


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    meta: dict = field(default_factory=dict)


Filter = dict  # e.g. {"product": "billing", "updated": "2026"}


def _matches(chunk: Chunk, where: Filter | None) -> bool:
    return not where or all(str(chunk.meta.get(k)) == str(v) for k, v in where.items())


# -- loading and chunking ----------------------------------------------------

def _split_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, header, body = raw.split("---", 2)
    meta = dict(line.split(":", 1) for line in header.strip().splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in meta.items()}, body


def chunk_markdown(text: str, source: str, meta: dict | None = None,
                   max_words: int = 120, overlap: int = 20) -> list[Chunk]:
    """Split on headings first (a section is a natural unit of meaning), then
    cut long sections into overlapping windows. Each chunk is prefixed with its
    title path so it still makes sense when read alone."""
    title, section, sections = "", "", []
    lines: list[str] = []

    def flush():
        body = " ".join(lines).strip()
        if body:
            sections.append((" > ".join(x for x in (title, section) if x), body))
        lines.clear()

    for line in text.splitlines():
        if line.startswith("# "):
            flush()
            title, section = line[2:].strip(), ""
        elif line.startswith("## "):
            flush()
            section = line[3:].strip()
        else:
            lines.append(line.strip())
    flush()

    chunks: list[Chunk] = []
    for heading, body in sections:
        words = body.split()
        step = max(1, max_words - overlap)
        for start in range(0, len(words), step):
            piece = " ".join(words[start : start + max_words])
            chunks.append(Chunk(f"{source}#{len(chunks)}", f"{heading}\n{piece}", source, dict(meta or {})))
            if start + max_words >= len(words):
                break
    return chunks


def load_corpus(directory: str | Path, **chunk_kwargs) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(Path(directory).glob("*.md")):
        meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
        chunks += chunk_markdown(body, path.name, meta, **chunk_kwargs)
    return chunks


# -- keyword search ----------------------------------------------------------

class BM25:
    """The classic keyword ranking function. A document scores higher when it
    contains the query's words often (tf), when those words are rare across the
    corpus (idf), and it is not penalised for simply being long (b)."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [tokenize(c.text) for c in chunks]
        self.tf = [Counter(d) for d in self.docs]
        self.avg_len = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(term for d in self.docs for term in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 5, where: Filter | None = None) -> list[tuple[Chunk, float]]:
        scored = []
        for i, chunk in enumerate(self.chunks):
            if not _matches(chunk, where):
                continue
            score, length = 0.0, len(self.docs[i])
            for term in tokenize(query):
                f = self.tf[i].get(term, 0)
                if f:
                    norm = f + self.k1 * (1 - self.b + self.b * length / self.avg_len)
                    score += self.idf[term] * f * (self.k1 + 1) / norm
            if score > 0:
                scored.append((chunk, score))
        return sorted(scored, key=lambda x: -x[1])[:k]


# -- vector search -----------------------------------------------------------

class VectorIndex:
    """Brute-force nearest neighbours: one matrix multiply. Exact, and fast
    enough up to ~100k chunks. Beyond that you use an approximate index (HNSW)
    inside a vector database; the interface stays the same."""

    def __init__(self, chunks: list[Chunk], embedder=None):
        self.chunks = chunks
        self.embedder = embedder or get_embedder()
        self.matrix = self.embedder.embed([c.text for c in chunks])

    def search(self, query: str, k: int = 5, where: Filter | None = None) -> list[tuple[Chunk, float]]:
        scores = self.matrix @ self.embedder.embed([query])[0]
        order = np.argsort(-scores)
        hits = [(self.chunks[i], float(scores[i])) for i in order if _matches(self.chunks[i], where)]
        return hits[:k]


# -- fusion ------------------------------------------------------------------

def rrf(rankings: list[list[Chunk]], k: int = 60) -> list[tuple[Chunk, float]]:
    """Reciprocal Rank Fusion. BM25 scores and cosine scores are on different
    scales, so we ignore the scores and combine RANKS: each list gives a chunk
    1 / (k + rank). Chunks that rank well in several lists rise to the top."""
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            by_id[chunk.id] = chunk
    return sorted(((by_id[i], s) for i, s in scores.items()), key=lambda x: -x[1])


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], embedder=None):
        self.bm25 = BM25(chunks)
        self.vectors = VectorIndex(chunks, embedder)

    def search(self, query: str, k: int = 5, where: Filter | None = None, pool: int = 20) -> list[tuple[Chunk, float]]:
        keyword = [c for c, _ in self.bm25.search(query, pool, where)]
        semantic = [c for c, _ in self.vectors.search(query, pool, where)]
        return rrf([keyword, semantic])[:k]


def format_context(chunks: list[Chunk]) -> str:
    """Numbered, tagged documents. The index is what the model cites."""
    return "\n".join(
        f'<document index="{i}" source="{c.source}">\n{c.text}\n</document>'
        for i, c in enumerate(chunks, start=1)
    )
