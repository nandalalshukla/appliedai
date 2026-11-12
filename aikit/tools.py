"""aikit.tools - tool infrastructure: define, describe, validate, run, report.

A "tool" is a function the model may ask you to run. The model never runs
anything; it emits a request (name + JSON arguments) and YOUR code decides
whether and how to execute it. This module is the layer in between:

    @registry.tool()            define a tool from a typed Python function
    registry.schemas()          the JSON schemas you send to the model
    registry.execute(name, in)  validate arguments, run with a timeout,
                                turn every failure into a message the model can act on
    registry.run_calls(resp)    run all tool calls in a response (in parallel)
                                and build the tool_result blocks to send back
"""

from __future__ import annotations

import inspect
import json
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError, create_model


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    args_model: type[BaseModel]
    needs_approval: bool = False  # used by the human-in-the-loop lab (Module 5)
    read_only: bool = True  # read-only tools are safe to run in parallel
    timeout_s: float = 30.0

    def schema(self) -> dict:
        js = self.args_model.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": js.get("properties", {}),
                "required": js.get("required", []),
                "additionalProperties": False,
            },
        }


@dataclass
class ToolResult:
    content: str
    is_error: bool = False
    seconds: float = 0.0


@dataclass
class ToolRegistry:
    max_result_chars: int = 8000  # tool output goes into the context window: cap it
    tools: dict[str, Tool] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)

    def tool(self, *, needs_approval: bool = False, read_only: bool = True, timeout_s: float = 30.0):
        """Decorator. The function's signature becomes the schema and its
        docstring becomes the description the model reads."""

        def wrap(fn: Callable) -> Callable:
            fields = {}
            for pname, p in inspect.signature(fn).parameters.items():
                annotation = p.annotation if p.annotation is not inspect.Parameter.empty else str
                default = ... if p.default is inspect.Parameter.empty else p.default
                fields[pname] = (annotation, default)
            args_model = create_model(f"{fn.__name__}_args", **fields)
            description = inspect.cleandoc(fn.__doc__ or "")
            if not description:
                raise ValueError(f"Tool {fn.__name__!r} needs a docstring: the model reads it.")
            self.tools[fn.__name__] = Tool(
                fn.__name__, description, fn, args_model, needs_approval, read_only, timeout_s
            )
            return fn

        return wrap

    def schemas(self) -> list[dict]:
        # Sorted so the request bytes are identical every time (keeps prompt caching working).
        return [self.tools[name].schema() for name in sorted(self.tools)]

    def execute(self, name: str, raw_input: dict) -> ToolResult:
        """Never raises. Every failure becomes an error message for the model."""
        start = time.perf_counter()
        result = self._execute(name, raw_input)
        result.seconds = round(time.perf_counter() - start, 3)
        self.log.append(
            {"tool": name, "input": raw_input, "is_error": result.is_error,
             "seconds": result.seconds, "chars": len(result.content)}
        )
        return result

    def _execute(self, name: str, raw_input: dict) -> ToolResult:
        tool = self.tools.get(name)
        if tool is None:
            return ToolResult(f"Unknown tool {name!r}. Available: {sorted(self.tools)}", True)
        try:
            args = tool.args_model.model_validate(raw_input)
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            return ToolResult(f"Invalid arguments for {name}: {problems}", True)

        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(tool.fn, **args.model_dump())
        try:
            value = future.result(timeout=tool.timeout_s)
        except FutureTimeout:
            return ToolResult(f"{name} timed out after {tool.timeout_s}s. Try a narrower request.", True)
        except Exception as e:  # the tool's own failure: tell the model what went wrong
            return ToolResult(f"{name} failed: {type(e).__name__}: {e}", True)
        finally:
            pool.shutdown(wait=False)

        text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
        if len(text) > self.max_result_chars:
            dropped = len(text) - self.max_result_chars
            text = text[: self.max_result_chars] + (
                f"\n[truncated {dropped} characters. Ask for a narrower result.]"
            )
        return ToolResult(text)

    def run_calls(self, response, approve: Callable[[Tool, dict], bool] | None = None) -> list[dict]:
        """Run every tool_use block in `response`; return tool_result blocks.

        All results go back in ONE user message, in the same order as the calls.
        """
        calls = [b for b in response.content if b.type == "tool_use"]

        def run_one(call) -> dict:
            tool = self.tools.get(call.name)
            if tool and tool.needs_approval and approve is not None and not approve(tool, call.input):
                result = ToolResult("The user declined this action. Do not retry it; ask what to do instead.", True)
            else:
                result = self.execute(call.name, call.input)
            block = {"type": "tool_result", "tool_use_id": call.id, "content": result.content}
            if result.is_error:
                block["is_error"] = True
            return block

        all_read_only = all(self.tools.get(c.name) and self.tools[c.name].read_only for c in calls)
        if len(calls) > 1 and all_read_only:
            with ThreadPoolExecutor(max_workers=min(8, len(calls))) as pool:
                return list(pool.map(run_one, calls))  # map() preserves order
        return [run_one(c) for c in calls]  # anything that writes runs one at a time
