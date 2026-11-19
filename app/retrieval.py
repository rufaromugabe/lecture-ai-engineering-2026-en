"""Lecture 05: page-level vector search."""

import argparse
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from collections import defaultdict, deque
from pathlib import Path

from google import genai
from google.genai import types
from pydantic_ai.exceptions import ModelHTTPError
import sqlite_vec

from app.config import (
    EMBEDDING_DIMENSIONS, EMBEDDING_MAX_TOKENS, EMBEDDING_MODEL,
    RAG_DB, RAG_DOCUMENT_IDS, RAG_SOURCE, RAG_TOP_K, RAG_TREE, get_api_key,
    RAG_GRAPH, GRAPH_START_K, GRAPH_HOPS, GRAPH_MAX_RESULTS,
)


def get_all_materials() -> str:
    """Combine all materials into one string with lecture, section, and page metadata."""
    documents = json.loads(RAG_SOURCE.read_text(encoding="utf-8"))
    return "\n\n".join(
        f"Document: {document['id']} / {document['title']}\n"
        f"Section: {section['section']}\n"
        f"Page: {page.get('citation') or ('PDF p.' + str(page['page']))} / {page['title']}\n{page['content']}"
        for document in documents
        for section in document["content"]
        for page in section["content"]
    )

def load_pages(source: Path = RAG_SOURCE) -> list[dict]:
    """Convert document → section → page JSON into a page list for the selected materials."""
    documents = json.loads(source.read_text(encoding="utf-8"))
    pages = []
    for document in documents:
        if document["id"] not in RAG_DOCUMENT_IDS:
            continue
        for section in document["content"]:
            for page in section["content"]:
                pages.append({"page_id": page["id"], "document_id": document["id"],
                              "lecture": int(document["id"][3:5]), "document_title": document["title"],
                              "section": section["section"], "title": page["title"],
                              "page": page["page"], "content": page["content"]})
                if page.get("citation"):
                    pages[-1]["citation"] = page["citation"]
    return pages


def browse_tree(node_id: str | None = None) -> dict:
    """Return the first sentence for child pages and the full text for the selected page itself."""
    tree = json.loads(RAG_TREE.read_text(encoding="utf-8"))
    tree["children"] = [node for node in tree["children"] if node["id"] in RAG_DOCUMENT_IDS]
    node_id = node_id or tree["id"]
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}

    def describe(node, full=False):
        info = {key: node[key] for key in ("id", "kind", "title")}
        if node["kind"] == "page":
            info.update({key: value for key, value in pages[node["id"]].items() if key != "page_id"})
            if not full:
                info["content"] = re.split(r"(?<=[。！？।॥])|(?<=[.!?؟])\s+|\n", info["content"].strip(), maxsplit=1)[0]
        return info

    remaining = [tree]
    while remaining:
        node = remaining.pop()
        if node["id"] == node_id:
            return {
                "node": describe(node, full=True),
                "children": [describe(child) for child in node.get("children", [])],
            }
        remaining.extend(node.get("children", []))
    raise ValueError("The requested table-of-contents node was not found.")


def read_page(page_id: str) -> dict:
    """Return text and citation metadata for one specified page from the main materials for Lectures 01–03."""
    for page in load_pages(RAG_SOURCE):
        if page["page_id"] == page_id:
            return page
    raise ValueError("The requested page was not found.")


def normalized_vector(values: list[float]) -> list[float]:
    """Normalize the vector to unit length."""
    norm = math.hypot(*values)
    if norm == 0:
        raise ValueError("The embedding is a zero vector.")
    return [value / norm for value in values]


def embed_text(text: str, task_type: str) -> list[float]:
    """Embed text with Gemini. Stop instead of truncating if the input limit is exceeded."""
    with genai.Client(api_key=get_api_key()) as client:
        count = client.models.count_tokens(model=EMBEDDING_MODEL, contents=text).total_tokens
        if count is None or count > EMBEDDING_MAX_TOKENS:
            raise ValueError(f"Embedding input exceeds the limit or could not be measured: {count} tokens.")
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=text,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS),
        )
    embedding = response.embeddings[0]
    if embedding.statistics and embedding.statistics.truncated:
        raise ValueError("The embedding API truncated the text.")
    return normalized_vector(embedding.values)


@contextmanager
def open_index(path: Path):
    """Open an existing search database read-only and close it on exit."""
    if not path.is_file():
        raise FileNotFoundError("Search database not found.")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        db.row_factory = sqlite3.Row
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        yield db
    finally:
        db.close()


