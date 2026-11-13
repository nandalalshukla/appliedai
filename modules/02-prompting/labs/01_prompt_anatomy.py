"""Lab 2.1 - Anatomy of a reliable prompt.

The same task, prompted two ways. The second is longer and far more reliable.

Run:  python modules/02-prompting/labs/01_prompt_anatomy.py
"""

from aikit import MODEL, get_client, text_of

REVIEW = "Battery died after 2 days. Support was friendly but could not fix it. Returning it."

VAGUE = f"Summarize this review: {REVIEW}"

# A reliable prompt answers the questions a smart new colleague would ask:
# who is this for, what exactly do you want, what does good look like,
# what do I do in the awkward cases, and what shape should the answer take?
SYSTEM = """You write one-line summaries of product reviews for a support dashboard.
Support agents scan hundreds of these per hour to decide which customers to call first.

Rules:
- One sentence, at most 20 words.
- Lead with the customer's main problem, then what they intend to do.
- Use only facts stated in the review. If the review does not mention a problem, write "No issue reported."
- Plain text. No preamble such as "Here is the summary"."""

# Put the data in tags so instructions and data cannot be confused,
# and put the question AFTER the data.
USER = f"<review>\n{REVIEW}\n</review>\n\nWrite the one-line summary."

client = get_client(
    script=[
        "Here's a summary of the review: The customer experienced battery issues with the product "
        "and although support was friendly they were unable to resolve it, so the customer is "
        "returning the item.",
        "Battery failed after two days and support could not fix it; customer is returning the product.",
    ]
)

vague = client.messages.create(
    model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": VAGUE}]
)
good = client.messages.create(
    model=MODEL, max_tokens=4000, system=SYSTEM, messages=[{"role": "user", "content": USER}]
)

print("VAGUE PROMPT ->", text_of(vague))
print("\nSPECIFIC PROMPT ->", text_of(good))

# Try it (live mode):
# 1. Run the vague prompt 5 times. How many different lengths and formats do you get?
#    Your downstream code has to handle all of them.
# 2. Feed the specific prompt a review with no problem ("Love it!"). Does the rule fire?
# 3. Delete the sentence explaining who reads the summaries. Does quality change?
#    Context about purpose lets the model make good choices you did not list.
