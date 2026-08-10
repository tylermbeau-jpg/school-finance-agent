"""Integration tests against the REAL school-finance-mcp server over stdio.

Only the LLM is stubbed. The MCP bridge, tool schemas, and tool execution are
the real thing.
"""

from __future__ import annotations

import json

import anyio

from sfagent.bridge import call_mcp_tool, list_anthropic_tools, open_mcp
from sfagent.loop import run_agent

EXPECTED_TOOLS = {
    "validate_sacs_string",
    "decode_sacs_string",
    "list_sacs_codes",
    "calculate_meal_reimbursement",
}


def test_bridge_lists_real_tools():
    async def go():
        async with open_mcp(stdio=True) as session:
            tools = await list_anthropic_tools(session)
            assert {t["name"] for t in tools} == EXPECTED_TOOLS
            for tool in tools:
                assert tool["input_schema"].get("type") == "object"

    anyio.run(go)


def test_bridge_executes_real_tool_call():
    async def go():
        async with open_mcp(stdio=True) as session:
            output = await call_mcp_tool(
                session, "validate_sacs_string", {"account_string": "01-0000-0-1110-1000-1100"}
            )
            assert json.loads(output)["valid"] is True

    anyio.run(go)


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Response:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class ScriptedLLM:
    """First call: request a tool. Second call: answer using the tool result."""

    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, *, model, max_tokens, system, tools, messages):
        self.calls += 1
        if self.calls == 1:
            assert {t["name"] for t in tools} == EXPECTED_TOOLS
            return _Response(
                [
                    _Block(
                        type="tool_use",
                        id="tu_1",
                        name="calculate_meal_reimbursement",
                        input={"free_lunches": 100, "california_universal_meals": True},
                    )
                ],
                "tool_use",
            )
        # the tool_result content from the real server must be in the transcript
        tool_result_msg = messages[-1]
        payload = json.loads(tool_result_msg["content"][0]["content"])
        total = payload["total_reimbursement"]
        return _Response(
            [_Block(type="text", text=f"The total reimbursement is ${total:,.2f}.")],
            "end_turn",
        )


def test_agent_loop_end_to_end_with_stub_llm():
    async def go():
        llm = ScriptedLLM()
        async with open_mcp(stdio=True) as session:
            outcome = await run_agent(llm, session, "100 free lunches with the CA top-up?")
        assert llm.calls == 2
        assert len(outcome["tool_calls"]) == 1
        assert outcome["tool_calls"][0]["tool"] == "calculate_meal_reimbursement"
        assert "$560.15" in outcome["answer"]

    anyio.run(go)
