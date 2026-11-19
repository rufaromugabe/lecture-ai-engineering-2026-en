"""Run one question once under one retrieval condition; save the answer, pages returned, and the --trace text.

Same agent, INSTRUCTIONS, model and data as `python -m app.agent`; only the condition changes.
    uv run python lectures/05/experiments/harness.py CONDITION K DB REP QID QUESTIONS.json OUTDIR
CONDITION: vector | neighbors | hub | graph (stock --graph mode)
K:  RAG_TOP_K for vector / neighbors (hub and graph use their own settings in config.py)
DB: ja = bundled index (Japanese-text vectors) | en = experimental index, English text re-embedded
"""
import contextlib
import io
import json
import sys
import time
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from pydantic_ai.messages import ToolCallPart, ToolReturnPart  # noqa: E402

import app.retrieval as retrieval  # noqa: E402
from app import tools  # noqa: E402
from app.agent import GRAPH_INSTRUCTIONS, agent, build_model, print_trace  # noqa: E402
from app.config import MODEL  # noqa: E402

DBS = {"ja": ROOT / "data/rag_data/index.sqlite3", "en": ROOT / ".cache/rag/en.sqlite3"}


def pages_in(content: str) -> list[dict]:
    data = json.loads(content)
    items = data.get("results") or (data.get("seeds", []) + data.get("expanded", []))
    return [{"page_id": p["page_id"],
             "role": p.get("role") or ("seed" if p.get("hops") == 0 else "expanded" if "hops" in p else "hit")}
            for p in items]


def main() -> None:
    condition, k, db, rep, qid, qfile, outdir = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6], Path(sys.argv[7])
    question = {q["id"]: q for q in json.loads(Path(qfile).read_text(encoding="utf-8"))}[qid]["q"]
    retrieval.RAG_TOP_K = k           # same effect as editing RAG_TOP_K in app/config.py
    retrieval.RAG_DB = DBS[db]        # same effect as AIE_RAG_DB
    retrieval.CURRENT_QUESTION.set(question)
    mode = contextlib.nullcontext()
    if condition == "graph":
        mode = agent.override(instructions=GRAPH_INSTRUCTIONS, tools=[tools.search_graph])
    else:
        retrieval.RETRIEVER = condition
    for attempt in range(4):
        try:
            started = perf_counter()
            with mode:
                result = agent.run_sync(question, model=build_model())
            break
        except Exception as e:  # rate limit / busy: wait and retry, never log request details
            if attempt == 3:
                raise
            print(f"retry after {type(e).__name__}", file=sys.stderr)
            time.sleep(30 * (attempt + 1))
    elapsed = perf_counter() - started
    queries, returned = [], []
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                args = part.args if isinstance(part.args, dict) else json.loads(part.args or "{}")
                queries.append(args.get("query"))
            elif isinstance(part, ToolReturnPart):
                returned.append(pages_in(part.content))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        print(f"[model] {MODEL}  [condition] {condition}  [RAG_TOP_K] {k}  [index] {db}  [question] {question}")
        print(result.output)
        print_trace(result, elapsed)
    usage = result.usage
    record = {"condition": condition, "k": k, "db": db, "rep": rep, "qid": qid, "model": MODEL, "answer": result.output,
              "queries": queries, "returned": returned, "time": round(elapsed, 2),
              "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "requests": usage.requests,
              "cache_read_tokens": getattr(usage, "cache_read_tokens", None),
              "cost": float(usage.cost) if usage.cost is not None else None}
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / f"{condition}_k{k}_{db}_{qid}_r{rep}"
    base.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    base.with_suffix(".trace.txt").write_text(buffer.getvalue(), encoding="utf-8")
    print(condition, k, db, qid, rep, record["time"], record["input_tokens"], len(queries), record["cost"])


if __name__ == "__main__":
    main()
