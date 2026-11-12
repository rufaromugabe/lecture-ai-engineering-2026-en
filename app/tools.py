"""Lecture 03: tools for the agent.

Function docstrings and type hints here become the "tool descriptions" presented to the model.
Rewriting descriptions changes whether the model uses a tool and which arguments it supplies.
"""

import json
import random
import re
from datetime import datetime
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# Homework (Implementation): where save_learning_log writes. Tests point this at a temp dir.
LEARNING_LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"
MAX_LOG_CHARS = 5000
MAX_RESULTS = 3


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """Search the course glossary and return definitions and the sessions that cover the terms.

    Use before answering about AI engineering terms or words specific to this course (AIE2026).
    Put only one term to look up in query (for example, "LoRA").
    """
    q = _normalize(query)
    if not q:
        return "The search query is empty. Specify one term to look up."
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # Exclude short names so aliases such as "r" do not match everything
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"The term '{query}' was not found in the glossary."
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """Return key points from the specified session (an integer starting at 1).

    Use when asked about session content or relationships, such as "What will we learn in Lecture 03?".
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"Key points for Lecture {lecture:02d} are not available yet. Available sessions: {', '.join(available)}"
    return path.read_text(encoding="utf-8")


def make_quiz(lecture: int) -> str:
    """Create one review question from the glossary terms of the specified session (an integer starting at 1).

    Use when the learner asks for a quiz, a review question, or a check question about a session,
    such as "Give me a review question on Lecture 02". Returns JSON with "question" and "answer".
    Show the question to the learner and keep the answer hidden until they reply.
    """
    candidates = [e for e in load_glossary() if e["lecture"] == lecture]
    if not candidates:
        available = sorted({e["lecture"] for e in load_glossary()})
        return (
            f"No glossary terms for Lecture {lecture:02d}, so no quiz can be made. "
            f"Sessions with terms: {', '.join(f'{n:02d}' for n in available)}"
        )
    entry = random.choice(candidates)
    return json.dumps(
        {"question": f"What does \"{entry['term']}\" mean?", "answer": entry["definition"], "lecture": lecture},
        ensure_ascii=False,
    )


def _safe_filename(title: str) -> str:
    """Turn a free-text title into a safe file name: letters, digits, '-' only, no paths."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:60].strip("-")
    return slug or "note"


def save_learning_log(title: str, content: str) -> str:
    """Save a learning record (what the learner studied or noticed) as a Markdown file in learning_log/.

    Use only when the learner explicitly asks to save, record or log what they learned.
    title is a short topic such as "LoRA vs QLoRA"; content is the note to save, written for the learner.
    The file is learning_log/<YYYY-MM-DD>_<title>.md. If it already exists, the note is appended, never overwritten.
    The user is asked to approve before anything is written.
    """
    if not title.strip() or not content.strip():
        return "Nothing was saved: both title and content must be non-empty."
    if len(content) > MAX_LOG_CHARS:
        return f"Nothing was saved: content is longer than {MAX_LOG_CHARS} characters. Shorten it."
    log_dir = LEARNING_LOG_DIR.resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = (log_dir / f"{now:%Y-%m-%d}_{_safe_filename(title)}.md").resolve()
    if path.parent != log_dir:  # defence in depth; _safe_filename already removes separators
        return "Nothing was saved: unsafe file name."
    existed = path.exists()
    with path.open("a", encoding="utf-8") as f:
        if not existed:
            f.write(f"# {title.strip()}\n")
        f.write(f"\n## {now:%Y-%m-%d %H:%M}\n\n{content.strip()}\n")
    rel = path.relative_to(log_dir.parent)
    return f"{'Appended to' if existed else 'Saved'} {rel.as_posix()}"
