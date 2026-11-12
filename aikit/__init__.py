"""aikit - the tiny teaching toolkit used across the Applied AI Masterclass."""

from .llm import (
    MAX_TOKENS,
    MODEL,
    CostMeter,
    FakeClient,
    fake_text,
    fake_tool,
    fake_tools,
    get_client,
    mock_mode,
    pretty,
    text_of,
    to_jsonable,
    tool_calls,
)

__all__ = [
    "MAX_TOKENS", "MODEL", "CostMeter", "FakeClient", "fake_text", "fake_tool",
    "fake_tools", "get_client", "mock_mode", "pretty", "text_of", "to_jsonable",
    "tool_calls",
]
