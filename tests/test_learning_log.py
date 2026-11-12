"""Homework (Implementation): save_learning_log and the approval flow (no LLM, no API key)."""

import json

import pytest
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, run_with_approvals


@pytest.fixture(autouse=True)
def tmp_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path / "learning_log")
    return tmp_path / "learning_log"


def test_save_creates_file_then_appends(tmp_log_dir):
    assert tools.save_learning_log("LoRA vs QLoRA", "first note").startswith("Saved learning_log/")
    assert tools.save_learning_log("LoRA vs QLoRA", "second note").startswith("Appended to")
    files = list(tmp_log_dir.iterdir())
    assert len(files) == 1 and files[0].name.endswith("_lora-vs-qlora.md")
    text = files[0].read_text(encoding="utf-8")
    assert "first note" in text and "second note" in text  # appended, not overwritten


@pytest.mark.parametrize("title", ["../../etc/passwd", "/abs/path", "a\\b:c*?", "..", "日本語のみ"])
def test_filename_stays_inside_log_dir(tmp_log_dir, title):
    tools.save_learning_log(title, "x")
    files = list(tmp_log_dir.iterdir())
    assert len(files) == 1 and files[0].parent == tmp_log_dir
    assert all(c.isalnum() or c in "-_." for c in files[0].name)


def test_rejects_empty_and_too_long(tmp_log_dir):
    assert "Nothing was saved" in tools.save_learning_log("  ", "x")
    assert "Nothing was saved" in tools.save_learning_log("t", "")
    assert "Nothing was saved" in tools.save_learning_log("t", "x" * (tools.MAX_LOG_CHARS + 1))
    assert not tmp_log_dir.exists() or not any(tmp_log_dir.iterdir())


def test_tool_pauses_for_approval():
    with agent.override(model=TestModel(call_tools=["save_learning_log"])):
        result = agent.run_sync("Save what I learned")
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]


@pytest.mark.parametrize("approve", [True, False])
def test_approve_and_deny_paths(tmp_log_dir, approve):
    model = TestModel(call_tools=["save_learning_log"])
    result = run_with_approvals(agent, "Save what I learned", model, decide=lambda call: approve)
    assert isinstance(result.output, str)
    ret = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]
    assert len(ret) == 1
    written = tmp_log_dir.exists() and any(tmp_log_dir.iterdir())
    assert written is approve
    if not approve:
        assert "declined" in str(ret[0].content)


def test_make_quiz_handles_missing_lecture():
    assert "No glossary terms" in tools.make_quiz(0)
    quiz = json.loads(tools.make_quiz(2))
    assert quiz["question"] and quiz["answer"]