def search(query: str) -> list[dict]:
    """Embed the query and return up to RAG_TOP_K similar pages."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("The search query is empty.")
    with open_index(RAG_DB) as db:
        vector = embed_text(query.strip(), "RETRIEVAL_QUERY")
        columns = {column["name"] for column in db.execute("PRAGMA table_info(chunks)")}
        citation = "citation," if "citation" in columns else ""
        rows = db.execute(f"""
            SELECT page_id, document_id, lecture, document_title, section, title, page, content,
                   {citation}
                   vec_distance_cosine(embedding, ?) AS distance
            FROM chunks ORDER BY distance, page_id LIMIT ?
        """, (sqlite_vec.serialize_float32(vector), RAG_TOP_K))
        return [dict(row) for row in rows]


def search_graph(query: str) -> dict:
    """Start with vector search, then expand candidates through adjacent pages and shared terms."""
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}
    graph = json.loads(RAG_GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]
             if node["kind"] == "term" or node["id"] in pages}
    adjacent = defaultdict(set)
    for edge in graph["edges"]:
        a, b = edge["source"], edge["target"]
        if edge["relation"] in ("next_page", "mentions") and a in nodes and b in nodes:
            adjacent[a].add(b)
            adjacent[b].add(a)

    seeds = [hit for hit in search(query) if hit["page_id"] in pages][:min(GRAPH_START_K, GRAPH_MAX_RESULTS)]
    seed_ids = {seed["page_id"] for seed in seeds}
    results, candidates = [], {}
    for rank, seed in enumerate(seeds):
        root = seed["page_id"]
        results.append({**pages[root], "distance": seed["distance"], "hops": 0,
                        "path": [{"id": root, "title": pages[root]["title"]}]})
        queue = deque([(root, [root])])
        visited = {root}
        while queue:
            current, path = queue.popleft()
            if len(path) - 1 >= GRAPH_HOPS:
                continue
            # At the same depth, follow terms with fewer connections first.
            neighbors = sorted(adjacent[current], key=lambda n: (len(adjacent[n]), n))
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                route = path + [neighbor]
                queue.append((neighbor, route))
                if neighbor not in pages or neighbor in seed_ids:
                    continue
                frequency = max((len(adjacent[n]) for n in route if nodes[n]["kind"] == "term"), default=0)
                priority = (len(route) - 1, frequency, rank, neighbor)
                candidate = {**pages[neighbor], "hops": len(route) - 1,
                             "path": [{"id": n, "title": nodes[n]["title"]} for n in route]}
                if neighbor not in candidates or priority < candidates[neighbor][0]:
                    candidates[neighbor] = (priority, candidate)
    expanded = [candidate for _, candidate in sorted(candidates.values())]
    return {"seeds": results, "expanded": expanded[:max(0, GRAPH_MAX_RESULTS - len(results))],
            "max_hops": GRAPH_HOPS}



def run_full_context(agent, question: str, model, instructions: str, prompt_template: str):
    """Pass all materials at once and answer without retrieval tools."""
    prompt = prompt_template.format(materials=get_all_materials(), question=question)
    print(f"[full-context] Input: {len(prompt):,} characters")
    try:
        with agent.override(tools=[], instructions=instructions):
            return agent.run_sync(prompt, model=model)
    except ModelHTTPError as e:
        print(f"[full-context] API error HTTP {e.status_code}: {e.body}")
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the lecture materials without using an agent")
    parser.add_argument("query", help="What to look up")
    args = parser.parse_args()
    for i, result in enumerate(search(args.query), 1):
        print(f"\n{'=' * 60}\nSearch result {i}\n{'=' * 60}")
        print(f"Lecture: {result['document_title']}")
        print(f"Section: {result['section']}")
        print(f"Title: {result['title']}")
        print(f"Page: {result.get('citation') or result['page']}")
        print(f"\n{result['content']}")


# ---------------------------------------------------------------------------
# Lecture 05 homework. RETRIEVER chooses what search_materials returns.
# ---------------------------------------------------------------------------
from contextvars import ContextVar
from functools import cache

from app.config import (HUB_DETAIL_PER_SEED, HUB_EDGES, HUB_EDGES_AUTO, HUB_MAX_RESULTS, HUB_PER_MISSING_LECTURE,
                        HUB_START_K, NEIGHBOR_MIN_CHARS, RAG_RETRIEVER)

RETRIEVER = RAG_RETRIEVER
# The learner's question, set by the caller, so the hub retriever can see which lectures it names.
CURRENT_QUESTION: ContextVar[str] = ContextVar("CURRENT_QUESTION", default="")


@cache
def _pages_by_position() -> tuple[dict, dict]:
    pages = load_pages(RAG_SOURCE)
    return {p["page_id"]: p for p in pages}, {(p["document_id"], p["page"]): p for p in pages}


def expand_neighbors(hits: list[dict]) -> list[dict]:
    """Implementation level: return each hit followed by its page-1 / page+1.

    - neighbours come from load_pages() metadata: same document_id AND same section, so a hit never pulls in
      another lecture or the opener of the next section
    - "Part N" divider pages (under NEIGHBOR_MIN_CHARS characters) are not added as neighbours
    - each page appears once; a page that is itself a hit is always labelled "hit" and keeps its own rank
    - every page keeps its text and citation metadata; neighbours say which hit they belong to
    """
    by_id, by_pos = _pages_by_position()
    hit_ids = {hit["page_id"] for hit in hits}
    out, seen = [], set()
    for rank, hit in enumerate(hits, 1):
        page = by_id.get(hit["page_id"], hit)
        for offset in (-1, 0, 1):
            item = page if offset == 0 else by_pos.get((page["document_id"], page["page"] + offset))
            if item is None or item["page_id"] in seen:
                continue
            if offset == 0:
                entry = {**page, **hit, "role": "hit", "rank": rank}
            elif (item["page_id"] in hit_ids or item["section"] != page["section"]
                  or len(item["content"].strip()) < NEIGHBOR_MIN_CHARS):
                continue
            else:
                entry = {**item, "role": "neighbor", "neighbor_of": hit["page_id"],
                         "side": "before" if offset < 0 else "after"}
            seen.add(item["page_id"])
            out.append(entry)
    return out


def search_with_neighbors(query: str) -> list[dict]:
    """Vector search (RAG_TOP_K hits), then add adjacent pages."""
    return expand_neighbors(search(query))


LECTURE_NUMBER = re.compile(r"\b(?:Lectures?|lec)\s*0?([1-9])((?:\s*(?:,|and|&|or)\s*0?[1-9])*)", re.I)


def named_lectures(text: str) -> set[int]:
    """Lectures named in text: 'Lecture 01', 'Lectures 01 and 02', 'Lecture 1, 2 and 3'."""
    found = set()
    for first, rest in LECTURE_NUMBER.findall(text):
        found |= {int(first)} | {int(n) for n in re.findall(r"[1-9]", rest)}
    return found


@cache
def elaborates(auto: bool = False) -> dict[str, list[str]]:
    """Overview -> detail links: hand-checked (elaborates.json) or built by build_links.py (elaborates_auto.json)."""
    data = json.loads((HUB_EDGES_AUTO if auto else HUB_EDGES).read_text(encoding="utf-8"))
    return {edge["source"]: edge["targets"] for edge in data["edges"]}


def rank_all(query: str) -> list[dict]:
    """One query embedding, distance for every indexed page (expansion ranks candidates by the same distance)."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("The search query is empty.")
    with open_index(RAG_DB) as db:
        vector = embed_text(query.strip(), "RETRIEVAL_QUERY")
        rows = db.execute("""
            SELECT page_id, document_id, lecture, document_title, section, title, page, content, citation,
                   vec_distance_cosine(embedding, ?) AS distance
            FROM chunks ORDER BY distance, page_id
        """, (sqlite_vec.serialize_float32(vector),))
        return [dict(row) for row in rows]


