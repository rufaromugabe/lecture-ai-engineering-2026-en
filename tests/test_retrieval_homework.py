"""Lecture 05 homework: neighbour expansion and the hub retriever, offline (no API calls)."""

import pytest

from app import retrieval as r
from app.config import RAG_SOURCE

pytestmark = pytest.mark.skipif(not RAG_SOURCE.is_file(), reason="Lecture 05 materials not present")


def hit(page_id, distance=0.1):
    return {"page_id": page_id, "distance": distance}


def ids(results):
    return [p["page_id"] for p in results]


def test_neighbors_never_cross_documents():
    out = r.expand_neighbors([hit("lec01-main-p073"), hit("lec02-main-p001")])
    assert all(p["page_id"][:10] == p["document_id"] for p in out)
    assert "lec01-main-p074" not in ids(out) and "lec02-main-p000" not in ids(out)


def test_adjacent_hits_are_not_duplicated_and_stay_hits():
    out = r.expand_neighbors([hit("lec02-main-p051"), hit("lec02-main-p052")])
    assert ids(out) == ["lec02-main-p050", "lec02-main-p051", "lec02-main-p052", "lec02-main-p053"]
    roles = {p["page_id"]: p["role"] for p in out}
    assert roles["lec02-main-p051"] == roles["lec02-main-p052"] == "hit"
    assert len(ids(out)) == len(set(ids(out)))


def test_lower_ranked_hit_next_to_better_hit_keeps_its_rank():
    out = r.expand_neighbors([hit("lec02-main-p042"), hit("lec02-main-p043")])
    p43 = next(p for p in out if p["page_id"] == "lec02-main-p043")
    assert p43["role"] == "hit" and p43["rank"] == 2


def test_quiz_question_brings_answer_page_with_citation_metadata():
    out = r.expand_neighbors([hit("lec02-main-p042")])
    answer = next(p for p in out if p["page_id"] == "lec02-main-p043")
    assert answer["role"] == "neighbor" and answer["side"] == "after" and answer["neighbor_of"] == "lec02-main-p042"
    assert {"page", "lecture", "title", "content", "citation"} <= answer.keys()


def test_no_divider_or_next_section_neighbours():
    out = ids(r.expand_neighbors([hit("lec03-main-p038")]))
    assert "lec03-main-p037" not in out          # 'Part 6 Memory' divider page, 45 characters
    assert "lec03-main-p039" in out
    out = ids(r.expand_neighbors([hit("lec03-main-p036")]))
    assert "lec03-main-p037" not in out          # first page of the next section


def test_named_lectures():
    assert r.named_lectures("What do Lectures 01 and 02 say?") == {1, 2}
    assert r.named_lectures("How do Lecture 01 and Lecture 03 each argue") == {1, 3}
    assert r.named_lectures("In Lecture 03, why?") == {3}
    assert r.named_lectures("Lectures 1, 2 and 3") == {1, 2, 3}
    assert r.named_lectures("What is LoRA?") == set()


def test_hub_edges_point_to_real_pages():
    by_id, _ = r._pages_by_position()
    for source, targets in r.elaborates().items():
        assert source in by_id and all(t in by_id for t in targets)


def fake_ranking(order):
    by_id, _ = r._pages_by_position()
    return [{**by_id[p], "distance": i / 100} for i, p in enumerate(order)]


def test_hub_adds_detail_pages_and_missing_lecture(monkeypatch):
    by_id, _ = r._pages_by_position()
    order = ["lec02-main-p003", "lec02-main-p004", "lec02-main-p005", "lec02-main-p015", "lec01-main-p046"]
    order += [p for p in by_id if p not in order]
    monkeypatch.setattr(r, "rank_all", lambda q: fake_ranking(order))
    out = r.search_hub("why benchmarks are not enough", question="What do Lectures 01 and 02 say?")
    roles = {p["page_id"]: p.get("via", p["role"]) for p in out}
    assert ids(out)[:3] == order[:3]
    assert roles["lec02-main-p015"].startswith("detail of overview lec02-main-p003")
    assert roles["lec01-main-p046"].startswith("Lecture 1 is named")
    assert len(out) <= r.HUB_MAX_RESULTS and len(set(ids(out))) == len(out)


