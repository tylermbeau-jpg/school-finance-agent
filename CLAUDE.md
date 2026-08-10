# school-finance-agent

Claude agent over school-finance-mcp (live HTTP default, --stdio local), plus a graded eval suite (contains / number_close / tool_used). MIT licensed.

**This repo is PUBLIC** (github.com/tylermbeau-jpg/school-finance-agent, portfolio piece). Nothing non-public goes in it: no client or employer references, no district data. Eval questions use only what the public MCP tools can answer.

## Commands

- Setup: `python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"` (dev extra installs school-finance-mcp from GitHub for the stdio integration tests)
- Tests: `.venv/bin/python -m pytest -q` (offline: scorer + real-MCP integration with a stub LLM; keep them passing)
- Live: `sfagent ask "..."` / `sfagent eval` (need $ANTHROPIC_API_KEY)

## Design boundaries

- The system prompt requires tool grounding; do not weaken it. The grounding-refusal eval question guards it.
- The scorer stays mechanical. No LLM-graded checks in this harness.
- Keep the agent transport-agnostic: everything goes through bridge.open_mcp, never a direct import of school_finance_mcp internals.

## Working standards

- No em dashes or en dashes in anything: docs, code comments, commit messages.
- Never announce work as done with unflagged incomplete parts (the README's testing-scope note is this rule in print; keep it accurate).
- Verify before declaring ready: run the tests, run one ask against the live server if a key is available, check the README still matches.
