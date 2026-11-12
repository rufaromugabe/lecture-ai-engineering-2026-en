"""Lecture 03: a learning support agent built with Pydantic AI.

Usage:
    uv run python -m app.agent "What is a lecNN-start tag in the AIE2026 course?"
    uv run python -m app.agent --trace "What is the difference between LoRA and QLoRA?"   # Show tool calls
    uv run python -m app.agent --mcp --trace "What is LoRA?"    # Lecture 05: receive tools from MCP servers
    uv run python -m app.agent --mcp --list-tools               # Lecture 05: list tools visible to the model (no API key needed)

Agent = model + loop + tools.
The model calls functions in tools.py as "tools" and uses their results to compose answers.
In Lecture 05, it receives the same tools through an MCP server (app/mcp_server.py).
"""

import argparse
import inspect
import json
from pathlib import Path

from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, ToolDenied
from pydantic_ai.exceptions import ModelHTTPError
from fastmcp import Client
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider

from app import tools
from app.config import MODEL, api_error_message, get_api_key

INSTRUCTIONS = """\
You are a learning support agent for the AI Engineering Pilot Course (AIE2026).
- Always check the glossary with search_glossary before answering about terms or course-specific information.
- Use get_lecture_summary when asked about the content of a session.
- If something is absent from the glossary, say "It is not in the glossary" instead of making assertions based on guesses.
- End your answer by indicating the relevant session (Lecture NN).
- Guide learners with hints on how to think, rather than writing homework answers for them.
"""

# Pass the model at runtime (so tests can substitute TestModel without calling an API)
# output_type includes DeferredToolRequests: a run pauses and returns it when an approval-required tool is called
agent = Agent(instructions=INSTRUCTIONS, output_type=[str, DeferredToolRequests])
agent.tool_plain(tools.search_glossary)
agent.tool_plain(tools.get_lecture_summary)

# Lecture 03 exercise: review-question tool
agent.tool_plain(tools.make_quiz)

# Homework (Implementation): writing a file is hard to undo, so it needs the user's approval first
agent.tool_plain(tools.save_learning_log, requires_approval=True)

# Lecture 05: MCP server configuration file. Uses the same "mcpServers" format as Claude Desktop and Cursor
MCP_CONFIG = Path(__file__).resolve().parent / "mcp_servers.json"


def load_mcp_servers(config_path: Path = MCP_CONFIG) -> list[MCPToolset]:
    """Read the configuration file (mcpServers format) and create a connection (MCPToolset) per server.

    - With "command", use stdio: start the server as a subprocess
    - With "url", use Streamable HTTP: connect to a running server
    Prefix tool names with "server_name_" (for example, glossary_search_glossary) to
    distinguish tools with identical names on different servers.

    Pydantic AI also has load_mcp_toolsets() for the same purpose. We assemble connections
    ourselves here because automatic connection-mode detection ("auto") emits many warnings
    for servers built with older SDKs (such as fetch). Fixing the mode to "legacy" connects
    quietly to both older and newer servers.
    """
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))["mcpServers"]
    toolsets = []
    for name, spec in config.items():
        if "url" in spec:
            transport = spec["url"]
        else:
            transport = StdioTransport(spec["command"], spec.get("args", []), env=spec.get("env"))
        toolsets.append(MCPToolset(Client(transport, mode="legacy")).prefixed(name))
    return toolsets


def build_mcp_agent(config_path: Path = MCP_CONFIG) -> Agent:
    """Lecture 05: an agent using tools exposed by MCP servers instead of directly registered functions. INSTRUCTIONS stays the same."""
    return Agent(instructions=INSTRUCTIONS, toolsets=load_mcp_servers(config_path))


def build_model() -> GoogleModel:
    return GoogleModel(MODEL, provider=GoogleProvider(api_key=get_api_key()))


def print_tools(target: Agent) -> None:
    """Display tools visible to the model (names, descriptions, arguments). Do not call an LLM.

    Pass the tools to TestModel (the fake model used for testing) and read them back.
    MCP server tools and Lecture 03's function tools look the same to the model.
    """
    model = TestModel(call_tools=[])
    target.run_sync("Tool list", model=model)
    tools_seen = model.last_model_request_parameters.function_tools
    print(f"Tools visible to the model: {len(tools_seen)}")
    for tool in tools_seen:
        print(f"\n[{tool.name}]")
        print("  " + inspect.cleandoc(tool.description or "").replace("\n", "\n  "))
        params = tool.parameters_json_schema.get("properties", {})
        print(f"  Arguments: {json.dumps(params, ensure_ascii=False)}")


def print_trace(result) -> None:
    """Display which tools were called with which arguments and what they returned."""
    print("\n--- trace ---")
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                print(f"[tool call]   {part.tool_name}({part.args})")
            elif isinstance(part, ToolReturnPart):
                print(f"[tool return] {part.tool_name} -> {str(part.content)[:120]}…")
    print(f"[usage] {result.usage}")
    for i, usage in enumerate(getattr(result, "paused_usage", []), 1):
        print(f"[usage before approval pause {i}] {usage}")


def ask_approvals(requests: DeferredToolRequests, decide=None) -> DeferredToolResults:
    """Ask the user (y/n) about each tool call waiting for approval and build DeferredToolResults.

    decide(call) -> bool can replace the interactive prompt (used in tests).
    """
    results = DeferredToolResults()
    for call in requests.approvals:
        args = call.args_as_dict()
        print(f"\n[approval needed] {call.tool_name}")
        for key, value in args.items():
            print(f"  {key}: {value}")
        if decide is not None:
            ok = decide(call)
        else:
            try:
                ok = input("Save this? [y/N] ").strip().casefold() in ("y", "yes")
            except EOFError:  # no terminal input: deny by default (the safe choice)
                ok = False
        print(f"[approval] {'approved' if ok else 'denied'}")
        results.approvals[call.tool_call_id] = True if ok else ToolDenied(
            "The user declined to save this learning log. Nothing was written; do not retry unless asked."
        )
    return results


def run_with_approvals(target: Agent, question: str, model, decide=None, max_rounds: int = 5):
    """Run the agent; while it pauses for approval, ask the user and continue the same conversation."""
    result = target.run_sync(question, model=model)
    paused_usage = []  # usage of runs that ended in an approval pause (result.usage covers only the last run)
    for _ in range(max_rounds):
        if not isinstance(result.output, DeferredToolRequests):
            result.paused_usage = paused_usage
            return result
        paused_usage.append(result.usage)
        results = ask_approvals(result.output, decide)
        result = target.run_sync(message_history=result.all_messages(), deferred_tool_results=results, model=model)
    raise SystemExit("Too many approval rounds; stopping.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the learning support agent a question")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--trace", action="store_true", help="Show tool calls")
    parser.add_argument("--mcp", action="store_true", help="Lecture 05: receive tools from MCP servers (app/mcp_servers.json)")
    parser.add_argument("--list-tools", action="store_true", help="List tools visible to the model and exit (no API key needed)")
    args = parser.parse_args()

    target = build_mcp_agent() if args.mcp else agent
    if args.list_tools:
        print_tools(target)
        return
    if not args.question:
        parser.error("Please provide a question")

    print(f"[model] {MODEL}")
    if args.mcp:
        print("[tools] MCP servers (app/mcp_servers.json)")
    try:
        result = run_with_approvals(target, args.question, build_model())
    except ModelHTTPError as e:
        print(api_error_message(e.status_code, str(e.body)[:200]))
        raise SystemExit(1)
    print(result.output)
    if args.trace:
        print_trace(result)


if __name__ == "__main__":
    main()
