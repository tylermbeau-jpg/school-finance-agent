"""CLI behavior that must not require a paid API call."""

from sfagent.cli import main


def test_ask_without_key_fails_cleanly(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["ask", "Is 01-0000-0-1110-1000-1100 valid?"]) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_eval_without_key_fails_cleanly(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["eval"]) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
