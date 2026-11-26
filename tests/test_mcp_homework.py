"""Lecture 06 homework tests: get_lecture_summary and make_quiz on the glossary MCP server,
and what the client receives when a tool returns a message versus raises (no LLM or API key used)."""

import asyncio
import json
import logging
import re

import pytest
from fastmcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.mcp_server import MAX_QUIZ_QUESTIONS, server

QUIZ_LECTURES = sorted({t["lecture"] for t in tools.load_glossary()})


def call(name: str, arguments: dict):
    """Call a tool on the real server object through an in-memory MCP client."""

    async def run():
        async with Client(server) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)

    return asyncio.run(run())


def text(result) -> str:
    return result.content[0].text


def test_server_lists_all_three_tools():
    async def names():
        async with Client(server) as client:
            return {t.name for t in await client.list_tools()}

    assert {"search_glossary", "get_lecture_summary", "make_quiz"} <= asyncio.run(names())


def test_lecture_summary_through_mcp():
    result = call("get_lecture_summary", {"lecture": 2})
    assert not result.is_error
    assert text(result).startswith("# Lecture 02")


@pytest.mark.parametrize("lecture", QUIZ_LECTURES)
def test_quiz_is_grounded_in_that_lectures_glossary(lecture):
    result = call("make_quiz", {"lecture": lecture, "num_questions": 3})
    assert not result.is_error
    quiz = json.loads(text(result))
    lecture_terms = {t["term"] for t in tools.load_glossary() if t["lecture"] == lecture}
    assert quiz["lecture"] == lecture and len(quiz["questions"]) == 3
    assert len({q["answer"] for q in quiz["questions"]}) == 3  # no repeated question
    for q in quiz["questions"]:
        assert q["answer"] in q["choices"] and len(set(q["choices"])) == len(q["choices"]) == 4
        assert set(q["choices"]) <= lecture_terms
        short = re.escape(q["answer"].split(" (")[0])
        assert not re.search(rf"\b{short}\b", q["question"], re.IGNORECASE)  # the definition does not give the answer away


@pytest.mark.parametrize("lecture", [0, 5, 99, -1])
def test_unknown_lecture_returns_a_message_not_an_error(lecture):
    result = call("make_quiz", {"lecture": lecture})
    assert not result.is_error
    assert f"No quiz for Lecture {lecture}" in text(result)
    assert "01, 02, 03, 04, 06" in text(result)


@pytest.mark.parametrize("num_questions", [0, MAX_QUIZ_QUESTIONS + 1])
def test_num_questions_out_of_range_returns_a_message(num_questions):
    result = call("make_quiz", {"lecture": 2, "num_questions": num_questions})
    assert not result.is_error
    assert f"between 1 and {MAX_QUIZ_QUESTIONS} (got {num_questions})" in text(result)


def test_wrong_argument_type_is_rejected_by_the_schema():
    result = call("make_quiz", {"lecture": "two"})
    assert result.is_error


# --- return vs raise, as the agent (Pydantic AI MCP client) sees it ---

probe = MCPServer("probe")


@probe.tool()
def returns(lecture: int) -> str:
    """Return a message for an unknown lecture."""
    return f"No quiz for Lecture {lecture}."


@probe.tool()
def raises_value_error(lecture: int) -> str:
    """Raise ValueError for an unknown lecture."""
    raise ValueError(f"No quiz for Lecture {lecture}.")


@probe.tool()
def raises_tool_error(lecture: int) -> str:
    """Raise ToolError for an unknown lecture."""
    raise ToolError(f"No quiz for Lecture {lecture}.")


def what_the_model_sees(tool: str):
    agent = Agent(toolsets=[MCPToolset(Client(probe)).prefixed("p")])
    logging.disable(logging.CRITICAL)  # the server logs the traceback; keep test output clean
    try:
        with capture_run_messages() as messages:
            try:
                agent.run_sync("quiz", model=TestModel(call_tools=[f"p_{tool}"]))
            except UnexpectedModelBehavior:
                pass  # TestModel repeats the same failing call until retries run out
    finally:
        logging.disable(logging.NOTSET)
    return [p for m in messages for p in m.parts if isinstance(p, (ToolReturnPart, RetryPromptPart))]


def test_return_reaches_the_model_as_a_normal_result():
    parts = what_the_model_sees("returns")
    assert isinstance(parts[0], ToolReturnPart)
    assert parts[0].content == "No quiz for Lecture 0."


def test_value_error_message_is_hidden_from_the_model():
    parts = what_the_model_sees("raises_value_error")
    assert isinstance(parts[0], RetryPromptPart)
    assert parts[0].content == "Error executing tool raises_value_error"  # the reason never arrives


def test_tool_error_message_reaches_the_model_as_a_retry():
    parts = what_the_model_sees("raises_tool_error")
    assert isinstance(parts[0], RetryPromptPart)
    assert parts[0].content == "Error executing tool raises_tool_error: No quiz for Lecture 0."
