"""Lab 5.2 - The ReAct loop, built on plain text.

ReAct (Reason + Act, 2022) is the idea behind every modern agent: let the
model alternate between THINKING out loud and ACTING, and feed it what
happened. Before APIs had tool calling, people did it with a text format:

    Thought: I need the population of France.
    Action: search[population of France]
    Observation: 68 million            <- written by YOUR code
    Thought: Now I can answer.
    Final Answer: 68 million

Building it once shows there is no magic: the "agent" is string parsing plus
a loop. Native tool calling (Lab 5.1) is the same idea with a reliable format.

Run:  python modules/05-agents/labs/02_react_from_scratch.py
"""

import re

from aikit import MODEL, get_client, text_of

FACTS = {"capital of australia": "Canberra", "population of canberra": "about 470,000"}

ACTIONS = {
    "search": lambda q: FACTS.get(q.lower().strip(), "no results"),
    "calculate": lambda e: str(eval(e, {"__builtins__": {}})),  # toy only: never eval model output in real code
}

SYSTEM = """Answer the question by alternating Thought, Action and Observation steps.

Available actions:
- search[query]: look up a fact
- calculate[expression]: do arithmetic

Use exactly this format, one step at a time, then stop and wait:
Thought: <your reasoning>
Action: <action>[<input>]

When you know the answer:
Thought: <your reasoning>
Final Answer: <answer>"""

ACTION_RE = re.compile(r"Action:\s*(\w+)\[(.*?)\]", re.S)

client = get_client(script=[
    "Thought: I first need the capital of Australia.\nAction: search[capital of Australia]",
    "Thought: The capital is Canberra. Now its population.\nAction: search[population of Canberra]",
    "Thought: I have both facts.\nFinal Answer: The capital is Canberra, with about 470,000 people.",
])


def react(question: str, max_steps: int = 6) -> str:
    transcript = f"Question: {question}"
    for _ in range(max_steps):
        reply = text_of(client.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM,
            messages=[{"role": "user", "content": transcript}],
        ))
        print(reply)
        if "Final Answer:" in reply:
            return reply.split("Final Answer:", 1)[1].strip()

        match = ACTION_RE.search(reply)
        if not match:  # the model broke the format: tell it, do not crash
            observation = "Invalid format. Reply with 'Action: name[input]' or 'Final Answer: ...'."
        else:
            name, arg = match.groups()
            fn = ACTIONS.get(name)
            observation = fn(arg) if fn else f"Unknown action {name!r}. Use: {list(ACTIONS)}"
        print(f"Observation: {observation}\n")
        transcript += f"\n{reply}\nObservation: {observation}"  # the growing scratchpad
    return "No answer within the step limit."


if __name__ == "__main__":
    print("\n=>", react("What is the capital of Australia and how many people live there?"))

# Why text ReAct was fragile, and what native tool calling fixed:
#   - the model could write its own "Observation:" line and hallucinate a result
#   - format drift broke the regex
#   - arguments were untyped strings
# Tool calling gives typed arguments, a hard stop (stop_reason="tool_use")
# and a clear boundary between what the model said and what really happened.
# The loop is unchanged.
#
# Try it:
# 1. Make the scripted model write a fake "Observation:" itself. How would you
#    detect and strip it? (Real implementations used stop sequences.)
# 2. Rewrite this with ToolRegistry + Agent. Compare the two transcripts.
