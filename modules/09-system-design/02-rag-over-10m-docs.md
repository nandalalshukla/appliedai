# Design 2: RAG over 10 million documents

## Problem

A company has 10 million internal documents (wikis, tickets, PDFs, chat exports). Build a question-answering system over them for 50,000 employees.

*Stop here and design it yourself first.*

## Clarify

| Question | Assumption |
|---|---|
| Document size and type? | Average 2,000 tokens; mixed formats including scanned PDFs |
| Permissions? | Yes. Documents have access-control lists (ACLs). **This shapes everything** |
| Freshness? | New and edited documents searchable within minutes |
| Load? | About 500,000 questions per day, peak 50 per second |
| Latency? | First token within 2 seconds |
| Deletes? | A deleted document must stop appearing promptly (legal requirement) |

## Back-of-envelope numbers

- 10M docs × 2,000 tokens ÷ ~400 tokens per chunk ≈ **50 million chunks**.
- Vectors: 50M × 1,024 dimensions × 4 bytes ≈ **200 GB** raw. Too large for one machine's memory without compression. Quantization (storing each dimension in 1 byte or 1 bit) cuts this 4x to 32x.
- Embedding the corpus once: 20 billion tokens. A real line item; do it with batch pricing, and never re-embed everything casually. **Changing the embedding model means re-embedding 50M chunks**, so choose carefully and version the index.

## Architecture

```
OFFLINE / STREAMING INGESTION
 sources ─► connectors ─► queue ─► parse (OCR, tables) ─► chunk ─► embed (batched) ─► index
              │ change events                                  │ dedupe by content hash
              ▼                                                ▼
        ACL + metadata store ────────────────────────► search engine (sharded):
                                                         inverted index (BM25) + ANN vector index
                                                         + metadata & ACL fields per chunk
ONLINE
 question ─► auth ─► semantic cache? ─► rewrite ─► hybrid retrieve (ACL-filtered, top 100)
          ─► re-rank (top 8) ─► generate with citations (streamed) ─► output checks ─► user
                                                                        └─► trace + feedback
```

## Key decisions

**Ingestion is a pipeline, not a script.** Connectors emit change events (create, update, delete). A queue feeds idempotent workers. A content hash per chunk means an edited document re-embeds only its changed chunks. Deletes propagate as tombstones. Track every document's indexing state so you can answer "why is this not searchable?".

**Parsing quality.** At this scale a meaningful share of documents are scans, slides or tables. Budget for OCR and layout-aware parsing, and sample parsed output regularly. Bad text is invisible in metrics and fatal to answers.

**Chunking.** Structure-aware, with title-path prefixes (Module 4). Store parent document IDs so you can expand a hit to its surrounding section when the model needs more context.

**Hybrid retrieval in one engine.** Internal corpora are full of IDs, project names and error codes: BM25 is essential, not optional. Use an engine that does keyword and vector search together and fuses them (RRF).

**ANN index.** HNSW gives high recall with low latency but lives in memory; with quantization the 50M vectors fit across a few shards. Shard by tenant or by hash; replicate for availability. Measure ANN recall against exact search on a sample.

**Permissions are enforced inside retrieval.** Store allowed groups on each chunk and filter in the query using the user's group memberships. Never retrieve first and filter afterwards in the application (you would lose your top-k and risk leaking through the model). Never rely on the prompt to withhold content. ACL changes must propagate quickly; test revocation explicitly.

**Two-stage ranking.** Retrieve ~100 candidates cheaply, re-rank to ~8 with a cross-encoder. The re-ranker is where latency goes, so batch it and cap candidate length.

**Query handling.** Standalone rewrite for follow-ups; route obvious non-questions away; apply metadata filters extracted from the question ("in the 2026 handbook") where confident.

**Generation.** Numbered sources, required citations, an explicit not-found path, streaming. Prefer newer documents when sources conflict, and say so.

**Caching, three layers.** Embedding cache for repeated queries; semantic answer cache **keyed by permission set** as well as question; prompt caching for the stable instruction prefix.

## Failure modes

| Failure | Mitigation |
|---|---|
| Permission leak | Filter in the engine; per-request ACL; audit tests with synthetic restricted docs |
| Stale or duplicate documents dominate | Freshness and authority signals in ranking; near-duplicate collapse |
| Answer cached for one user served to another without access | Cache key includes the permission scope |
| Embedding model upgrade | Versioned indexes; build the new one alongside; switch after evals |
| Ingestion backlog | Queue depth alerts; priority lanes for recent edits |
| Poisoned document with injected instructions | Treat retrieved text as data; no powerful tools in the answering path |
| Hot shard or slow re-ranker | Timeouts; degrade to un-re-ranked results with a notice |

## Evaluation

- Retrieval set: 300+ real questions with labelled relevant chunks; recall@100 for stage 1, recall@8 and MRR after re-ranking, sliced by source type.
- Answers: faithfulness and citation validity (judge plus code), correct refusal on unanswerable questions.
- Permissions: an automated suite that asserts restricted content never appears for unauthorized users. Zero tolerance.
- Online: thumbs, citation click-through, reformulation rate (a user re-asking is a failure signal).

## Cost and latency budget (illustrative)

| Stage | Latency |
|---|---|
| Rewrite (small model) | 300 ms |
| Hybrid retrieval | 100 ms |
| Re-rank 100 candidates | 200 ms |
| First token from generator | 700 ms |
| **Total to first token** | **≈1.3 s** |

Per question: roughly 4,000 input tokens (mostly retrieved chunks) and 300 output tokens. Multiply by 500,000 per day and model choice dominates the bill, so route simple lookups to a small model.

## Build the core

Scale `aikit.rag` to a few thousand documents (any public dataset): add a content-hash incremental indexer, an `allowed_groups` metadata filter, the re-ranker from Lab 4.3, and a permission test suite.
