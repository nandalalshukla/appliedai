"""Lab 4.1 - RAG in 40 lines: retrieve, then generate, with citations.

RAG = Retrieval-Augmented Generation. Instead of hoping the model knows your
company's refund policy (it does not), you look the policy up and paste it
into the prompt. The model's job becomes reading, not remembering.

Run:  python modules/04-rag/labs/01_naive_rag.py
"""

from aikit import MODEL, get_client, text_of
from aikit.rag import VectorIndex, format_context, load_corpus

# INDEXING (done once, offline): load -> chunk -> embed -> store
chunks = load_corpus("data/handbook")
index = VectorIndex(chunks)
print(f"indexed {len(chunks)} chunks\n")

SYSTEM = """You answer customer-support questions using only the documents provided.

- Every factual sentence must end with the index of the document it came from, like [2].
- If the documents do not contain the answer, reply exactly: "I could not find this in the handbook."
- Do not use knowledge from outside the documents."""


def answer(client, question: str, k: int = 3) -> str:
    # QUERY TIME: retrieve -> build prompt -> generate
    hits = [chunk for chunk, _ in index.search(question, k)]
    print("retrieved:", [c.id for c in hits])
    prompt = f"{format_context(hits)}\n\nQuestion: {question}"  # documents first, question last
    response = client.messages.create(
        model=MODEL, max_tokens=4000, system=SYSTEM, messages=[{"role": "user", "content": prompt}]
    )
    return text_of(response)


if __name__ == "__main__":
    client = get_client(
        script=[
            "Monthly plans can be refunded in full within 14 days of a charge, and annual plans "
            "within 30 days of purchase [1]. Refunds take 5 to 10 business days to appear [1].",
            "I could not find this in the handbook.",
        ]
    )
    for q in ["How long do I have to ask for a refund?", "Do you offer a student discount?"]:
        print(f"Q: {q}\nA: {answer(client, q)}\n")

# Try it:
# 1. Print the full prompt for one question. This is the first thing to look at
#    when a RAG answer is wrong: was the right chunk even retrieved?
# 2. Set k=1, then k=10. What changes in cost? In answer quality?
# 3. Ask "can I get my money back on a yearly plan?". Look at what was retrieved.
#    The handbook says "refund" and "annual"; the user said "money back" and
#    "yearly". Labs 4.2 and 4.4 fix this.
