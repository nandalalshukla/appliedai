"""Lab 5.4 - Human in the loop: the agent proposes, a person approves.

Some actions are cheap to undo (reading a file). Some are not (sending money,
deleting data, emailing a customer). For the second kind the agent should
PAUSE and ask. The gate lives in code, around the tool - not in the prompt,
where a clever input could talk the model out of it.

Run:  python modules/05-agents/labs/04_human_in_the_loop.py          (auto: approve small, deny large)
      python modules/05-agents/labs/04_human_in_the_loop.py --ask    (you decide at the keyboard)
"""

import sys

from aikit import fake_tool, get_client
from aikit.agent import Agent, print_events
from aikit.tools import Tool, ToolRegistry

registry = ToolRegistry()
LEDGER: list[dict] = []


@registry.tool()
def get_order(order_id: str) -> dict:
    """Look up an order. Returns amount_usd and status."""
    return {"order_id": order_id, "amount_usd": {"A-1": 20, "A-2": 900}[order_id], "status": "delivered"}


@registry.tool(needs_approval=True, read_only=False)
def issue_refund(order_id: str, amount_usd: float, reason: str) -> str:
    """Refund money to the customer for an order. This moves real money and cannot be undone."""
    LEDGER.append({"order_id": order_id, "amount_usd": amount_usd})
    return f"refunded ${amount_usd} for {order_id}"


def policy(tool: Tool, args: dict) -> bool:
    """Policy-based approval: auto-approve small refunds, block large ones."""
    ok = args["amount_usd"] <= 100
    print(f"      policy: refund ${args['amount_usd']} -> {'auto-approved' if ok else 'DENIED (over $100 limit)'}")
    return ok


def ask_human(tool: Tool, args: dict) -> bool:
    """Show the exact action and its arguments. Approve the specific call, not a vague intent."""
    print(f"\n      APPROVAL NEEDED: {tool.name}\n      arguments: {args}")
    return input("      approve? [y/N] ").strip().lower() == "y"


SYSTEM = """You handle refund requests. Look up the order, then issue the refund for its full amount.
If a refund is declined, do not retry it. Tell the user it needs manager review."""

client = get_client(script=[
    fake_tool("get_order", {"order_id": "A-1"}),
    fake_tool("issue_refund", {"order_id": "A-1", "amount_usd": 20, "reason": "damaged"}),
    "Refunded $20 for order A-1.",
    fake_tool("get_order", {"order_id": "A-2"}),
    fake_tool("issue_refund", {"order_id": "A-2", "amount_usd": 900, "reason": "damaged"}),
    "The $900 refund for A-2 was declined and needs manager review.",
])

approve = ask_human if "--ask" in sys.argv else policy
for order in ["A-1", "A-2"]:
    print(f"\n=== refund request for {order}")
    result = Agent(client, registry, SYSTEM, approve=approve, on_event=print_events).run(
        f"Customer wants a refund for order {order}: item arrived damaged."
    )
    print("agent:", result.text)

print("\nledger:", LEDGER)

# Design choices to notice:
# - A denial is returned to the model as a tool error, so it can explain and
#   stop instead of crashing or silently retrying.
# - The approver sees the exact tool and arguments.
# - Three levels: always allow (reads) / allow by policy (small) / always ask (large).
#
# In a real product the human is not at a terminal. The run CHECKPOINTS at the
# approval point (Lab 5.3), a notification goes out, and the run resumes hours
# later when someone clicks approve. Pause = checkpoint. Approve = resume.
#
# Try it:
# 1. Run with --ask and deny everything. Does the agent behave sensibly?
# 2. Add "approve and remember for this session" so repeated identical
#    approvals are not asked twice. What is the risk of remembering too broadly?
# 3. Approval fatigue: if people are asked 50 times a day they stop reading.
#    Which calls in your own project truly need a human?
