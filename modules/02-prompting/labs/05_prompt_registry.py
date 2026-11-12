"""Lab 2.5 - Infrastructure around prompts.

In a real product a prompt is not a string in a function. It is a versioned
asset with variables, an owner, and a paper trail. This is a minimal registry:

- prompts live in one place, with a name and a version
- rendering fails loudly if a variable is missing
- every call logs which prompt version produced which output

Run:  python modules/02-prompting/labs/05_prompt_registry.py
"""

import hashlib
import json
import string
import time
from dataclasses import dataclass
from pathlib import Path

from aikit import MODEL, get_client, text_of

LOG = Path("runs/prompt_log.jsonl")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    user_template: str

    @property
    def fingerprint(self) -> str:
        """Short hash of the content. If someone edits the text without bumping
        the version, the fingerprint in your logs gives it away."""
        return hashlib.sha256((self.system + self.user_template).encode()).hexdigest()[:10]

    def render(self, **variables) -> str:
        needed = {f for _, f, _, _ in string.Formatter().parse(self.user_template) if f}
        missing = needed - variables.keys()
        if missing:
            raise ValueError(f"{self.name}@{self.version}: missing variables {sorted(missing)}")
        return self.user_template.format(**variables)


REGISTRY: dict[tuple[str, str], Prompt] = {}


def register(p: Prompt) -> Prompt:
    REGISTRY[(p.name, p.version)] = p
    return p


register(Prompt(
    name="summarize_review", version="v1",
    system="Summarize the review in one sentence.",
    user_template="{review}",
))
register(Prompt(
    name="summarize_review", version="v2",
    system="You write one-line review summaries for support agents. At most 20 words. "
           "Lead with the main problem. Use only facts in the review.",
    user_template="<review>\n{review}\n</review>\n\nWrite the summary.",
))

# Which version is live is CONFIG, not code. Rolling back is a one-line change.
ACTIVE = {"summarize_review": "v2"}


def run_prompt(client, name: str, **variables) -> str:
    prompt = REGISTRY[(name, ACTIVE[name])]
    started = time.time()
    response = client.messages.create(
        model=MODEL, max_tokens=2000, system=prompt.system,
        messages=[{"role": "user", "content": prompt.render(**variables)}],
    )
    output = text_of(response)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:  # one JSON object per line: easy to grep and to load
        f.write(json.dumps({
            "ts": started, "prompt": name, "version": prompt.version,
            "fingerprint": prompt.fingerprint, "model": MODEL, "variables": variables,
            "output": output, "latency_s": round(time.time() - started, 3),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }) + "\n")
    return output


if __name__ == "__main__":
    client = get_client(script=["Battery failed in two days; customer is returning it."])
    print(run_prompt(client, "summarize_review", review="Battery died after 2 days. Returning it."))
    print("logged ->", LOG, "\n", LOG.read_text().splitlines()[-1][:160], "...")

    try:
        run_prompt(client, "summarize_review")  # forgot the variable
    except ValueError as e:
        print("caught:", e)

# Try it:
# 1. Add v3 and switch ACTIVE to it. Then roll back. Notice no code changed.
# 2. Send 10% of calls to v3 and 90% to v2 (an A/B test). Log which was used.
# 3. Module 7 connects this to evals: a new version ships only if it scores
#    at least as well as the active one on your eval set.
