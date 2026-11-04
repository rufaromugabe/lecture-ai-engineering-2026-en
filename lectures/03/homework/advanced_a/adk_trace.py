"""Run the ADK glossary_agent on the Basic question set with a fresh session per question,
and print the function calls (like --trace) so it can be compared with the Pydantic AI traces.

    PYTHONPATH=. uv run --with google-adk python lectures/03/homework/advanced_a/adk_trace.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "basic"))
from run_variants import QUESTIONS  # noqa: E402  same fixed questions as the Basic homework

from adk_agent.glossary_agent.agent import root_agent  # noqa: E402


async def ask(runner, question):
    session = await runner.session_service.create_session(app_name=runner.app_name, user_id="student")
    calls, answer, llm_responses = [], "", 0
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=question)])):
        if event.content and event.content.role == "model":  # one per LLM response
            llm_responses += 1
        for fc in event.get_function_calls():
            calls.append((fc.name, dict(fc.args or {})))
        for fr in event.get_function_responses():
            print(f"  [tool return] {fr.name} -> {str(fr.response)[:100]}…")
        if event.is_final_response() and event.content and event.content.parts:
            answer = "".join(p.text or "" for p in event.content.parts)
    return calls, answer, llm_responses


async def main(runs: int = 2):
    runner = InMemoryRunner(agent=root_agent, app_name="glossary_agent")
    out = []
    for qname, q in QUESTIONS.items():
        for run in range(1, runs + 1):
            for attempt in range(5):
                try:
                    calls, answer, n = await ask(runner, q)
                    break
                except Exception as e:  # 429/503 from the API surface wrapped in ADK errors
                    print(f"  [retry {attempt + 1}] {type(e).__name__}: {str(e)[:80]}")
                    time.sleep(20 * (attempt + 1))
            print(f"=== {qname} run{run}: {q}")
            for name, args in calls:
                print(f"[tool call]   {name}({args})")
            print(f"[LLM responses] {n}")
            print(answer.strip() + "\n")
            out.append({"question": qname, "run": run, "calls": calls, "answer": answer})
            time.sleep(4)
    (Path(__file__).parent / "adk_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
