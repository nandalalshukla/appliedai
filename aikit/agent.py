"""aikit.agent - a complete agent loop in about 100 lines.

An agent is a model calling tools in a loop until the task is done:

    observe (read the history, including the last tool results)
    think   (the model decides what to do next)
    act     (your code runs the tools it asked for)
    ...repeat until the model answers without asking for a tool.

Everything else in this file is what makes that loop safe to run unattended:
a step limit, a spend limit, repeated-call detection, human approval,
checkpoints you can resume from, and an event stream you can log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .llm import MAX_TOKENS, MODEL, CostMeter, text_of, to_jsonable, tool_calls
from .tools import Tool, ToolRegistry


@dataclass
class AgentResult:
    text: str
    stopped: str  # "done" | "max_steps" | "budget" | "loop" | "refusal" | "max_tokens"
    steps: int
    messages: list
    meter: CostMeter


@dataclass
class Agent:
    client: object
    registry: ToolRegistry
    system: str
    model: str = MODEL
    max_tokens: int = MAX_TOKENS
    max_steps: int = 20
    max_usd: float | None = None
    approve: Callable[[Tool, dict], bool] | None = None  # human in the loop
    on_event: Callable[[str, dict], None] | None = None  # tracing hook
    checkpoint: Path | None = None  # save state here after every step
    meter: CostMeter = field(default_factory=CostMeter)

    def _emit(self, kind: str, **data) -> None:
        if self.on_event:
            self.on_event(kind, data)

    def _save(self, messages: list, step: int) -> None:
        if self.checkpoint:
            self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
            state = {"step": step, "messages": [
                {"role": m["role"], "content": to_jsonable(m["content"])} for m in messages
            ]}
            tmp = self.checkpoint.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, default=str))
            tmp.replace(self.checkpoint)  # atomic: never leaves a half-written file

    def resume(self) -> AgentResult:
        """Continue from the last checkpoint instead of starting over."""
        state = json.loads(self.checkpoint.read_text())
        self._emit("resumed", step=state["step"])
        return self.run(messages=state["messages"], start_step=state["step"])

    def run(self, task: str | None = None, messages: list | None = None, start_step: int = 0) -> AgentResult:
        messages = messages if messages is not None else [{"role": "user", "content": task}]
        recent_calls: list[str] = []

        for step in range(start_step + 1, self.max_steps + 1):
            # THINK
            response = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens, system=self.system,
                tools=self.registry.schemas(), messages=messages,
            )
            self.meter.add(response)
            self._emit("model", step=step, stop_reason=response.stop_reason)

            if response.stop_reason in ("refusal", "max_tokens"):
                return AgentResult("", response.stop_reason, step, messages, self.meter)

            messages.append({"role": "assistant", "content": response.content})
            calls = tool_calls(response)
            if not calls:  # no tool requested -> the model is finished
                self._save(messages, step)
                return AgentResult(text_of(response), "done", step, messages, self.meter)

            # Guard: the same call three times in a row means the agent is stuck.
            signature = json.dumps([(c.name, c.input) for c in calls], sort_keys=True, default=str)
            recent_calls.append(signature)
            if recent_calls[-3:] == [signature] * 3:
                return AgentResult("Stopped: repeating the same action.", "loop", step, messages, self.meter)

            # ACT
            for c in calls:
                self._emit("tool_call", step=step, name=c.name, input=c.input)
            results = self.registry.run_calls(response, approve=self.approve)
            for r in results:
                self._emit("tool_result", step=step, is_error=r.get("is_error", False),
                           preview=str(r["content"])[:200])

            # OBSERVE (the results become part of what the model reads next turn)
            messages.append({"role": "user", "content": results})
            self._save(messages, step)

            if self.max_usd is not None and self.meter.usd > self.max_usd:
                return AgentResult("Stopped: budget exceeded.", "budget", step, messages, self.meter)

        return AgentResult("Stopped: step limit reached.", "max_steps", self.max_steps, messages, self.meter)


def print_events(kind: str, data: dict) -> None:
    """A ready-made on_event hook that prints a readable trace."""
    if kind == "tool_call":
        print(f"  [{data['step']}] -> {data['name']}({json.dumps(data['input'], default=str)[:120]})")
    elif kind == "tool_result":
        mark = "x" if data["is_error"] else "<-"
        print(f"  [{data['step']}] {mark} {data['preview'][:120]!r}")
    elif kind == "resumed":
        print(f"  (resumed from checkpoint at step {data['step']})")
