"""The eval scorer must be mechanical and unforgiving."""

from sfagent.evals import load_questions, score_answer

EVALS = "evals/questions.jsonl"


def test_contains_pass_and_fail():
    checks = [{"type": "contains", "values": ["Cafeteria", "food"]}]
    good = score_answer(checks, "Fund 13 is the Cafeteria fund, function 3700 is Food Services.", [])
    assert good["passed"] == 1 and not good["failures"]
    bad = score_answer(checks, "Fund 13 is a special revenue fund.", [])
    assert bad["passed"] == 0 and "missing" in bad["failures"][0]


def test_number_close_handles_currency_formatting():
    checks = [{"type": "number_close", "value": 3921.05, "tolerance": 1.0}]
    assert score_answer(checks, "The total comes to $3,921.05 for the month.", [])["passed"] == 1
    assert score_answer(checks, "The total comes to $4,100.", [])["passed"] == 0


def test_tool_used():
    checks = [{"type": "tool_used", "value": "validate_sacs_string"}]
    calls = [{"tool": "validate_sacs_string", "input": {}, "output": "{}"}]
    assert score_answer(checks, "answer", calls)["passed"] == 1
    assert score_answer(checks, "answer", [])["passed"] == 0


def test_unknown_check_type_fails_loudly():
    result = score_answer([{"type": "vibes"}], "answer", [])
    assert result["passed"] == 0
    assert "unknown check type" in result["failures"][0]


def test_questions_file_is_well_formed():
    rows = load_questions(EVALS)
    assert len(rows) >= 12
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)), "duplicate question ids"
    for row in rows:
        assert row["question"].strip()
        assert row["checks"], f"{row['id']} has no checks"
        for check in row["checks"]:
            assert check["type"] in {"contains", "number_close", "tool_used"}, row["id"]


def test_number_close_uses_default_tolerance():
    checks = [{"type": "number_close", "value": 4.60}]
    assert score_answer(checks, "That lunch reimburses $4.60 federally.", [])["passed"] == 1
    assert score_answer(checks, "That lunch reimburses $4.75 federally.", [])["passed"] == 0
