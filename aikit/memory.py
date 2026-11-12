"""aikit.memory - working memory (the context window) and long-term memory.

WORKING MEMORY is the message list. It is finite and you pay for it on every
call, so it needs a budget:
    estimate_tokens(messages)       rough size of the history
    compact(client, messages, ...)  replace old turns with a summary

LONG-TERM MEMORY survives across conversations. It has two paths:
    WRITE path  remember(...)  extract durable facts -> add / update / skip
    READ path   recall(...)    find the few memories relevant to this moment
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .embed import get_embedder
from .llm import MODEL, text_of, to_jsonable

# -- working memory ----------------------------------------------------------


def estimate_tokens(messages: list) -> int:
    """Rough estimate (4 characters per token). Use the provider's token
    counting endpoint when you need an exact number."""
    return sum(len(json.dumps(to_jsonable(m["content"]), default=str)) for m in messages) // 4


def _is_plain_user_turn(message: dict) -> bool:
    """True for a user message that is NOT carrying tool results."""
    if message["role"] != "user":
        return False
    content = message["content"]
    if isinstance(content, str):
        return True
    return not any((b.get("type") if isinstance(b, dict) else getattr(b, "type", "")) == "tool_result"
                   for b in content)


def safe_cut(messages: list, keep_last: int) -> int:
    """Index where the kept tail starts. A tool_use and its tool_result must
    stay together, so the tail must begin at a plain user message."""
    cut = max(0, len(messages) - keep_last)
    while cut > 0 and not _is_plain_user_turn(messages[cut]):
        cut -= 1
    return cut


SUMMARY_SYSTEM = """You compress the earlier part of a conversation so work can continue without it.
Write a summary that preserves: the user's goal, decisions made, facts and identifiers learned
(names, IDs, numbers, file paths), what has been done, and what remains to do.
Leave out pleasantries and dead ends. Be specific; the summary replaces the original."""


def compact(client, messages: list, keep_last: int = 6, model: str = MODEL) -> list:
    """Summarise everything except the most recent turns."""
    cut = safe_cut(messages, keep_last)
    if cut == 0:
        return messages
    old = json.dumps([{"role": m["role"], "content": to_jsonable(m["content"])} for m in messages[:cut]],
                     default=str)
    response = client.messages.create(
        model=model, max_tokens=4000, system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": f"<conversation>\n{old}\n</conversation>\n\nWrite the summary."}],
    )
    note = f"<summary_of_earlier_conversation>\n{text_of(response)}\n</summary_of_earlier_conversation>\n\n"
    first = messages[cut]
    if isinstance(first["content"], str):
        merged = {"role": "user", "content": note + first["content"]}
    else:
        merged = {"role": "user", "content": [{"type": "text", "text": note}, *first["content"]]}
    return [merged, *messages[cut + 1 :]]


# -- long-term memory --------------------------------------------------------


@dataclass
class Memory:
    id: int
    text: str
    kind: str = "fact"  # "fact" | "preference" | "episode"
    importance: int = 3  # 1 (trivia) .. 5 (critical)
    created: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)


EXTRACT_SYSTEM = """You decide what an assistant should remember about a user for FUTURE conversations.

From the exchange, extract only durable information: stable facts about the user, their
preferences, and decisions that will still matter next week. Skip small talk, one-off
requests, and anything already in the existing memories unless it has CHANGED.

Return JSON: {"operations": [
  {"op": "add", "text": "...", "kind": "fact|preference|episode", "importance": 1-5},
  {"op": "update", "id": <existing memory id>, "text": "<new text replacing the old>"}
]}
Return {"operations": []} when nothing is worth remembering. Write each memory as a
self-contained sentence in the third person ("The user ...")."""


class MemoryStore:
    """A small file-backed memory with embedding recall. One store per user."""

    def __init__(self, path: str | Path, embedder=None):
        self.path = Path(path)
        self.embedder = embedder or get_embedder()
        self.items: list[Memory] = []
        if self.path.exists():
            self.items = [Memory(**json.loads(line)) for line in self.path.read_text().splitlines() if line]

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(json.dumps(asdict(m)) for m in self.items))

    # WRITE PATH -------------------------------------------------------------
    def remember(self, client, exchange: str, model: str = MODEL) -> list[dict]:
        """Extract -> decide add/update/skip -> persist. Returns the operations applied."""
        related = self.recall(exchange, k=5, touch=False)  # show the model what we already know
        known = "\n".join(f"[{m.id}] {m.text}" for m in related) or "(none)"
        response = client.messages.create(
            model=model, max_tokens=2000, system=EXTRACT_SYSTEM,
            messages=[{"role": "user", "content":
                       f"<existing_memories>\n{known}\n</existing_memories>\n\n<exchange>\n{exchange}\n</exchange>"}],
        )
        try:
            operations = json.loads(text_of(response)).get("operations", [])
        except (ValueError, AttributeError):
            return []  # extraction failed: remember nothing rather than something wrong
        applied = []
        for op in operations:
            if op.get("op") == "add" and op.get("text"):
                next_id = max((m.id for m in self.items), default=0) + 1
                self.items.append(Memory(next_id, op["text"], op.get("kind", "fact"),
                                         int(op.get("importance", 3))))
                applied.append(op)
            elif op.get("op") == "update":
                target = next((m for m in self.items if m.id == op.get("id")), None)
                if target and op.get("text"):
                    target.text, target.created = op["text"], time.time()
                    applied.append(op)
        self._persist()
        return applied

    # READ PATH --------------------------------------------------------------
    def recall(self, query: str, k: int = 3, touch: bool = True) -> list[Memory]:
        """Rank by relevance, nudged by importance and recency."""
        if not self.items:
            return []
        vectors = self.embedder.embed([m.text for m in self.items])
        relevance = vectors @ self.embedder.embed([query])[0]
        now = time.time()
        scores = []
        for m, rel in zip(self.items, relevance):
            days_old = (now - m.created) / 86400
            recency = 0.5 ** (days_old / 30)  # halves every 30 days
            scores.append(float(rel) + 0.05 * m.importance + 0.1 * recency)
        top = [self.items[i] for i in np.argsort(scores)[::-1][:k]]
        if touch:
            for m in top:
                m.last_used = now
            self._persist()
        return top

    def as_context(self, query: str, k: int = 3) -> str:
        memories = self.recall(query, k)
        if not memories:
            return ""
        lines = "\n".join(f"- {m.text}" for m in memories)
        return f"<memories_about_user>\n{lines}\n</memories_about_user>"
