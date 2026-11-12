"""Lab 2.2 - Few-shot examples and letting the model reason.

Task: route support messages to a queue. Rules are fuzzy, so we SHOW the model
the boundary cases instead of trying to describe every one.

Run:  python modules/02-prompting/labs/02_few_shot_cot.py
"""

from aikit import MODEL, get_client, text_of

QUEUES = ["billing", "bug", "account", "other"]

# Good examples are: correct, varied, and aimed at the hard boundaries.
# Three easy examples teach nothing. Note example 2 and 3 are deliberately tricky.
EXAMPLES = [
    ("I was charged twice this month.", "billing"),
    ("The app crashes when I open my invoice.", "bug"),          # mentions invoice, but it's a crash
    ("I can't log in to update my card.", "account"),            # mentions card, but it's login
    ("Do you have a student discount?", "billing"),
    ("Great product, thanks!", "other"),
]


def build_system() -> str:
    shots = "\n".join(
        f"<example>\n<message>{m}</message>\n<queue>{q}</queue>\n</example>" for m, q in EXAMPLES
    )
    return f"""You route customer messages to exactly one support queue.

Queues: {", ".join(QUEUES)}
Route by the ROOT problem the customer needs solved, not by keywords they mention.

<examples>
{shots}
</examples>

Before answering, reason briefly inside <reasoning> tags about what the root problem is.
Then give the queue inside <queue> tags. The queue must be one of the listed names."""


def parse_queue(text: str) -> str:
    """Pull the answer out of the tags. Reasoning is ignored by code but improves the answer."""
    start, end = text.find("<queue>"), text.find("</queue>")
    queue = text[start + 7 : end].strip() if start != -1 and end != -1 else ""
    return queue if queue in QUEUES else "other"  # never trust; always validate


client = get_client(
    script=[
        "<reasoning>The customer mentions a refund but cannot see the page because of an error "
        "screen. The root problem is a broken page.</reasoning>\n<queue>bug</queue>"
    ]
)

message = "The refund page shows a blank error screen every time."
response = client.messages.create(
    model=MODEL,
    max_tokens=2000,
    system=build_system(),
    messages=[{"role": "user", "content": f"<message>{message}</message>"}],
)
raw = text_of(response)
print(raw, "\n\nrouted to:", parse_queue(raw))

# Why reasoning-then-answer works: the model writes left to right. If the answer
# comes first, the "reasoning" after it is a justification, not a cause. Asking
# for reasoning first lets the answer depend on it. (This is chain-of-thought.)
#
# Reasoning models already think before answering, so explicit step-by-step
# instructions matter less than they used to. Visible reasoning is still
# valuable: you can log it and read it when the answer is wrong.
#
# Try it:
# 1. Remove the two tricky examples. Find a message that now gets misrouted.
# 2. Put <queue> before <reasoning> in the instructions. Compare on 10 hard messages.
# 3. Make every example "billing". What happens? (Models copy example patterns
#    closely, including accidental ones: length, tone, label balance.)
