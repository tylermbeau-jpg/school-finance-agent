"""The agent loop: Claude answers a school-finance question by calling MCP tools.

The LLM client is injected (anything exposing messages.create), so the loop is
integration-testable against the real MCP server with a scripted stub model.
"""

from __future__ import annotations

import os

from .bridge import call_mcp_tool, list_anthropic_tools

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM = (
    "You are a California school-finance assistant with tools for SACS account "
    "strings and school-meal reimbursement. Use the tools for anything factual; "
    "do not answer SACS or reimbursement questions from memory. Ground every "
    "claim in a tool result and say which tool produced it. If the tools cannot "
    "answer the question, say so plainly."
)


def make_client():
    """Real Anthropic client from $ANTHROPIC_API_KEY."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set; export it to run the live agent.")
    import anthropic

    return anthropic.Anthropic()


async def run_agent(
    client,
    session,
    question: str,
    *,
    model: str = DEFAULT_MODEL,
    max_turns: int = 8,
) -> dict:
    """Run the tool-use loop. Returns {"answer": str, "tool_calls": [...]}."""
    tools = await list_anthropic_tools(session)
    messages = [{"role": "user", "content": question}]
    tool_calls: list[dict] = []

    for _ in range(max_turns):
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        blocks = response.content
        messages.append({"role": "assistant", "content": blocks})

        if response.stop_reason != "tool_use":
            answer = "\n".join(b.text for b in blocks if getattr(b, "text", None))
            return {"answer": answer, "tool_calls": tool_calls}

        results = []
        for block in blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            output = await call_mcp_tool(session, block.name, block.input)
            tool_calls.append({"tool": block.name, "input": block.input, "output": output})
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )
        messages.append({"role": "user", "content": results})

    return {
        "answer": "Stopped: exceeded the maximum number of tool-use turns.",
        "tool_calls": tool_calls,
    }
