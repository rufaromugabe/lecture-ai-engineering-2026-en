# Lecture 05 Answers

## Exercises

- Answering model (`[model]` shown during execution): `gemini-3.5-flash-lite`, default settings. Query embedding `gemini-embedding-001`, 768 dims.
- Comparison question: `In Lecture 02, what does LoRA freeze and what does it train? What does QLoRA add?`
- Target materials: English data on `main` (2e201d1). Vector, Tree and Graph search the 214 main pages of Lectures 01–03. Full context sends all 8 documents, 398 pages (95,824 input tokens), so it also sees the exercise decks. The bundled index still holds the original Japanese-text vectors (byte-identical to the Japanese index, I checked), so English queries are matched against Japanese text.

### Results by Method

Q1, 3 runs each:

| Method | Key points and correctness of the answer | Cited pages and evidence | Time (seconds) | Input/output tokens | Model responses | Estimated generation API cost (USD) |
|---|---|---|---|---|---|---|
| Full context | Correct 3/3: base weights frozen, low-rank A and B trained, QLoRA compresses the frozen weights to 4 bits | L02 p.52 (3/3), always with the full supplied label | 1.37–2.32 | 95,824 / 135–230 | 1 | 0.0293 cold, 0.0044 / 0.0042 cached |
| Vector search | Correct 3/3 | L02 p.51–52, written as bare `Lecture 2, p. 51–52` | 2.15–2.76 | 2,759 / 157–253 | 2 | 0.0012–0.0015 |
| Tree | Correct 3/3 | p.52 (3/3) | 4.35–4.67 | 9,442 / 314–329 | 5 | 0.0036–0.0037 |
| Graph | Correct 3/3 | p.51–52 in 2 runs; run 1 cited no page | 2.52–2.71 | 5,190 / 189–251 | 2 | 0.0015–0.0021 |

Extra questions, 1 run each. Q2 (evidence L03 p.13, 39, 40), about compaction vs memory: all four were correct on part 1. Full context ($0.0296) and vector ($0.0014, one search) got both parts. Tree read p.39/40 and still turned the "no" into a hint. Q3 (not in the materials): all four said there's no measurement. Tree got there from headings without reading a page. Full context cited `Lecture 2 · translated PDF p.8` for advice that's actually in the Lecture 2 *exercise* deck, so the shortened label points to a different main-deck page.

- Pages found by running search alone: `LoRA QLoRA difference` → L02 p.52, 51, 60, 47, 61. p.52 is the evidence (W frozen, A/B trained, 4-bit base) and p.51 supports it. p.60/61 (exercise plan) and p.47 (RAG vs FT) only share terms.
- Tool calls shown by `--trace`: vector made 1 call, `LoRA freeze train QLoRA add`. Tree went root → Lecture 2 → s045 "When and how to adapt the selected model" → p.52 every run. Graph's 7 expanded pages were 6 via `next_page` and 1 via the term `lora`. Repeats were nearly deterministic: same queries, same paths, identical token counts.
- Insufficient evidence, or retrieved but not used: none on Q1. On Q2, Tree had p.40 and withheld the answer.
- Method I'd adopt: vector search. It was right 3/3 with 35x fewer tokens than full context and the lowest cost. Limitation: Q1 is a one-page question, 3 runs, and full context sees a wider scope.
- Observations and questions:
  - Full context only got cheap on the back-to-back Q1 repeats (implicit cache). Q2/Q3 a few minutes later were billed cold again ($0.029).
  - Agent answers mostly ignore the supplied `citation` label. For Lecture 2 that matters: 22 pages use translated-PDF numbers and 48 use Japanese-source numbers, so a bare `p.21` can mean two different slides.

## Homework

<!-- Completing any one of Basic, Implementation, or Advanced is sufficient. -->

