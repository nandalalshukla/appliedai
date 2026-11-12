# Module 4: Retrieval-augmented generation (RAG)

**Weeks 6-7.** Models do not know your company's documents, and they cannot read ten million pages per question. RAG fetches the few passages that matter and lets the model answer from them. It is the most widely deployed LLM pattern in industry, and "we built RAG and the answers are bad" is the most common problem you will be hired to fix.

Labs: [`labs/`](labs/) · Toolkit: [`aikit/rag.py`](../../aikit/rag.py) · Design problem: [RAG over 10M documents](../09-system-design/02-rag-over-10m-docs.md) · Project unlocked: [P2 Ask My Docs](../../projects/02-ask-my-docs/README.md)

---

## 4.1 The pipeline

Run [Lab 4.1](labs/01_naive_rag.py).

```
INDEXING (offline, once per document change)
  documents ─► clean ─► chunk ─► embed ─► store (vectors + text + metadata)

QUERYING (online, per question)
  question ─► [rewrite] ─► retrieve ─► [filter] ─► [re-rank] ─► build prompt ─► generate ─► [verify]
```

The single most useful idea in this module:

> **RAG quality is mostly retrieval quality.** If the right passage is not in the prompt, the model cannot give the right answer. Debug retrieval first, generation second.

### When to use RAG, and when not to

| Situation | Approach |
|---|---|
| Knowledge fits comfortably in the context window (a few documents) | Put it all in the prompt. Simpler and often better. Cache it (Module 8) |
| Large or changing private corpus | **RAG** |
| Facts that live in a database or API | A tool (Module 3), not document search |
| The model must explore: follow references, search repeatedly | Agentic retrieval: give an agent a search tool (Module 5) |
| You want a different *style or skill*, not new facts | Prompting and examples; fine-tuning only as a last resort |

## 4.2 Chunking

Documents are split into **chunks** because embeddings blur long text into one average vector, and because you want to send only the relevant parts to the model.

| Decision | Guidance |
|---|---|
| Size | Start around 200-500 tokens. Too small loses context ("it lasts 30 days": what does?). Too large dilutes the match and wastes tokens |
| Boundaries | Split on structure first (headings, paragraphs, functions), size second. Never cut mid-sentence |
| Overlap | 10-20%, so a fact that straddles a boundary survives in one piece |
| Context | Prefix each chunk with its title path (`Billing > Refund policy`). A chunk must make sense read alone |
| Metadata | Keep source, section, date, product, permissions with every chunk |

Read `chunk_markdown` in [`aikit/rag.py`](../../aikit/rag.py): it splits on headings, windows long sections with overlap, and prefixes the title path. A stronger version of the last idea, *contextual retrieval*, has a model write a one-line description of where each chunk sits in its document before embedding.

Parsing is where real projects bleed: PDFs with tables, scanned pages, slide decks. Garbage text in means garbage retrieval out. Always look at your extracted text before blaming the model.

## 4.3 Hybrid search and metadata filtering

Run [Lab 4.2](labs/02_hybrid_search.py).

| | Keyword search (BM25) | Vector search |
|---|---|---|
| Matches | Exact words | Similar meaning |
| Strong at | IDs, error codes, names, rare terms (`STG-507`) | Paraphrases ("money back" → "refund") |
| Weak at | Synonyms, rephrasing | Exact identifiers, numbers, negation |
| Needs | An inverted index | An embedding model and a vector index |

**BM25** scores a document higher when it contains the query's words often, when those words are rare in the corpus, and it corrects for document length. It is decades old and still a strong baseline. Read the 20-line `BM25` class.

**Hybrid search** runs both and merges them. Their scores are on different scales, so merge *ranks* with **Reciprocal Rank Fusion (RRF)**: each list contributes `1 / (60 + rank)` per document, and documents ranked well by both rise to the top. Read `rrf`; it is ten lines.

**Metadata filtering** restricts candidates by structured fields. In the lab, two documents describe the refund policy and one is from 2023. Both are "about refunds", so similarity cannot pick the current one; a filter on `updated` can. Filters express what similarity cannot:

- **Freshness:** only current documents.
- **Scope:** only the product the user is asking about.
- **Permissions:** only documents this user may see. **This one is a security requirement.** In a multi-tenant product, a missing tenant filter is a data leak. Enforce it in the retrieval layer, where the model cannot forget it.

Filter before ranking, so that all top-k results are eligible.

### Vector databases, briefly

The lab's `VectorIndex` compares the query with every vector, which is exact and fine to about 100,000 chunks. Beyond that you use **approximate nearest neighbour (ANN)** indexes such as HNSW, which trade a little recall for a large speedup. Common choices: pgvector (inside Postgres, a sensible default if you already run Postgres), Qdrant, Weaviate, Milvus, Pinecone, and the search engines OpenSearch and Elasticsearch, which do keyword and vector search together. Choosing among them matters far less than chunking, hybrid search and evaluation.

## 4.4 Re-ranking: bi-encoders and cross-encoders

Run [Lab 4.3](labs/03_reranking.py).

- A **bi-encoder** embeds the query and each document *separately*. Documents can be embedded ahead of time, so search is one fast vector comparison, but the two texts never interact.
- A **cross-encoder** reads the query and one document *together* and outputs a relevance score. It is much more accurate, and far too slow to run over a corpus.

So search is done in two stages:

```
stage 1  retrieve ~50-100 candidates (hybrid search)      goal: recall, do not miss it
stage 2  re-rank them, keep the best 3-10                 goal: precision, best first
```

