"""Lab 2.3 - Structured outputs: getting data, not prose.

Your code cannot use "Sure! The customer seems upset and...". It needs fields.
This lab shows the recommended path (schema-constrained output) and the
gotchas that remain even when the JSON is guaranteed valid.

Run:  python modules/02-prompting/labs/03_structured_outputs.py
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from aikit import MODEL, get_client


class Ticket(BaseModel):
    # GOTCHA 1: field order matters. The model fills fields top to bottom, so put
    # the reasoning BEFORE the decision that should depend on it.
    reasoning: str = Field(description="One sentence: what is the root problem?")
    category: Literal["billing", "bug", "account", "other"]
    urgency: Literal["low", "medium", "high"]
    # GOTCHA 2: give the model a legal way to say "I don't know". If a field is
    # required and the text does not contain it, the model will invent a value.
    order_id: Optional[str] = Field(
        description="Order ID exactly as written in the message, or null if none is given."
    )
    # GOTCHA 3: descriptions are prompt text. Vague field names produce vague data.
    summary: str = Field(description="At most 15 words, written for a support agent.")


SYSTEM = "Extract a support ticket from the customer's message. Use only what the message says."

MESSAGE = "URGENT: charged twice for order #A-4471, need this fixed before rent is due tomorrow!"

client = get_client(
    script=[
        '{"reasoning": "Customer was double charged and has a deadline tomorrow.", '
        '"category": "billing", "urgency": "high", "order_id": "A-4471", '
        '"summary": "Double charge on order A-4471; needs refund before tomorrow."}'
    ]
)

# messages.parse() sends the Pydantic model as a JSON schema, constrains the
# model's output to it, and validates the result into a Ticket instance.
response = client.messages.parse(
    model=MODEL,
    max_tokens=4000,
    system=SYSTEM,
    messages=[{"role": "user", "content": f"<message>{MESSAGE}</message>"}],
    output_format=Ticket,
)

# GOTCHA 4: constrained output guarantees the SHAPE only when the model
# finishes. Always check stop_reason before trusting the parse.
if response.stop_reason in ("max_tokens", "refusal"):
    raise RuntimeError(f"No usable output: stop_reason={response.stop_reason}")

ticket: Ticket = response.parsed_output
print(ticket.model_dump_json(indent=2))

# GOTCHA 5: valid JSON is not correct data. The schema cannot know whether
# "A-4471" really appears in the message. Check what you can in code.
if ticket.order_id and ticket.order_id not in MESSAGE:
    print("WARNING: order_id is not in the source text - likely invented.")

# More gotchas to remember:
# 6. Schemas are restricted: no recursive types, limited numeric/string
#    constraints. Keep schemas flat and simple; validate ranges in code.
# 7. Big nested schemas lower quality. Prefer two small calls over one giant one.
# 8. Changing the schema changes behaviour. Version it like code (Lab 2.5).
# 9. Enums beat free text for anything your code branches on.
#
# Try it:
# 1. Make order_id a required `str`. Send a message with no order ID. What do you get?
# 2. Move `reasoning` to the bottom of the class. Does urgency get worse on hard cases?
# 3. Add a field `refund_amount: Optional[float]`. Write the code check for it.
