"""Lecture 06 glossary and lecture summaries MCP server.

    uv run python -m app.mcp_agent --list-tools
    uv run python -m app.mcp_server --http

The first command lists tools without an API key. The second serves Streamable
HTTP at http://127.0.0.1:8000/mcp.

By default the server waits for input on stdio. MCP clients such as
app.mcp_agent launch it as a subprocess. If run directly, it will wait for input.
The functions registered in Lecture 03 are available through the same protocol
to the learning agent and to other MCP clients.
"""

import argparse
import json
import random
import re

from mcp.server.mcpserver import MCPServer

from app import tools

# Server name and description, shown to clients (distinct from the "glossary" key in the configuration file)
server = MCPServer(
    "aie2026-glossary",
    instructions="Provides the glossary and session key points for AIE2026 (AI Engineering Pilot Course).",
)

# Expose the same function as in Lecture 03 as an MCP tool. Its docstring and type hints become the description
server.tool()(tools.search_glossary)

# TODO(Basic homework): expose get_lecture_summary as well
server.tool()(tools.get_lecture_summary)

MAX_QUIZ_QUESTIONS = 5
CHOICES_PER_QUESTION = 4


def _mask(definition: str, term: str) -> str:
    """Hide the term (and its short form before any bracket) so the definition does not give away the answer."""
    for name in {term, term.split(" (")[0]}:
        definition = re.sub(rf"\b{re.escape(name)}\b", "____", definition, flags=re.IGNORECASE)
    return definition


@server.tool()
def make_quiz(lecture: int, num_questions: int = 3) -> str:
    """Make multiple-choice review questions for one lecture from the course glossary, with an answer key.

    Use when the learner asks for a quiz, review questions, or practice on a lecture (for example, "Quiz me on Lecture 02").
    lecture is the lecture number as an integer starting at 1. num_questions is 1 to 5 (default 3).
    Show the questions and choices first. Reveal the answers only after the learner replies.
    """
    by_lecture: dict[int, list[dict]] = {}
    for entry in tools.load_glossary():
        by_lecture.setdefault(entry["lecture"], []).append(entry)
    available = ", ".join(f"{n:02d}" for n in sorted(by_lecture))

    if lecture not in by_lecture:
        return (
            f"No quiz for Lecture {lecture}: the glossary has no terms for it. "
            f"Lectures with quiz terms: {available}. Ask the learner to pick one of these."
        )
    if not 1 <= num_questions <= MAX_QUIZ_QUESTIONS:
        return (
            f"num_questions must be between 1 and {MAX_QUIZ_QUESTIONS} (got {num_questions}). "
            f"Call make_quiz again with a value in that range."
        )

    terms = by_lecture[lecture]
    rng = random.Random()
    questions = []
    for entry in rng.sample(terms, min(num_questions, len(terms))):
        other_terms = [t["term"] for t in terms if t is not entry]
        distractors = rng.sample(other_terms, min(CHOICES_PER_QUESTION - 1, len(other_terms)))
        choices = distractors + [entry["term"]]
        rng.shuffle(choices)
        questions.append(
            {
                "question": f"Which Lecture {lecture:02d} term matches this definition? {_mask(entry['definition'], entry['term'])}",
                "choices": choices,
                "answer": entry["term"],
            }
        )
    return json.dumps({"lecture": lecture, "questions": questions}, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Glossary MCP server")
    parser.add_argument("--http", action="store_true", help="Start with Streamable HTTP (default: stdio)")
    args = parser.parse_args()
    if args.http:
        print("Starting the MCP server at http://127.0.0.1:8000/mcp (Ctrl+C to stop)")
        server.run(transport="streamable-http")
    else:
        # With stdio, standard output carries protocol messages, so do not print to it
        server.run()


if __name__ == "__main__":
    main()