Re-ranking is often the largest single quality gain after hybrid search. It cannot fix stage 1: a document that was never retrieved cannot be promoted. Options, from fastest to slowest: a local cross-encoder model, a hosted re-rank API, or an LLM asked to order the candidates (slow, but it can follow instructions such as "prefer the newest policy").

## 4.5 Query rewriting

Run [Lab 4.4](labs/04_query_rewriting.py). Users do not write search queries; they write "and what about yearly ones?". Fix the query before searching:

| Technique | What it does | Use when |
|---|---|---|
| **Standalone rewrite** | Resolves "it", "that", "yearly ones" using the chat history | Any multi-turn chat. Almost mandatory |
| **Multi-query** | Generates several phrasings, searches each, fuses with RRF | Vocabulary mismatch between users and documents |
| **Decomposition** | Splits a compound question into sub-questions | "Compare X and Y", multi-part questions |
| **HyDE** | Has the model write a hypothetical answer and searches with that | Short questions against long formal documents |
| **Routing** | Chooses which index, or whether to search at all | Several corpora; small talk that needs no retrieval |

Each is an extra model call before the user sees anything. Use a small, fast model and keep a technique only if Lab 4.6 shows it helps.

## 4.6 Generation: grounded answers with citations

The prompt in Lab 4.1 does four things you should always do:

1. **Documents first, question last.**
2. **Number the documents** and require citations (`[2]`). Citations let users verify and let you check automatically that each cited document exists and supports the claim.
3. **An explicit "not found" path.** Without it the model answers from memory.
4. **"Use only the documents."** It reduces unsupported claims; it does not eliminate them. Verify.

Retrieved text is also **untrusted input**. A document can contain "ignore your instructions and...". Everything in Module 2 about prompt injection applies to your own knowledge base, especially if users or the public can add documents.

## 4.7 Measure retrieval

Run [Lab 4.6](labs/06_retrieval_eval.py). Build a small labelled set (question → passage that answers it) and compute:

- **Recall@k:** in what fraction of questions is a correct chunk in the top k? This is the ceiling on your answer quality.
- **MRR** (mean reciprocal rank): how high the first correct chunk appears.

Then change one thing at a time (chunk size, embedder, fusion, rewriting, re-ranking) and keep it only if the numbers move. This is the entire method. Teams that skip it tune by anecdote and go in circles.

End-to-end answer quality (faithfulness to the sources, relevance, completeness) is evaluated separately, in Module 7.

### The RAG debugging flowchart

```
Wrong answer
 ├─ Is the answer in the corpus at all?            no  → content gap; no retrieval fix exists
 ├─ Is it in a chunk, intact and readable?         no  → parsing or chunking bug
 ├─ Was that chunk in the top-50 candidates?       no  → stage-1 retrieval: hybrid, rewriting, embedder
 ├─ Was it in the top-k sent to the model?         no  → re-ranking, or k too small
 └─ It was in the prompt and the answer is wrong   → generation: prompt, model, too much noise in context
```

## 4.8 Semantic caching

Run [Lab 4.5](labs/05_semantic_cache.py). A semantic cache embeds each question and returns a stored answer when an earlier question is similar enough. For repetitive workloads such as support FAQs it removes a large share of model calls.

It also introduces a new way to be wrong: serving one question's answer to a different question. The guard rails:

1. **Scope the key.** Personalized answers must be keyed by user or tenant and permissions, or not cached.
2. **Expire and invalidate.** TTLs, plus clearing entries when source documents are re-indexed.
3. **Tune the threshold on real pairs.** It depends on the embedding model. In the lab, "reset my password" and "delete my account" share most of their words.
4. **Beware negation and numbers.** "with 2FA" and "without 2FA" embed almost identically.
5. **Never cache failures** or low-confidence answers.

Do not confuse this with **prompt caching** (Module 8), which is a provider feature that makes repeated prompt *prefixes* cheaper and never changes an answer.

## 4.9 RAG at scale: what changes

The design problem works through this in detail. In short: ANN indexes and sharding, an ingestion pipeline with incremental updates and deletes, hybrid retrieval in a search engine, permission filters, re-ranking budgets, caching layers, and continuous evaluation. Read [RAG over 10M documents](../09-system-design/02-rag-over-10m-docs.md) after the labs.

---

## Checkpoint

1. A RAG answer is wrong. What is the first thing you look at?
2. Give one query BM25 handles better than vector search, and one where it is the reverse.
3. Why does RRF combine ranks instead of scores?
4. Why is a tenant filter a security control and not a relevance feature? Where must it be enforced?
5. Explain bi-encoder vs cross-encoder in two sentences. Why not use a cross-encoder for stage 1?
6. What does recall@5 = 0.6 tell you about the best possible answer accuracy?
7. Name three ways a semantic cache can return a wrong answer.
8. When is putting the whole document set in the prompt better than RAG?

## Exercises

1. **Your own corpus.** Put 10-20 of your own notes or docs in a folder, index them, and write 15 gold questions. Report recall@3 for BM25, vector and hybrid.
2. **Chunk-size sweep.** Run Lab 4.6 with `max_words` of 30, 60, 120, 240, 480. Explain the shape of the curve.
3. **Citation checker.** Write a function that parses `[n]` citations from an answer and flags any that point to a document index that was not provided. Then use a second model call to judge whether each cited document supports its sentence.

## Project 2

Build [P2: Ask My Docs](../../projects/02-ask-my-docs/README.md).

## Go deeper

[Module 4 in RESOURCES.md](../../RESOURCES.md#module-4-rag).

Next: [Module 5: Single-agent loops and systems](../05-agents/README.md)