def search_hub(query: str, question: str | None = None, auto: bool = False) -> list[dict]:
    """Advanced level: vector seeds, then two typed expansions. Each page says why it was returned.

    1. elaborates: a seed that is an overview / agenda / summary page brings in its most query-similar detail pages
    2. lecture coverage: if the question or query names a lecture that no page so far comes from,
       add the best pages from inside that lecture (same query vector, restricted to that document)
    """
    ranked = rank_all(query)
    distance = {row["page_id"]: row["distance"] for row in ranked}
    rows = {row["page_id"]: row for row in ranked}
    links = elaborates(auto)
    results = [{**row, "role": "seed", "rank": i} for i, row in enumerate(ranked[:HUB_START_K], 1)]
    chosen = {row["page_id"] for row in results}

    def add(page_id: str, via: str) -> None:
        if len(results) < HUB_MAX_RESULTS and page_id not in chosen and page_id in rows:
            chosen.add(page_id)
            results.append({**rows[page_id], "role": "expanded", "via": via})

    for seed in list(results):
        targets = sorted((t for t in links.get(seed["page_id"], []) if t not in chosen), key=lambda t: distance.get(t, 9))
        for target in targets[:HUB_DETAIL_PER_SEED]:
            add(target, f"detail of overview {seed['page_id']}" + (" (auto link)" if auto else ""))

    named = named_lectures((question or CURRENT_QUESTION.get() or "") + " " + query)
    for lecture in sorted(named - {row["lecture"] for row in results}):
        inside = [row["page_id"] for row in ranked if row["lecture"] == lecture]
        for page_id in inside[:HUB_PER_MISSING_LECTURE]:
            add(page_id, f"Lecture {lecture} is named but had no result: best pages inside it")
    return results


def retrieve(query: str) -> list[dict]:
    """What search_materials returns. RETRIEVER = "vector" keeps the original behaviour."""
    if RETRIEVER == "vector":
        return search(query)
    if RETRIEVER == "neighbors":
        return search_with_neighbors(query)
    if RETRIEVER == "hub":
        return search_hub(query)
    if RETRIEVER == "hub_auto":
        return search_hub(query, auto=True)
    raise ValueError(f"Unknown retriever: {RETRIEVER}")
