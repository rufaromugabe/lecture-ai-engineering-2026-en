"""Build overview -> detail links automatically (no hand labels). Output: lectures/05/hub/elaborates_auto.json

    uv run python lectures/05/hub/build_links.py            # write elaborates_auto.json
    uv run python lectures/05/hub/build_links.py --compare  # also print overlap with the hand-written elaborates.json

Rules, fixed before any agent run:
1. Overview detection, from text and position only:
   - dividers are never overviews or details: the first page of every section (its title page) and any page
     under DIVIDER_CHARS characters
   - "lecture" overview: a page in the lecture's opening section ("Opening" / "Introduction"), or one whose title
     or first line has an agenda word (agenda, outline, contents, overview)
   - "summary": the title or first line has "summary" / "recap" / "wrap-up"
   - "section" opener: the first page after a section's divider, outside Appendix / Supplement sections
2. Candidate detail pages (same lecture, content pages only, never another overview):
   - lecture overview -> every later page of the lecture
   - summary          -> every earlier page of the lecture
   - section opener   -> the following pages up to the next section break or overview
3. Keep the MAX_LINKS candidates most similar to the overview page (cosine of the stored page embeddings).
"""
import json
import re
import sqlite3
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.config import RAG_DB  # noqa: E402
from app.retrieval import load_pages  # noqa: E402

OUT = Path(__file__).with_name("elaborates_auto.json")
HAND = Path(__file__).with_name("elaborates.json")
DIVIDER_CHARS = 150   # same cut as the neighbour retriever: shorter pages are dividers / title pages
MAX_LINKS = 6
AGENDA = re.compile(r"\b(agenda|outline|contents|overview)\b", re.I)
SUMMARY = re.compile(r"\b(summary|recap|wrap-?up)\b", re.I)
OPENING = re.compile(r"^(opening|introduction)$", re.I)
NO_OPENER = re.compile(r"appendix|supplement", re.I)


def first_line(page: dict) -> str:
    return page["content"].strip().split("\n", 1)[0]


def dividers(pages: list[dict]) -> set[str]:
    """Section title pages (first page of each section) and very short pages."""
    out = {p["page_id"] for p in pages if len(p["content"].strip()) < DIVIDER_CHARS}
    out |= {p["page_id"] for i, p in enumerate(pages) if i == 0 or p["section"] != pages[i - 1]["section"]}
    return out


def detect(pages: list[dict]) -> dict[str, str]:
    """page_id -> kind ('lecture' | 'summary' | 'section') for the pages of one lecture, in page order."""
    skip, kinds = dividers(pages), {}
    for i, page in enumerate(pages):
        if page["page_id"] in skip:
            continue
        head = page["title"] + " " + first_line(page)
        if OPENING.match(page["section"].strip()) or AGENDA.search(head):
            kinds[page["page_id"]] = "lecture"
        elif SUMMARY.search(head):
            kinds[page["page_id"]] = "summary"
        elif pages[i - 1]["page_id"] in skip and pages[i - 1]["section"] == page["section"] and not NO_OPENER.search(page["section"]):
            kinds[page["page_id"]] = "section"
    return kinds


def candidates(pages: list[dict], i: int, kind: str, kinds: dict) -> list[str]:
    skip = dividers(pages)
    ok = lambda p: p["page_id"] not in skip and p["page_id"] not in kinds  # noqa: E731
    if kind == "lecture":
        return [p["page_id"] for p in pages[i + 1:] if ok(p)]
    if kind == "summary":
        return [p["page_id"] for p in pages[:i] if ok(p)]
    out = []
    for p in pages[i + 1:]:
        if p["section"] != pages[i]["section"] or not ok(p):
            break
        out.append(p["page_id"])
    return out


def embeddings(db_path: Path = RAG_DB) -> dict[str, list[float]]:
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {pid: struct.unpack(f"{len(blob) // 4}f", blob) for pid, blob in db.execute("SELECT page_id, embedding FROM chunks")}
    finally:
        db.close()


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5))


def build(pages: list[dict], vectors: dict) -> list[dict]:
    edges = []
    by_lecture = {}
    for page in pages:
        by_lecture.setdefault(page["document_id"], []).append(page)
    for doc_pages in by_lecture.values():
        doc_pages.sort(key=lambda p: p["page"])
        kinds = detect(doc_pages)
        for i, page in enumerate(doc_pages):
            kind = kinds.get(page["page_id"])
            if not kind:
                continue
            cands = [c for c in candidates(doc_pages, i, kind, kinds) if c in vectors]
            cands.sort(key=lambda c: -cosine(vectors[page["page_id"]], vectors[c]))
            if cands:
                edges.append({"source": page["page_id"], "kind": kind, "targets": cands[:MAX_LINKS],
                              "why": f"{kind} page -> {min(len(cands), MAX_LINKS)} most similar of {len(cands)} candidates"})
    return edges


def compare(auto: list[dict], hand_path: Path = HAND) -> dict:
    hand = {e["source"]: set(e["targets"]) for e in json.loads(hand_path.read_text(encoding="utf-8"))["edges"]}
    mine = {e["source"]: set(e["targets"]) for e in auto}
    hand_links = {(s, t) for s, ts in hand.items() for t in ts}
    auto_links = {(s, t) for s, ts in mine.items() for t in ts}
    both = hand_links & auto_links
    src = set(hand) & set(mine)
    return {"overview pages: hand / auto / both": [len(hand), len(mine), len(src)],
            "overview precision": round(len(src) / len(mine), 2), "overview recall": round(len(src) / len(hand), 2),
            "links: hand / auto / both": [len(hand_links), len(auto_links), len(both)],
            "link precision": round(len(both) / len(auto_links), 2), "link recall": round(len(both) / len(hand_links), 2)}


if __name__ == "__main__":
    edges = build(load_pages(), embeddings())
    OUT.write_text(json.dumps({"description": "Automatic overview -> detail links from build_links.py "
                               f"(DIVIDER_CHARS={DIVIDER_CHARS}, MAX_LINKS={MAX_LINKS}); not hand-checked.",
                               "edges": edges}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(edges)} overview pages, {sum(len(e['targets']) for e in edges)} links -> {OUT.name}")
    if "--compare" in sys.argv:
        print(json.dumps(compare(edges), indent=1))
