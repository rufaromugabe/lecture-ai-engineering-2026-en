"""Lecture 01: a script that asks a bare LLM a single question.

Usage:
    uv run python -m app.ask "What is LoRA?"
    uv run python -m app.ask --chat "What is LoRA?"   # follow-up questions with history
    uv run python -m app.ask            # Ask a course-specific question if none is supplied

A "bare" call with no tools or conversation history.
Check that, when asked about course-specific information, it either says "I don't know"
or gives a plausible general answer (which differs from the actual course).
(In Lecture 03, improve it by making an agent that can search the glossary.)
"""

import argparse
import time

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# A course-specific question. The correct answer is in homework-levels in data/glossary.json
DEFAULT_QUESTION = "What are the 3 homework levels in the AIE2026 course?"


def print_usage(response, elapsed: float) -> None:
    """Print token counts and response time for one model call."""
    usage = response.usage_metadata
    if usage is None:
        print("[tokens] usage metadata not available")
    else:
        print(
            f"[tokens] input={usage.prompt_token_count or 0} "
            f"output={usage.candidates_token_count or 0} "
            f"thinking={usage.thoughts_token_count or 0} "
            f"total={usage.total_token_count or 0}"
        )
    print(f"[time] {elapsed:.2f}s\n")


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    start = time.perf_counter()
    response = client.models.generate_content(model=MODEL, contents=question)
    print_usage(response, time.perf_counter() - start)
    return response.text


def chat(first_question: str) -> None:
    """Homework (Implementation): keep the conversation history for follow-up questions.

    The chat session stores every earlier turn and sends it with each new question.
    Type a follow-up at the prompt; an empty line, 'quit' or 'exit' ends the chat.
    """
    client = genai.Client(api_key=get_api_key())
    session = client.chats.create(model=MODEL)
    question = first_question
    while True:
        start = time.perf_counter()
        response = session.send_message(question)
        print_usage(response, time.perf_counter() - start)
        print(response.text)
        try:
            question = input("\nYou (empty line to quit): ").strip()
        except EOFError:
            break
        if not question or question.lower() in {"quit", "exit"}:
            break
        print(f"[question] {question}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a bare LLM a question")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--chat",
        action="store_true",
        help="keep asking follow-up questions in the same conversation",
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    print(f"[question] {args.question}\n")
    try:
        if args.chat:
            chat(args.question)
        else:
            print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
