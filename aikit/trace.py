"""aikit.trace - minimal tracing: what happened, in what order, how long, how much.

A TRACE is one user request end to end. It is made of SPANS: timed steps
(a model call, a tool call, a retrieval) that nest inside each other.

    tracer = Tracer()
    with tracer.span("handle_request", user="u1"):
        with tracer.span("retrieve", k=5) as s:
            ...
            s.set(hits=5)
    tracer.print_tree()

This is the same data model as OpenTelemetry, which is what you use at work.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start: float
    end: float = 0.0
    status: str = "ok"
    attrs: dict = field(default_factory=dict)

    def set(self, **attrs) -> None:
        self.attrs.update(attrs)

    @property
    def ms(self) -> float:
        return round((self.end - self.start) * 1000, 1)


class Tracer:
    def __init__(self, path: str | Path | None = None):
        self.trace_id = uuid.uuid4().hex[:16]
        self.spans: list[Span] = []
        self._stack: list[Span] = []
        self.path = Path(path) if path else None

    @contextmanager
    def span(self, name: str, **attrs):
        parent = self._stack[-1].span_id if self._stack else None
        s = Span(self.trace_id, uuid.uuid4().hex[:8], parent, name, time.perf_counter(), attrs=dict(attrs))
        self.spans.append(s)
        self._stack.append(s)
        try:
            yield s
        except Exception as e:
            s.status = "error"
            s.set(error=f"{type(e).__name__}: {e}")
            raise
        finally:
            s.end = time.perf_counter()
            self._stack.pop()
            if self.path:  # one JSON line per finished span
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a") as f:
                    f.write(json.dumps({**asdict(s), "ms": s.ms}, default=str) + "\n")

    def record_usage(self, span: Span, response, model: str) -> None:
        """Attach token counts from a model response to a span."""
        u = response.usage
        span.set(model=model, input_tokens=getattr(u, "input_tokens", 0),
                 output_tokens=getattr(u, "output_tokens", 0),
                 cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                 stop_reason=response.stop_reason)

    def print_tree(self) -> None:
        children: dict[str | None, list[Span]] = {}
        for s in self.spans:
            children.setdefault(s.parent_id, []).append(s)

        def walk(parent: str | None, depth: int) -> None:
            for s in children.get(parent, []):
                extra = " ".join(f"{k}={v}" for k, v in s.attrs.items())
                flag = "" if s.status == "ok" else "  !! ERROR"
                print(f"{'  ' * depth}{s.name:<{28 - 2 * depth}}{s.ms:>8.1f} ms  {extra}{flag}")
                walk(s.span_id, depth + 1)

        print(f"trace {self.trace_id}")
        walk(None, 1)

    def total(self, key: str) -> float:
        return sum(s.attrs.get(key, 0) or 0 for s in self.spans)
