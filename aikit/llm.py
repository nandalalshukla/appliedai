"""aikit.llm - the thin layer every lab in the course shares.

It does three things and nothing else:

1. get_client()  -> a real `anthropic.Anthropic()` client when you have an API
                    key, or a FakeClient that replays a script when you don't.
2. text_of()     -> pull the text out of a response.
3. CostMeter     -> add up tokens and dollars across calls.

The fake client has the same shape as the real one (`client.messages.create`,
`response.content`, `response.stop_reason`, `response.usage`), so the code you
write in mock mode is the exact code that runs against the real API.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Iterable

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

MODEL = os.getenv("AIKIT_MODEL", "claude-opus-5-5")
MAX_TOKENS = 16000

# USD per 1M tokens (input, output). Check the pricing page before trusting
# these for a real budget - prices change.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def mock_mode() -> bool:
    """True when labs should run offline against scripted responses."""
    if os.getenv("AIKIT_MOCK", "").strip() in {"1", "true", "yes"}:
        return True
    return not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


# --------------------------------------------------------------------------
# Building fake responses
# --------------------------------------------------------------------------

def _usage(inp: int = 0, out: int = 0, cache_read: int = 0, cache_write: int = 0):
    return SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
    )


def fake_text(text: str, *, stop_reason: str = "end_turn", **usage) -> SimpleNamespace:
    """A scripted assistant turn that is plain text."""
    return SimpleNamespace(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        role="assistant",
        model="mock",
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=_usage(**usage) if usage else _usage(len(text) // 4, len(text) // 4),
    )


def fake_tool(name: str, input: dict, text: str = "") -> SimpleNamespace:
    """A scripted assistant turn that asks to call one tool."""
    return fake_tools([(name, input)], text)


def fake_tools(calls: Iterable[tuple[str, dict]], text: str = "") -> SimpleNamespace:
    """A scripted assistant turn that asks to call several tools at once."""
    content: list[Any] = []
    if text:
        content.append(SimpleNamespace(type="text", text=text))
    for name, inp in calls:
        content.append(
            SimpleNamespace(
                type="tool_use", id=f"toolu_{uuid.uuid4().hex[:12]}", name=name, input=inp
            )
        )
    return SimpleNamespace(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        role="assistant",
        model="mock",
        content=content,
        stop_reason="tool_use",
        usage=_usage(50, 30),
    )


Responder = Callable[[dict], SimpleNamespace]


class FakeClient:
    """Stands in for `anthropic.Anthropic()` when you have no API key.

    Give it either:
      script    - a list of responses, replayed in order (a str becomes text)
      responder - a function (request kwargs) -> response, for dynamic behaviour

    Every request is recorded in `.calls` so tests can assert on what was sent.
    """

    def __init__(self, script: list | None = None, responder: Responder | None = None):
        self._script = list(script or [])
        self._responder = responder
        self.calls: list[dict] = []
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self._responder is not None:
            out = self._responder(kwargs)
        elif self._script:
            out = self._script.pop(0)
        else:
            out = "[mock] No scripted reply left. Set ANTHROPIC_API_KEY to talk to a real model."
        return fake_text(out) if isinstance(out, str) else out

    def stream(self, **kwargs) -> "_FakeStream":
        """Mimics client.messages.stream(): yields the reply a few characters at a time."""
        return _FakeStream(self.create(**kwargs))

    def parse(self, *, output_format, **kwargs) -> SimpleNamespace:
        """Mimics client.messages.parse(): validates JSON text into a Pydantic model."""
        response = self.create(**kwargs)
        response.parsed_output = output_format.model_validate_json(text_of(response))
        return response


class _FakeStream:
    def __init__(self, final):
        self._final = final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        text = text_of(self._final)
        for i in range(0, len(text), 8):
            yield text[i : i + 8]

    def get_final_message(self):
        return self._final


def get_client(script: list | None = None, responder: Responder | None = None):
    """Real client if credentials exist, otherwise a FakeClient.

    Labs pass a `script` so they still demonstrate the full flow offline.
    """
    if mock_mode():
        return FakeClient(script=script, responder=responder)
    import anthropic

    return anthropic.Anthropic()


# --------------------------------------------------------------------------
# Reading responses
# --------------------------------------------------------------------------

def text_of(response) -> str:
    """Join every text block of a response. Raises if the model refused."""
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("The model declined this request (stop_reason='refusal').")
    return "".join(b.text for b in response.content if b.type == "text")


def tool_calls(response) -> list:
    return [b for b in response.content if b.type == "tool_use"]


def to_jsonable(content) -> Any:
    """Turn response content blocks into plain dicts (for saving checkpoints)."""
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if isinstance(b, dict):
            out.append(b)
        elif hasattr(b, "model_dump"):  # real SDK objects are Pydantic models
            out.append(b.model_dump(exclude_none=True))
        else:  # FakeClient blocks
            out.append(dict(vars(b)))
    return out


# --------------------------------------------------------------------------
# Counting cost
# --------------------------------------------------------------------------

@dataclass
class CostMeter:
    """Add every response to it; read .usd and .summary() at the end."""

    model: str = MODEL
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0
    history: list = field(default_factory=list)

    def add(self, response) -> None:
        u = response.usage
        self.calls += 1
        self.input_tokens += getattr(u, "input_tokens", 0) or 0
        self.output_tokens += getattr(u, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0

    @property
    def usd(self) -> float:
        p_in, p_out = PRICES.get(self.model, PRICES["claude-opus-5-5"])
        return (
            self.input_tokens * p_in
            + self.cache_write_tokens * p_in * 1.25  # writing to cache costs a bit more
            + self.cache_read_tokens * p_in * 0.10  # reading from cache is ~10x cheaper
            + self.output_tokens * p_out
        ) / 1_000_000

    def summary(self) -> str:
        return (
            f"{self.calls} calls | in={self.input_tokens} out={self.output_tokens} "
            f"cache_read={self.cache_read_tokens} cache_write={self.cache_write_tokens} "
            f"| ~${self.usd:.4f}"
        )


def pretty(obj) -> str:
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)