def test_default_retriever_is_plain_vector_search(monkeypatch):
    monkeypatch.setattr(r, "RETRIEVER", "vector")
    monkeypatch.setattr(r, "search", lambda q: [hit("lec02-main-p052")])
    assert r.retrieve("LoRA") == [hit("lec02-main-p052")]


# --- automatic overview links (lectures/05/hub/build_links.py) ---
import importlib.util  # noqa: E402
import json  # noqa: E402

from app.config import HUB_EDGES_AUTO, RAG_DB, ROOT  # noqa: E402


def load_builder():
    spec = importlib.util.spec_from_file_location("build_links", ROOT / "lectures/05/hub/build_links.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page(n, section, title, content="x" * 200, doc="lec09-main"):
    return {"page_id": f"{doc}-p{n:03d}", "document_id": doc, "section": section, "title": title, "page": n, "content": content}


def test_builder_rules_on_synthetic_lecture():
    b = load_builder()
    pages = [page(1, "Opening", "Title", "short"), page(2, "Opening", "Agenda"),
             page(3, "Part 1", "Part 1", "short"), page(4, "Part 1", "Intro to part 1"), page(5, "Part 1", "Detail A"),
             page(6, "Part 1", "Detail B"), page(7, "Part 2", "Part 2"), page(8, "Part 2", "Opener 2"),
             page(9, "Part 2", "Summary of the lecture"), page(10, "Appendix", "Appendix"), page(11, "Appendix", "Extra")]
    kinds = b.detect(pages)
    assert kinds == {"lec09-main-p002": "lecture", "lec09-main-p004": "section",
                     "lec09-main-p008": "section", "lec09-main-p009": "summary"}
    # section opener: following pages up to the section break; no dividers, no other overviews
    assert b.candidates(pages, 3, "section", kinds) == ["lec09-main-p005", "lec09-main-p006"]
    assert b.candidates(pages, 7, "section", kinds) == []                       # next page is an overview
    assert b.candidates(pages, 8, "summary", kinds) == ["lec09-main-p005", "lec09-main-p006"]
    vectors = {p["page_id"]: (1.0, 0.0) for p in pages}
    vectors["lec09-main-p006"] = (0.9, 0.1)
    vectors["lec09-main-p005"] = (0.0, 1.0)
    edges = {e["source"]: e["targets"] for e in b.build(pages, vectors)}
    assert edges["lec09-main-p004"] == ["lec09-main-p006", "lec09-main-p005"]  # most similar first
    assert all(len(t) <= b.MAX_LINKS for t in edges.values())


@pytest.mark.skipif(not RAG_DB.is_file() or not HUB_EDGES_AUTO.is_file(), reason="index or auto links not present")
def test_auto_link_file_is_reproducible_and_stays_inside_each_lecture():
    b = load_builder()
    saved = json.loads(HUB_EDGES_AUTO.read_text(encoding="utf-8"))["edges"]
    assert saved == b.build(r.load_pages(), b.embeddings())
    by_id, _ = r._pages_by_position()
    for edge in saved:
        assert edge["source"] in by_id and edge["targets"]
        assert all(by_id[t]["document_id"] == by_id[edge["source"]]["document_id"] for t in edge["targets"])


def test_hub_auto_uses_the_auto_links(monkeypatch):
    auto = r.elaborates(auto=True)
    source = next(iter(auto))
    by_id, _ = r._pages_by_position()
    order = [source] + [p for p in by_id if p != source]
    monkeypatch.setattr(r, "rank_all", lambda q: fake_ranking(order))
    out = r.search_hub("anything", question="no lecture named", auto=True)
    added = [p for p in out if p["role"] == "expanded"]
    assert added and all(p["page_id"] in auto[source] and p["via"].endswith("(auto link)") for p in added)
