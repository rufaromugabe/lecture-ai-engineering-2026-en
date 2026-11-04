"""Homework (Basic): run the same questions against one-change-at-a-time variants.

Each variant changes exactly ONE place (a line of INSTRUCTIONS or one tool docstring)
relative to the baseline in app/agent.py / app/tools.py. Instead of editing the files by
hand between runs, the variant text is applied in memory, which is equivalent to editing
the file (Pydantic AI reads the instructions string and the docstring at registration time),
and the exact change is written at the top of every trace file.

Usage (repo root):
    PYTHONPATH=. PYDANTIC_AI_NO_BANNER=1 uv run python lectures/03/homework/basic/run_variants.py [--runs 2] [--only V1,V2]
"""

import argparse
import functools
import io
import json
import time
from contextlib import redirect_stdout
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ToolCallPart

from app import tools
from app.agent import INSTRUCTIONS, build_model, print_trace
from app.config import MODEL

OUT = Path(__file__).resolve().parent / "traces"

QUESTIONS = {
    "Q1": "What is the difference between LoRA and QLoRA?",
    "Q2": "How are PEFT, LoRA, rank and quantization related to each other?",  # several terms
    "Q3": "What is RLHF, and in which lecture is it covered?",  # absent from the glossary
    "Q4": "What will we learn in Lecture 03, and what is a harness?",  # summary + term
}

SEARCH_ONE = 'Put only one term to look up in query (for example, "LoRA").'
SEARCH_MANY = 'Put several terms to look up in query at once (for example, "LoRA QLoRA").'
L_ALWAYS = "- Always check the glossary with search_glossary before answering about terms or course-specific information.\n"
L_ABSENT = '- If something is absent from the glossary, say "It is not in the glossary" instead of making assertions based on guesses.\n'
SEARCH_WHEN = "Use before answering about AI engineering terms or words specific to this course (AIE2026).\n    "
L_END = "- End your answer by indicating the relevant session (Lecture NN).\n"

# name -> (description, instructions, search_glossary docstring)
VARIANTS = {
    "V0": ("baseline (files as in the exercise)", INSTRUCTIONS, tools.search_glossary.__doc__),
    "V1": ("INSTRUCTIONS: delete the 'Always check the glossary with search_glossary' line",
           INSTRUCTIONS.replace(L_ALWAYS, ""), tools.search_glossary.__doc__),
    "V2": ("search_glossary docstring: 'Put only one term' -> 'Put several terms ... at once'",
           INSTRUCTIONS, tools.search_glossary.__doc__.replace(SEARCH_ONE, SEARCH_MANY)),
    "V3": ("INSTRUCTIONS: 'End your answer by indicating the relevant session' -> 'End your answer with one review question'",
           INSTRUCTIONS.replace(L_END, "- End your answer with one short review question for the learner.\n"),
           tools.search_glossary.__doc__),
    "V4": ("INSTRUCTIONS: delete the 'If something is absent ... It is not in the glossary' line",
           INSTRUCTIONS.replace(L_ABSENT, ""), tools.search_glossary.__doc__),
    # Follow-up after V1 showed no change: is the docstring's own "Use before answering" sentence
    # what keeps the model searching? V5 = one change in the docstring; V6 = V1 + V5 combined (2 changes, labelled).
    "V5": ("search_glossary docstring: delete the 'Use before answering about ... terms' sentence",
           INSTRUCTIONS, tools.search_glossary.__doc__.replace(SEARCH_WHEN, "")),
    "V6": ("COMBINED (2 changes): V1 + V5, no 'search first' rule anywhere",
           INSTRUCTIONS.replace(L_ALWAYS, ""), tools.search_glossary.__doc__.replace(SEARCH_WHEN, "")),
}


def build_agent(instructions: str, search_doc: str) -> Agent:
    @functools.wraps(tools.search_glossary)
    def search_glossary(query: str) -> str:
        return tools.search_glossary(query)

    search_glossary.__doc__ = search_doc
    a = Agent(instructions=instructions)
    a.tool_plain(search_glossary)
    a.tool_plain(tools.get_lecture_summary)
    a.tool_plain(tools.make_quiz)
    return a


def run_once(a: Agent, question: str):
    for attempt in range(6):
        try:
            return a.run_sync(question, model=build_model())
        except ModelHTTPError as e:
            if e.status_code in (429, 500, 503):
                wait = 15 * (attempt + 1)
                print(f"  HTTP {e.status_code}, retry in {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("gave up after retries")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--only", default="")
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, args.only.split(",")))
    summary_path = OUT.parent / "summary.jsonl"
    for vname, (desc, instr, doc) in VARIANTS.items():
        if only and vname not in only:
            continue
        a = build_agent(instr, doc)
        for qname, q in QUESTIONS.items():
            for run in range(1, args.runs + 1):
                result = run_once(a, q)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    print_trace(result)
                calls = [(p.tool_name, p.args_as_dict()) for m in result.all_messages()
                         for p in m.parts if isinstance(p, ToolCallPart)]
                head = (f"# variant {vname}: {desc}\n# model {MODEL}\n# question {qname}: {q}\n"
                        f"# run {run}\n\n[answer]\n")
                (OUT / f"{vname}_{qname}_run{run}.txt").write_text(
                    head + str(result.output) + "\n" + buf.getvalue(), encoding="utf-8")
                rec = {"variant": vname, "question": qname, "run": run, "calls": calls,
                       "requests": result.usage.requests, "input_tokens": result.usage.input_tokens,
                       "output_tokens": result.usage.output_tokens, "answer": str(result.output)}
                with summary_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(vname, qname, run, [f"{n}({a})" for n, a in calls], f"req={result.usage.requests}")
                time.sleep(4)  # stay under free-tier requests-per-minute


if __name__ == "__main__":
    main()
