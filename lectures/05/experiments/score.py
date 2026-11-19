"""Score saved runs: cited pages (parsed from the answer), evidence groups, key facts, searches, tokens, cost.

    uv run python lectures/05/experiments/score.py RUNS_DIR [RUNS_DIR ...] > scored.json
    uv run python lectures/05/experiments/score.py --questions heldout_questions.json RUNS_DIR > scored.json
Citations on the English data come in three shapes, and all three are handled:
  "Lecture 2 · Japanese source p.52"  /  "Lecture 2 · translated PDF p.98"  /  bare "Lecture 2, p. 51–52".
For Lecture 2 the two numberings differ on 21 pages, so a bare number is read as the Japanese/page number
(the `page` field the tool returns) and counted as "bare"; lec01/lec03 numbers are the same in both.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QFILE = sys.argv[2] if sys.argv[1:2] == ["--questions"] else "questions.json"   # held-out set: --questions heldout_questions.json
QUESTIONS = {q["id"]: q for q in json.loads((Path(__file__).with_name(Path(QFILE).name)).read_text(encoding="utf-8"))}
SOURCES = json.loads((ROOT / "data/rag_data/page_sources.json").read_text(encoding="utf-8"))
LABEL = {}   # (lecture, kind, number) -> page_id, main decks only
for pid, src in SOURCES.items():
    if "-main-" not in pid or pid.startswith("lec05"):
        continue
    lec = int(pid[3:5])
    LABEL[(lec, "page", src["canonical_japanese_page"])] = pid
    LABEL[(lec, "translated" if src["reference"]["kind"] == "translated_pdf" else "japanese", src["reference"]["page"])] = pid

SPAN = re.compile(r"(?:Lecture|lec)\s*0?([1-3])(?:-main)?\b(.{0,160}?)(?=[\]\)\n]|Lecture\s*\d|lec\d|$)", re.I | re.S)
TOKEN = re.compile(r"(translated PDF|Japanese source|corresponding translated PDF)|(?:\bp(?:p|ages?)?\.?\s*|,\s*|and\s+|–|-|to\s+)(\d{1,2})(?:\s*[–-]\s*(\d{1,2}))?", re.I)


PAGE_ID = re.compile(r"lec0([1-3])-main-p(\d{3})")


def citations(answer: str) -> list[dict]:
    # explicit page IDs (e.g. a markdown link to lec02-main-p052) count as exact citations
    out = [{"page_id": m.group(0), "kind": "page_id", "ambiguous": False, "mismatch": False} for m in PAGE_ID.finditer(answer)]
    answer = PAGE_ID.sub(" ", answer)
    for m in SPAN.finditer(answer):
        lec, body = int(m.group(1)), m.group(2)
        if not re.search(r"\bp(?:p|ages?)?\.?\s*\d|\bpage", body, re.I):
            continue
        kind, skip = "bare", False
        for t in TOKEN.finditer(body):
            if t.group(1):
                label = t.group(1).lower()
                skip = label.startswith("corresponding")
                kind = "translated" if "translated" in label else "japanese"
                continue
            if skip or not t.group(2):
                continue
            lo = int(t.group(2)); hi = int(t.group(3) or lo)
            for n in range(lo, min(hi, lo + 6) + 1):
                key = (lec, kind if kind != "bare" else "page", n)
                pid = LABEL.get(key) or LABEL.get((lec, "page", n))
                ambiguous = kind == "bare" and lec == 2 and LABEL.get((2, "translated", n)) not in (None, pid)
                if pid:
                    out.append({"page_id": pid, "kind": kind, "ambiguous": ambiguous, "mismatch": key not in LABEL})
    return out


HINT = re.compile(r"ask yourself|take a (close )?look|try (to )?(explain|compar|think)|review (pages|the)|look at how|what do you think|can you (think|identify)|consider (how|why|what)\b", re.I)


def score(record: dict) -> dict:
    q = QUESTIONS[record["qid"]]
    cites = citations(record["answer"])
    cited = {c["page_id"] for c in cites}
    slots = q["slots"]
    evidence = sum(any(p in cited for p in s) for s in slots) / len(slots) if slots else None
    facts = q["facts"]
    fact_score = (sum(any(re.search(f, record["answer"], re.I) for f in group) for group in facts) / len(facts)) if facts else None
    labelled = {p for s in slots for p in s}
    returned = {p["page_id"] for call in record["returned"] for p in call}
    retrieved_ev = sum(any(p in returned for p in s) for s in slots) / len(slots) if slots else None
    neighbor_ids = {p["page_id"] for call in record["returned"] for p in call if p["role"] in ("neighbor", "expanded")}
    return {**{k: record[k] for k in ("condition", "k", "db", "rep", "qid", "time", "input_tokens", "output_tokens", "requests", "cost")},
            "searches": len(record["queries"]), "queries": record["queries"],
            "cited": sorted(cited), "evidence_cited": evidence, "evidence_retrieved": retrieved_ev,
            "facts": fact_score, "unlabelled_cited": sorted(cited - labelled),
            "n_cites": len(cites), "bare_cites": sum(c["kind"] == "bare" for c in cites),
            "ambiguous_cites": sum(c["ambiguous"] for c in cites), "mismatch_cites": sum(c["mismatch"] for c in cites),
            "pages_returned": sum(len(call) for call in record["returned"]),
            "added_pages_cited": sorted(cited & neighbor_ids),
            "added_evidence_cited": sorted(cited & neighbor_ids & labelled),
            "hint_flag": bool(HINT.search(record["answer"])),
            "refused": bool(re.search(r"not explicitly|do not specify|does not specify|don't specify|cannot verify|can't verify|not (contain|include|mention|specif|provide|found)|no (mention|information|specific)|does not (specify|mention|contain|include|provide)|doesn't (specify|mention|contain)|unable to (find|verify)|not available|not listed|outside", record["answer"], re.I)),
            "two_part_one_search": len(slots) >= 2 and len(record["queries"]) == 1}


if __name__ == "__main__":
    rows = []
    for d in (sys.argv[3:] if sys.argv[1:2] == ["--questions"] else sys.argv[1:]):
        for f in sorted(Path(d).glob("*.json")):
            rows.append(score(json.loads(f.read_text(encoding="utf-8"))))
    print(json.dumps(rows, ensure_ascii=False, indent=1))
