"""Lab 5.1 - Anatomy of an agent: the observe-think-act loop.

An agent = a model + tools + a loop + a stopping rule. You built the loop in
Lab 3.3. Here it is as a reusable class (aikit/agent.py - read it, it is short)
with the safety rails a loop needs before you can leave it running.

Run:  python modules/05-agents/labs/01_agent_loop.py
"""

from aikit import fake_tool, fake_tools, get_client
from aikit.agent import Agent, print_events
from aikit.tools import ToolRegistry

registry = ToolRegistry()
TICKETS = {
    "T-1": {"customer": "asha@example.com", "text": "Charged twice for my October invoice", "status": "open"},
    "T-2": {"customer": "ben@example.com", "text": "How do I export data?", "status": "open"},
}
CHARGES = {"asha@example.com": [{"date": "2026-10-01", "usd": 29}, {"date": "2026-10-01", "usd": 29}]}


@registry.tool()
def get_ticket(ticket_id: str) -> dict:
    """Fetch a support ticket by id (e.g. 'T-1'). Returns customer email, text and status."""
    return TICKETS[ticket_id]


@registry.tool()
def list_charges(customer_email: str) -> list:
    """List this month's charges for a customer. Returns [{date, usd}]. Use to verify billing complaints."""
    return CHARGES.get(customer_email, [])


@registry.tool(read_only=False)
def add_note(ticket_id: str, note: str) -> str:
    """Attach an internal note to a ticket for the human support team."""
    TICKETS[ticket_id].setdefault("notes", []).append(note)
    return "note added"


SYSTEM = """You are a support investigator. For the ticket you are given:
1. Read the ticket.
2. Verify the customer's claim with the tools. Never assume a claim is true.
3. Add one internal note stating what you verified and what a human should do next.
Then reply with a one-line summary. You cannot issue refunds yourself."""

client = get_client(script=[
    fake_tool("get_ticket", {"ticket_id": "T-1"}),                                 # observe
    fake_tool("list_charges", {"customer_email": "asha@example.com"}),             # verify
    fake_tool("add_note", {"ticket_id": "T-1", "note": "Verified: two $29 charges on 2026-10-01. "
                                                       "Duplicate confirmed. Refund one charge."}),  # act
    "T-1: duplicate $29 charge on 2026-10-01 confirmed; note added recommending a refund.",
])

agent = Agent(client, registry, SYSTEM, max_steps=10, on_event=print_events)
result = agent.run("Investigate ticket T-1.")

print(f"\nstopped: {result.stopped} after {result.steps} steps | {result.meter.summary()}")
print("answer: ", result.text)
print("notes:  ", TICKETS["T-1"].get("notes"))

# The anatomy, mapped to this file:
#   model         - decides the next step
#   tools         - what it can observe (get_ticket, list_charges) and do (add_note)
#   instructions  - SYSTEM: goal, procedure, limits
#   state         - result.messages: the entire memory of this run
#   loop + stop   - Agent.run: ends when the model stops calling tools,
#                   or at max_steps / max_usd / a repeated call
#
# Try it:
# 1. Set max_steps=2. What does `stopped` say? What should a product do then?
# 2. Change the scripted model to call get_ticket("T-1") forever. Watch the
#    loop guard fire. (Hint: responder=lambda kwargs: fake_tool(...).)
# 3. Print result.messages. This transcript is what you read when debugging.
