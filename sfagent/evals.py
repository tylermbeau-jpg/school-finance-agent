"""Eval harness: graded questions, a mechanical scorer, and a runner.

Check types:
- contains: every listed substring appears in the answer (case-insensitive)
- number_close: some number in the answer is within tolerance of the target
- tool_used: the agent called the named tool at least once

The scorer is deliberately mechanical. If a check needs judgment to grade, it
belongs in a different harness.
"""

from __future__ import annotations

import json
import pathlib
import re

_NUMBER = re.compile(r"-?\$?\d[\d,]*\.?\d*")


def load_questions(path: str | pathlib.Path) -> list[dict]:
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _numbers_in(text: str) -> list[float]:
    values = []
    for match in _NUMBER.findall(text):
        cleaned = match.replace("$", "").replace(",", "")
        try:
            values.append(float(cleaned))
        except ValueError:
            continue
    return values


def score_answer(checks: list[dict], answer: str, tool_calls: list[dict]) -> dict:
    """Grade one answer. Returns {passed, total, failures}."""
    failures = []
    for check in checks:
        kind = check["type"]
        if kind == "contains":
            missing = [s for s in check["values"] if s.lower() not in answer.lower()]
            if missing:
                failures.append(f"contains: missing {missing}")
        elif kind == "number_close":
            target, tol = float(check["value"]), float(check.get("tolerance", 0.01))
            if not any(abs(n - target) <= tol for n in _numbers_in(answer)):
                failures.append(f"number_close: {target} (+/- {tol}) not found")
        elif kind == "tool_used":
            used = {call["tool"] for call in tool_calls}
            if check["value"] not in used:
                failures.append(f"tool_used: {check['value']} not called (used: {sorted(used)})")
        else:
            failures.append(f"unknown check type: {kind}")
    return {"passed": len(checks) - len(failures), "total": len(checks), "failures": failures}


async def run_evals(client, session, questions: list[dict], *, model: str) -> dict:
    """Run every question through the agent and grade it. Live model required."""
    from .loop import run_agent

    results = []
    for row in questions:
        outcome = await run_agent(client, session, row["question"], model=model)
        grade = score_answer(row["checks"], outcome["answer"], outcome["tool_calls"])
        results.append({"id": row["id"], **grade})
    passed = sum(1 for r in results if r["passed"] == r["total"])
    return {"questions": len(results), "fully_passed": passed, "results": results}
