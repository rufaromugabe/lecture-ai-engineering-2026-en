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
