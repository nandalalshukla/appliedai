"""Lab 8.1 - Prompt caching: stop paying full price for the same prefix.

Most requests start with the same thousands of tokens: system prompt, tool
definitions, a long document, the earlier conversation. Prompt caching lets
the provider reuse the processed prefix: cached input tokens cost about 10%
of the normal price and are faster.

The rule that explains every caching bug:  CACHING IS A PREFIX MATCH.
The request is rendered in the order  tools -> system -> messages.  If any
byte changes, everything after that point is uncached.

Run:  python modules/08-production/labs/01_prompt_caching.py
"""

import hashlib
import time
from datetime import datetime

from aikit import MODEL, CostMeter, fake_text, get_client

HANDBOOK = open("data/handbook/billing.md").read() * 12  # pretend this is a long document

GOOD_SYSTEM = [
    {
        "type": "text",
        "text": "You answer questions about the Acme Cloud handbook.\n\n<handbook>\n" + HANDBOOK + "\n</handbook>",
        "cache_control": {"type": "ephemeral"},  # cache everything up to and including this block
    }
]


def bad_system():
    """Same content, with one 'harmless' dynamic line at the TOP."""
    return [
        {
            "type": "text",
            "text": f"Current time: {datetime.now().isoformat()}\n\n"  # <- changes every request
                    "You answer questions about the Acme Cloud handbook.\n\n<handbook>\n" + HANDBOOK + "\n</handbook>",
            "cache_control": {"type": "ephemeral"},
        }
    ]


# ---- offline simulation of the provider's cache accounting ------------------
_seen: set[str] = set()


def responder(kwargs):
    prefix = kwargs["system"][0]["text"]
    key = hashlib.sha256(prefix.encode()).hexdigest()
    tokens = len(prefix) // 4
    question_tokens = len(str(kwargs["messages"])) // 4
    if key in _seen:
        return fake_text("(answer)", inp=question_tokens, out=40, cache_read=tokens)
    _seen.add(key)
    return fake_text("(answer)", inp=question_tokens, out=40, cache_write=tokens)


client = get_client(responder=responder)
QUESTIONS = ["What is the refund window?", "How long do refunds take?", "What is error PAY-409?",
             "When are invoices generated?"]


def run(label: str, system_factory) -> CostMeter:
    meter = CostMeter()
    print(f"\n{label}")
    for q in QUESTIONS:
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=system_factory(),
            messages=[{"role": "user", "content": q}],  # the part that varies goes LAST
        )
        meter.add(response)
        u = response.usage
        print(f"  cache_write={u.cache_creation_input_tokens:>6}  cache_read={u.cache_read_input_tokens:>6}"
              f"  uncached_in={u.input_tokens:>4}   {q}")
        time.sleep(0.001)
    print(f"  total ~${meter.usd:.4f}")
    return meter


good = run("STABLE PREFIX (cache hits after the first request)", lambda: GOOD_SYSTEM)
bad = run("TIMESTAMP IN THE PREFIX (every request is a cache miss)", bad_system)
print(f"\nThe timestamp made this workload {bad.usd / good.usd:.1f}x more expensive.")

# How to read `usage` (always log these three):
#   cache_creation_input_tokens  written to the cache this request (costs ~1.25x)
#   cache_read_input_tokens      served from the cache              (costs ~0.1x)
#   input_tokens                 not cached                         (costs 1x)
# If cache_read stays at 0 across repeated requests, something in your prefix
# is changing. The usual suspects:
#   - a timestamp, request id or user name near the top of the system prompt
#   - tools in a different order each time (aikit sorts them for this reason)
#   - json.dumps without sort_keys
#   - editing or re-summarising early messages in the history
#   - a prefix shorter than the model's minimum cacheable size
#
# Design rule: order content from MOST stable to LEAST stable:
#   tool definitions -> system prompt -> long documents -> conversation -> this turn
# Put per-request facts (time, user, question) at the END, in the user message.
#
# Caches expire (about 5 minutes by default, refreshed on each hit; a 1-hour
# option exists at a higher write price). Caching pays off when the same
# prefix is reused within that window.
#
# Try it:
# 1. Move the timestamp into the user message. Confirm cache hits return.
# 2. Live mode: print response.usage for 3 identical-prefix requests.
# 3. For a multi-turn chat, where should the cache breakpoint go so each turn
#    reuses the previous turns? (Hint: the end of the conversation so far.)
