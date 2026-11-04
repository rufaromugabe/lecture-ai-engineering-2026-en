"""Build the comparison table from summary.jsonl (written by run_variants.py)."""
import json
import re
from pathlib import Path

here = Path(__file__).parent
rows = [json.loads(l) for l in (here / "summary.jsonl").read_text(encoding="utf-8").splitlines()]
short = {"search_glossary": "S", "get_lecture_summary": "L", "make_quiz": "Q"}


def seq(calls):
    return " → ".join(f"{short[n]}({next(iter(a.values()))})" for n, a in calls) or "(none)"


out = ["| Var | Q | run | tool calls in order (S=search_glossary, L=get_lecture_summary) | #calls | requests | input tok | 'not in glossary' | ends with Lecture NN | ends with '?' |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    a = r["answer"].strip()
    out.append(f"| {r['variant']} | {r['question']} | {r['run']} | {seq(r['calls'])} | {len(r['calls'])} | {r['requests']} | "
               f"{r['input_tokens']} | {'yes' if 'not in the glossary' in a.lower() or 'not in the course glossary' in a.lower() else 'no'} | "
               f"{'yes' if re.search(r'Lecture \d\d', a[-60:]) else 'no'} | {'yes' if a.endswith('?') else 'no'} |")
(here / "table_all_runs.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
