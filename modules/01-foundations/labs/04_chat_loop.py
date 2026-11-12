"""Lab 1.4 - Models have no memory. A chatbot is a list you keep resending.

Run:  python modules/01-foundations/labs/04_chat_loop.py          (scripted demo)
      python modules/01-foundations/labs/04_chat_loop.py --chat   (type yourself)
"""

import sys

from aikit import MODEL, CostMeter, get_client, text_of

client = get_client(script=["Nice to meet you, Asha!", "Your name is Asha.", "I don't know your name."])
meter = CostMeter()


def ask(history: list[dict], user_text: str) -> str:
    history.append({"role": "user", "content": user_text})
    response = client.messages.create(
        model=MODEL, max_tokens=2000, system="Be brief.", messages=history
    )
    meter.add(response)
    reply = text_of(response)
    history.append({"role": "assistant", "content": reply})  # <- this line IS the memory
    return reply


def demo():
    history: list[dict] = []
    print("user: My name is Asha.\nbot: ", ask(history, "My name is Asha."))
    print("user: What is my name?\nbot: ", ask(history, "What is my name?"))
    print(f"\nThe second request carried {len(history) - 1} earlier messages with it.")

    fresh: list[dict] = []  # a new list = a model with amnesia
    print("\n(new conversation)\nuser: What is my name?\nbot: ", ask(fresh, "What is my name?"))
    print("\n" + meter.summary())


def chat():
    history: list[dict] = []
    print("Type a message. Ctrl+C to quit.")
    while True:
        print("bot:", ask(history, input("you: ")))
        print(f"     [{meter.summary()}]")


if __name__ == "__main__":
    try:
        chat() if "--chat" in sys.argv else demo()
    except (KeyboardInterrupt, EOFError):
        print()

# Try it:
# 1. In --chat mode, watch input tokens grow with every turn. You pay for the
#    whole history on every request. What happens at turn 500?
# 2. Keep only the last 4 messages before each call. What breaks?
#    (You will fix this properly in Module 6: memory.)
# 3. Delete the "history.append(assistant...)" line. What does the model see?
