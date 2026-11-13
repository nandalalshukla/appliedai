"""Lab 2.6 - "System One" models: a fast typed-decision step before the LLM.

Not every step needs a model that writes text. Many steps are DECISIONS
("is this spam?", "which queue?") or EXTRACTIONS ("what is the order ID?").
A new class of non-generative models targets exactly these steps: they return
typed answers with a confidence score in one pass, with no generated tokens.
Examples announced in late 2026 are TypeSafe AI's Jev (decisions) and
Cloudflare's Clairic (extraction of typed values). See the lesson for sources
and caveats.

This lab teaches the ARCHITECTURE those models enable, using a stand-in
classifier so it runs anywhere:

    input -> fast decision (cheap, typed, with confidence)
                 | confident?  yes -> act on it in code
                 | no          -> escalate to the LLM (slow, expensive, flexible)

Swap `fast_decide` for a real System One model, a small fine-tuned classifier,
or a cheap LLM. The routing logic around it stays the same.

Run:  python modules/02-prompting/labs/06_system_one_gate.py
"""

from dataclasses import dataclass

from aikit import MODEL, get_client, text_of

KEYWORDS = {
    "billing": {"charge", "charged", "refund", "invoice", "payment", "price"},
    "bug": {"crash", "crashes", "error", "broken", "blank", "freeze"},
    "account": {"login", "log", "password", "email", "locked"},
}


@dataclass
class Decision:
    label: str
    confidence: float  # 0..1
    source: str  # "fast" or "llm"


def fast_decide(message: str) -> Decision:
    """Stand-in for a System One model: typed label + confidence, no text generation."""
    words = set(message.lower().replace(".", " ").replace(",", " ").split())
    hits = {label: len(words & kws) for label, kws in KEYWORDS.items()}
    total = sum(hits.values())
    if total == 0:
        return Decision("other", 0.0, "fast")
    label = max(hits, key=hits.get)
    return Decision(label, hits[label] / total, "fast")  # 1.0 only if a single label matched


def llm_decide(client, message: str) -> Decision:
    r = client.messages.create(
        model=MODEL, max_tokens=4000,
        system="Route the message to one queue: billing, bug, account, other. "
               "Route by root problem. Reply with the queue name only.",
        messages=[{"role": "user", "content": f"<message>{message}</message>"}],
    )
    return Decision(text_of(r).strip().lower(), 1.0, "llm")


def route(client, message: str, threshold: float = 0.9) -> Decision:
    d = fast_decide(message)
    return d if d.confidence >= threshold else llm_decide(client, message)


if __name__ == "__main__":
    client = get_client(script=["bug", "other"])
    messages = [
        "I was charged twice, please refund me.",          # clear -> fast path
        "I forgot my password and I am locked out.",       # clear -> fast path
        "The refund page shows a blank error.",            # mixed signals -> LLM
        "Do you ship to Nepal?",                           # no signal -> LLM
    ]
    llm_calls = 0
    for m in messages:
        d = route(client, m)
        llm_calls += d.source == "llm"
        print(f"{d.source:>4} conf={d.confidence:.2f} -> {d.label:<8} | {m}")
    print(f"\nLLM used for {llm_calls}/{len(messages)} messages.")

# What decides whether this is worth it:
# - the share of traffic the fast path can answer confidently
# - whether its confidence is CALIBRATED (0.9 should be right ~90% of the time);
#   you check that on a labelled set, which is an eval (Module 7)
#
# Try it:
# 1. Lower the threshold to 0.5. Which message is now routed wrongly?
# 2. Log every (fast decision, LLM decision) pair. Where they disagree is your
#    best source of new training/eval examples.