- Level attempted: Basic, Implementation and Advanced.
- What you did: Basic, `RAG_TOP_K` 1/3/5/10. Implementation, neighbour pages in `app/retrieval.py` (`--retriever neighbors`), plus an English re-embedded index to test the Japanese-vector question. Advanced, my own `hub` retriever (`--retriever hub`, `lectures/05/hub/elaborates.json`). Offline tests are in `tests/test_retrieval_homework.py` (26/26 pass with the existing ones).
- Comparison question and conditions held fixed: same model, 214-page scope, `INSTRUCTIONS` and `search_materials` tool. `lectures/05/experiments/harness.py` changes only k / index / retriever and calls the same `agent.run_sync` + `print_trace` as `app.agent`. 17 questions I wrote and labelled from the pages (`experiments/questions.json`), with evidence groups and key facts. `score.py` parses all three citation styles into page IDs. 3 runs per cell, interleaved, 366 runs in total. All runs are in `results/runs.csv`.

### Headline: the Japanese vectors are fine for English queries

I rebuilt the index from the English text (`AIE_RAG_DB`, same model and dims) and compared both indexes with the same query vectors. On the 106 real queries the agent sent, the bundled JA vectors were slightly *better*: MRR 0.907 vs 0.882, evidence at rank 1 89 vs 86. The JA vectors won on 15 queries and lost on 7. At the agent level (vector k=3), evidence cited was 0.95 vs 0.91, which is within noise. English titles found their own page at rank 1 about equally (175 vs 177 of 214). So the mismatch costs almost nothing here, and I wouldn't rebuild. Data: `results/agent_query_ranks.csv`, `question_ranks.csv`, `title_probe.csv`.

### Basic: RAG_TOP_K (9 questions × 3 runs per row)

| RAG_TOP_K | searches (mean, max) | input tokens median | cost USD mean | evidence cited | key facts | 2-part questions answered after 1 search |
|---|---|---|---|---|---|---|
| 1 | 2.8, 7 | 2,116 | 0.0019 | 0.90 | 0.94 | 3/15 |
| 3 | 1.9, 3 | 3,771 | 0.0019 | **0.98** | 0.96 | 1/15 |
| 5 (default) | 1.7, 3 | 4,785 | 0.0021 | **0.98** | **0.98** | 4/15 |
| 10 | 1.2, 3 | 3,874 | 0.0021 | 0.94 | 0.94 | 13/15 |

I first ran Basic on the Japanese reference data before the English data came out on 19 Nov, then redid it here. The chart compares the two: `results/basic_topk.png`

- Big k makes the agent stop early. At k=10 it answered 13/15 two-part questions after one search. On X1 that drops the Lecture 01 page, because L01 p.46 only shows up on a second, Lecture-1 search (2/3 runs at k=3, 0/3 at k=10).
- The k=1 runaway from the Japanese data is gone: max 7 searches and $0.0047, compared with 33 searches and $0.035 before.
- Hint-only answers fell from 12/156 to 1/108, and no answer came back in Japanese.
- 379 of 550 citations were bare page numbers instead of the supplied label. 48 of those are Lecture 2 numbers that mean a different slide in the translated PDF.
- Pick: k=3 or 5. They tie on evidence, and k=3 uses 21% fewer tokens.

### Implementation: neighbour pages

Each hit gets page-1 and page+1 from `load_pages()` metadata, only within the same document and section. Pages under 150 characters (dividers, title, appendix) are skipped, nothing is duplicated, a page that's also a hit keeps its hit label and rank, and neighbours carry `neighbor_of` / `side` plus full text and citation.

12 questions × 3 runs:

| Condition | evidence cited | key facts | searches (mean, max) | input tokens median / mean | pages per search | cost USD (36 runs) | 2-part answered after 1 search |
|---|---|---|---|---|---|---|---|
| vector k=3 | **0.95** | **0.94** | 2.1, 9 | 3,681 / 5,557 | 3.0 | **0.082** | 4/21 |
| neighbors k=3 | 0.86 | 0.85 | 1.8, 11 | 3,614 / 12,421 | 7.3 | 0.102 | 13/21 |
| vector k=5 | 0.92 | 0.89 | 2.0, 9 | 2,744 / 8,661 | 5.0 | 0.093 | 7/21 |
| neighbors k=5 | 0.86 | 0.86 | 1.5, 8 | 4,646 / 11,544 | 11.3 | 0.102 | 17/21 |

