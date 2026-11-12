"""Aggregate the saved judge runs (no API calls). Run from repo root:
    uv run python lectures/04/analysis/summarize_runs.py
Writes lectures/04/analysis/runs_summary.csv and prints a table per experiment.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L4 = ROOT / "lectures" / "04"
CRIT = ["grounding", "scope", "hint", "clarity", "lecture_mark"]

GROUPS = {
    "ex_before (original rubric, flash-lite)": "basic/ex_before_r*.json",
    "ex_after (my Grounding policy, flash-lite)": "basic/ex_after_r*.json",
    "basic: model = gemini-3.5-flash": "basic/model_flash_r*.json",
    "extra: gemini-3.5-flash on the ORIGINAL rubric": "basic/extra_flash_original_rubric_r*.json",
    "basic: wording, Grounding = facts only": "basic/wording_grounding_r*.json",
    "basic: wording, Clarity <= ~100 words": "basic/wording_clarity_r*.json",
    "basic: order, verdict before reason": "basic/order_verdict_first_r*.json",
    "impl: my cases, flash-lite": "impl/my_judge_lite_r*.json",
    "impl: my cases, gemini-3.5-flash": "impl/my_judge_flash_r*.json",
    "impl: my cases, flash-lite, Clarity <= ~100 words rubric": "impl/my_judge_lite_clarity_length_r*.json",
}


def row(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    s = d["summary"]
    out = {"file": str(path.relative_to(L4)), "model": d["model"]}
    llm_agree = llm_cmp = 0
    for k in CRIT:
        p = s["per_criterion"][k]
        out[k] = f"{p['agree']}/{p['compared']}"
        if k != "lecture_mark":
            llm_agree += p["agree"]
            llm_cmp += p["compared"]
    out["llm_cells"] = f"{llm_agree}/{llm_cmp}"
    out["overall"] = f"{s['overall']['agree']}/{s['overall']['compared']}"
    out["review"] = len(s["review"])
    out["missed"] = sum(m["kind"] == "Missed failure" for m in s["mismatches"])
    out["false_alarm"] = sum(m["kind"] == "False alarm" for m in s["mismatches"])
    out["mismatch_ids"] = " ".join(f"#{m['id']}{m['criterion'][:2]}" for m in s["mismatches"])
    out["review_ids"] = " ".join(f"#{r['id']}{r['criterion'][:2]}" for r in s["review"])
    return out


rows = []
for group, pattern in GROUPS.items():
    for p in sorted(L4.glob(pattern)):
        r = row(p)
        r["group"] = group
        rows.append(r)

fields = ["group", "file", "model", *CRIT, "llm_cells", "overall", "review", "missed", "false_alarm", "mismatch_ids", "review_ids"]
with open(L4 / "analysis" / "runs_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

for r in rows:
    print(f"{r['group'][:44]:44} {r['file'][-26:]:26} G{r['grounding']:>6} S{r['scope']:>6} H{r['hint']:>6} C{r['clarity']:>6} "
          f"llm {r['llm_cells']:>6} ovr {r['overall']:>5} rev {r['review']} miss {r['missed']} fa {r['false_alarm']} | {r['mismatch_ids']} | {r['review_ids']}")
