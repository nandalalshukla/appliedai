"""Lab 8.4 - Self-evolving agents: learning from failures, safely.

A "self-evolving" (self-improving) agent changes its own future behaviour
from experience. In almost every real system this does NOT mean retraining
the model. It means the agent edits something that is fed back into its
context next time:

    a playbook of lessons     (procedural memory)   <- this lab
    its prompts or tool descriptions
    a library of solved examples or reusable skills

The danger is obvious: an agent that rewrites its own instructions can make
itself worse, or be manipulated into doing so. So every proposed change goes
through the same gate as a human's change: the eval suite.

    run tasks -> collect failures -> REFLECT: propose a lesson
              -> EVALUATE the playbook with the lesson added
              -> ACCEPT only if nothing regressed  (otherwise discard)

Run:  python modules/08-production/labs/04_self_evolving.py
"""

from aikit import MODEL, get_client, text_of
from aikit.evals import Case, compare, exact_match, run_eval

CASES = [
    Case("s1", "Charged twice this month", "billing"),
    Case("s2", "App crashes on launch", "bug"),
    Case("s3", "Refund page shows a blank screen", "bug"),          # fails without a lesson
    Case("s4", "Invoice download button does nothing", "bug"),      # fails without a lesson
    Case("s5", "Forgot my password", "account"),
    Case("s6", "Can't log in to change my card", "account"),        # fails without a lesson
    Case("s7", "Do you have a student discount?", "billing"),
    Case("s8", "The card form crashes when I submit it", "bug"),
]

BASE_PROMPT = "Route the support message to one queue: billing, bug, account, other. Reply with the queue only."

GOOD_LESSON = "A broken page, button or screen is a bug, even when it is on a billing page."
BAD_LESSON = "Anything that mentions money, cards, invoices or refunds is billing."
LOGIN_LESSON = "If the customer cannot log in, route to account regardless of what they wanted to do after."


def simulated_router(playbook: list[str]):
    """Offline stand-in for the model: its accuracy depends on which lessons it was given."""
    def route(message: str) -> str:
        m = message.lower()
        if BAD_LESSON in playbook and any(w in m for w in ("refund", "invoice", "card", "discount", "charged")):
            return "billing"
        if LOGIN_LESSON in playbook and "log in" in m:
            return "account"
        if GOOD_LESSON in playbook and any(w in m for w in ("blank screen", "button does nothing")):
            return "bug"
        if "crash" in m:
            return "bug"
        if any(w in m for w in ("refund", "invoice", "card", "discount", "charged")):
            return "billing"
        return "account" if "password" in m else "other"
    return route


def evaluate(playbook: list[str], name: str):
    # Live mode would build the system prompt as BASE_PROMPT + playbook and call the model.
    return run_eval(name, CASES, simulated_router(playbook), [exact_match])


REFLECT_SYSTEM = """You improve a ticket-routing agent by writing ONE general lesson for its playbook.
You are shown cases it got wrong. Write a single short rule that would fix them without
breaking other cases. State a general principle; do not mention specific tickets."""

reflector = get_client(script=[BAD_LESSON, GOOD_LESSON, LOGIN_LESSON])


def reflect(failures) -> str:
    listing = "\n".join(f"- message: {r.input!r} | routed to: {r.output} | correct: "
                        f"{next(c.expected for c in CASES if c.id == r.case_id)}" for r in failures)
    r = reflector.messages.create(model=MODEL, max_tokens=4000, system=REFLECT_SYSTEM,
                                  messages=[{"role": "user", "content": f"Failed cases:\n{listing}"}])
    return text_of(r).strip()


if __name__ == "__main__":
    playbook: list[str] = []
    current = evaluate(playbook, "gen-0")
    print(f"generation 0: {current.pass_rate:.0%}  playbook: (empty)")

    for generation in range(1, 4):
        failures = current.failures()
        if not failures:
            break
        lesson = reflect(failures)
        candidate = evaluate(playbook + [lesson], f"gen-{generation}")
        diff = compare(current, candidate)
        accepted = candidate.pass_rate > current.pass_rate and not diff["regressed"]
        print(f"\ngeneration {generation}: proposed lesson: {lesson!r}")
        print(f"  pass rate {current.pass_rate:.0%} -> {candidate.pass_rate:.0%} | "
              f"fixed {diff['fixed']} | regressed {diff['regressed']}")
        print(f"  {'ACCEPTED' if accepted else 'REJECTED - playbook unchanged'}")
        if accepted:
            playbook, current = playbook + [lesson], candidate

    print(f"\nfinal: {current.pass_rate:.0%} with {len(playbook)} lessons:")
    for line in playbook:
        print("  -", line)

# What to notice:
# - Generation 1 proposes a plausible-sounding rule that fixes nothing and BREAKS a case.
#   Without the eval gate it would have been written into the agent for good.
# - The agent only improves as far as its eval set can see. A thin eval set
#   produces an agent overfitted to it. Use a held-out set as the final check.
#
# Guard rails for anything self-modifying:
# 1. Changes are proposals. An eval (and for high-stakes systems, a human) accepts them.
# 2. Every change is versioned and reversible.
# 3. Lessons come from verified outcomes, never from instructions found in
#    user content or tool results (that would be self-inflicted prompt injection).
# 4. Cap the playbook size and prune: 200 lessons is a prompt nobody can reason about.
# 5. Monitor for drift after acceptance, exactly as for a human-made change.
#
# Try it:
# 1. Remove the "not diff['regressed']" condition. What ends up in the playbook?
# 2. Add a held-out case set and report it at the end.
# 3. Live mode: build the real prompt from BASE_PROMPT + playbook and let a real
#    model both route and reflect.
