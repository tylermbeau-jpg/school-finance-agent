"""CLI: ask the agent a question, or run the eval suite."""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

from . import evals as evals_mod
from .bridge import DEFAULT_URL, open_mcp
from .loop import DEFAULT_MODEL, make_client, run_agent

EVALS_PATH = pathlib.Path(__file__).resolve().parent.parent / "evals" / "questions.jsonl"


def _add_transport_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default=DEFAULT_URL, help=f"MCP server URL (default {DEFAULT_URL})")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="spawn a local school-finance-mcp over stdio instead of connecting to --url",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)


async def _ask(args) -> int:
    client = make_client()
    async with open_mcp(args.url, stdio=args.stdio) as session:
        outcome = await run_agent(client, session, args.question, model=args.model)
    for call in outcome["tool_calls"]:
        print(f"[tool] {call['tool']}({json.dumps(call['input'])})", file=sys.stderr)
    print(outcome["answer"])
    return 0


async def _eval(args) -> int:
    client = make_client()
    questions = evals_mod.load_questions(args.questions)
    async with open_mcp(args.url, stdio=args.stdio) as session:
        report = await evals_mod.run_evals(client, session, questions, model=args.model)
    for row in report["results"]:
        status = "PASS" if row["passed"] == row["total"] else "FAIL"
        print(f"{status} {row['id']} ({row['passed']}/{row['total']})")
        for failure in row["failures"]:
            print(f"     {failure}")
    print(f"\n{report['fully_passed']}/{report['questions']} questions fully passed")
    return 0 if report["fully_passed"] == report["questions"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sfagent",
        description="School-finance agent over the school-finance-mcp server.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ask", help="ask one question")
    p.add_argument("question")
    _add_transport_args(p)
    p.set_defaults(coro=_ask)

    p = sub.add_parser("eval", help="run the graded eval suite (live model required)")
    p.add_argument("--questions", default=str(EVALS_PATH))
    _add_transport_args(p)
    p.set_defaults(coro=_eval)

    args = parser.parse_args(argv)
    try:
        return asyncio.run(args.coro(args))
    except RuntimeError as exc:
        print(f"sfagent: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