- Gained: same-lecture questions. On M3, p.34 brought p.35, so it took 1 search instead of 2.7 and 3,467 tokens instead of 6,402. On M1, p.39 brought p.40 (cited 3/3).
- Noise: single-fact questions were already 1.00 and their median tokens doubled (1,710 → 3,513).
- Why it lost overall: the bigger first result makes the agent stop searching. X1 fell from 0.83 to 0.50, with one search in 9/9 neighbour runs, because six Lecture 2 pages look like a full answer, so Lecture 1 never gets searched.
- N1 shows the other risk: the agent's query `95 of 100 test questions` hits the wrong lecture, the neighbours of a wrong hit are also wrong, and one run used 183,118 tokens.
- Per search, neighbours do add evidence (264 vs 234 of 358 groups over the 194 real queries), but plain k=5 gets 259 with fewer pages. It's roughly the same trade as raising k. I wouldn't make it the default.

### Advanced: hub retriever

Design: vector top 3 as seeds. (1) A seed that's an overview, agenda or summary page adds its 2 most query-similar detail pages from `elaborates.json`, which I wrote by hand from the page text (20 overview pages → 95 links, keyed by page ID so it works for both languages). (2) If the question names a lecture with no page in the results, add the best 2 pages inside that lecture. Max 8 pages, and every page says why it was returned (`via`, shown in `--trace`). I didn't route through the stock graph's terms because they're too uneven: `ai-agent` is on 54 pages, and there's no `benchmark` term at all.

11 questions × 3 runs (M1–M3, X1, O1, A1–A5, N1):

| Method | evidence cited | evidence retrieved | key facts | searches (mean, max) | input tokens median / mean | time s median | cost USD (33 runs) |
|---|---|---|---|---|---|---|---|
| vector k=3 | 0.83 | 0.83 | 0.88 | 2.5, 9 | 4,190 / 7,062 | 4.1 | 0.093 |
| vector k=5 (default) | 0.82 | 0.82 | 0.83 | 2.3, 9 | 5,833 / 10,090 | 4.0 | 0.101 |
| stock `--graph` | 0.68 | 0.78 | **0.90** | 1.4, 4 | 4,763 / 7,773 | 3.0 | 0.092 |
| **hub** | **0.92** | **0.93** | 0.88 | 1.5, 4 | **2,580 / 4,149** | **3.0** | **0.070** |

Chart: `results/adv_tradeoff.png`

- Best example (N1): the agent's query `95 of 100 test questions` seeded three wrong Lecture 2 pages. Lecture 01 is named but missing, so hub added L01 p.41/40, and the agent's next search got p.42. It was correct 3/3 with 5,227 median tokens, against 30,134 for vector k=3 (0.67 evidence). X1 worked the same way: 1.00 with one search.
- Overview links worked as intended: on A4, seed L02 p.3 pulled in whichever of p.13/14/15 weren't already seeds, giving 1.00 at 2,304 tokens vs 0.67 at 6,334.
- Added pages were useful far more often: 22 of the 68 pages hub added were cited as evidence (32%), compared with 20 of 312 for the stock graph (6%).
- I'd adopt it, with vector k=3 as the fallback. The link file is 20 entries for 3 lectures, and the named-lecture rule is free.

### Limitations

- I wrote and labelled all 17 questions myself, and the hard ones (X1, N1, A1–A5) were chosen because I'd seen them fail, so the hub gain is measured on the failures it was built for.
- 3 runs per setting, so differences of about ±0.05 are noise. The X1, N1 and neighbour search-count effects held in every run.
- Hub still fails A5 (0.50). The 2-per-seed cap picked Lecture 3 detail pages, and an off-topic Lecture 2 seed counted as covering Lecture 2, so the missing pages never came in.
- Key facts are regex checks. I read every answer below 1.0 and every cited page outside my labels. `[cost]` excludes embeddings, which came to under $0.02.

### Questions

- Could the tool return only the `citation` label, or the instruction be stricter? 69% of citations ignore it.
- Is re-embedding the English text planned? My numbers say it isn't needed.

Total API spend: about $1.04 for generation plus under $0.02 for embeddings.
