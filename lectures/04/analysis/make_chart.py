"""Draw lectures/04/summary_chart.png from the saved runs (no API calls).
    uv run --with matplotlib python lectures/04/analysis/make_chart.py
"""
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

L4 = Path(__file__).resolve().parents[1]
LLM = ["grounding", "scope", "hint", "clarity"]


def load(pattern):
    return [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(L4 / pattern)))]


def disagree(run):  # LLM-judged cells that disagree with my labels (unsure excluded)
    return sum(p["compared"] - p["agree"] for k, p in run["summary"]["per_criterion"].items() if k in LLM)


def review(run):
    return len(run["summary"]["review"])


conds = [
    ("Original rubric\n(flash-lite)", "basic/ex_before_r*.json"),
    ("+ my Grounding\npolicy (Exercise)", "basic/ex_after_r*.json"),
    ("Model:\ngemini-3.5-flash", "basic/model_flash_r*.json"),
    ("Wording: Grounding\n= facts only", "basic/wording_grounding_r*.json"),
    ("Wording: Clarity\n<= ~100 words", "basic/wording_clarity_r*.json"),
    ("Order: verdict\nbefore reason", "basic/order_verdict_first_r*.json"),
]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
x = range(len(conds))
for xi, (label, pat) in zip(x, conds):
    runs = load(pat)
    d = [disagree(r) for r in runs]
    rv = [review(r) for r in runs]
    ax1.bar(xi - 0.18, sum(d) / len(d), 0.36, color="#c0504d")
    ax1.bar(xi + 0.18, sum(rv) / len(rv), 0.36, color="#4f81bd")
    for v in d:
        ax1.plot(xi - 0.18, v, "k.", ms=7)
    for v in rv:
        ax1.plot(xi + 0.18, v, "k.", ms=7)
ax1.set_xticks(list(x))
ax1.set_xticklabels([c[0] for c in conds], fontsize=8)
ax1.set_ylabel("count per run (bar = mean of 3, dots = each run)")
ax1.set_title("Instructor's 10 cases: disagreements with my labels and needs-review items\n(40 LLM-judged cells per run; one change per condition)", fontsize=10)
ax1.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#c0504d"), plt.Rectangle((0, 0), 1, 1, color="#4f81bd")],
           labels=["disagreements", "needs review"], loc="upper right", fontsize=8)
ax1.set_ylim(0, 4)

for off, (label, pat, color) in zip((-0.2, 0.2), [("flash-lite", "impl/my_judge_lite_r*.json", "#9bbb59"), ("flash", "impl/my_judge_flash_r*.json", "#8064a2")]):
    runs = load(pat)
    for i, k in enumerate(LLM):
        vals = [r["summary"]["per_criterion"][k]["agree"] / max(r["summary"]["per_criterion"][k]["compared"], 1) for r in runs]
        ax2.bar(i + off, 100 * sum(vals) / len(vals), 0.38, color=color, label=label if i == 0 else None)
        for v in vals:
            ax2.plot(i + off, 100 * v, "k.", ms=7)
ax2.set_xticks(range(len(LLM)))
ax2.set_xticklabels([k.capitalize() for k in LLM])
ax2.set_ylim(50, 102)
ax2.set_ylabel("agreement with my labels (%)")
ax2.set_title("My 10 cases (answers from my Lecture 03 agent)\nagreement by criterion, 3 runs per model", fontsize=10)
ax2.legend(fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig(L4 / "summary_chart.png", dpi=130)
print("saved", L4 / "summary_chart.png")
