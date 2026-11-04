# Lecture 03 Answers

## Exercises

- **Bare LLM (Lecture 01) vs agent answers:** I asked "What are the 3 homework levels in the AIE2026 course?". `app.ask` made up "Foundations / Intermediate / Advanced" and even gave alternative names. The agent gave the correct Basic / Implementation / Advanced and cited Lecture 01, because it read the course data first. (`exercise/01_ask_vs_agent.txt`)
- **Tool calls shown by `--trace`:** that question: `get_lecture_summary({'lecture': 1})` → `search_glossary({'query': 'homework'})`. "Difference between LoRA and QLoRA": `search_glossary({'query': 'LoRA'})` and `search_glossary({'query': 'QLoRA'})`, called in parallel.
- **Number of LLM calls (`requests`):** 2 for LoRA/QLoRA (one turn with the tool calls, one turn to answer) and 3 for the homework question (the two tools were called one after the other).
- **Tool added and its docstring:** `make_quiz(lecture: int)` in `app/tools.py`: "Create one review question from the glossary terms of the specified session... Use when the learner asks for a quiz, a review question, or a check question about a session... Returns JSON with "question" and "answer". Show the question to the learner and keep the answer hidden until they reply." `--list-tools` shows 3 tools. "Give me a review question on Lecture 02" → `make_quiz({'lecture': 2})`, requests=2. The answer was not revealed. A lecture with no terms returns a message listing the valid sessions. (`exercise/02_make_quiz.txt`)

## Homework

**Summary (5 lines)**
1. Basic: 7 configs (baseline + 5 one-change variants + 1 combined) × 4 fixed questions × 2 runs = 56 traced runs.
2. The biggest effect came from the *grounding* lines: dropping them made the absent term (RLHF) cost 7–8 requests and ~8–8.8k input tokens per run, vs 2 requests / 893 tokens at baseline.
3. Implementation: `save_learning_log` with `requires_approval=True` and a CLI y/N loop. Deny writes nothing, approve writes `learning_log/`, and a second approve appends. 22 tests pass.
4. Advanced (a): the ADK agent made exactly the same tool calls as Pydantic AI on all 4 questions in both runs, but answered absent terms more briefly.
5. Advanced (b): Pi builds its prompt from per-tool snippets/guidelines. It has no grounding rule and no approval step, which I confirmed by running it in a sandbox.

- **Level attempted:** Advanced (Basic, Implementation, Advanced (a) and (b) all done)

### What I did

- **Basic** (`homework/basic/`). `run_variants.py` builds each variant in memory: one line of `INSTRUCTIONS` or one docstring sentence, swapped with a `functools.wraps` copy, so the repo files stay untouched. Model: gemini-3.5-flash-lite. Questions: Q1 LoRA vs QLoRA; Q2 PEFT, LoRA, rank, quantization (several terms); Q3 RLHF (not in the glossary); Q4 Lecture 03 + "harness".
  - V0 baseline
  - V1 delete "Always check the glossary with search_glossary…"
  - V2 docstring "Put only one term" → "Put several terms at once"
  - V3 "End with (Lecture NN)" → "End with one short review question"
  - V4 delete "If something is absent… say 'It is not in the glossary'"
  - V5 delete docstring sentence "Use before answering about AI engineering terms…"
  - V6 = V1+V5 (two changes, labelled as such: "no search rule anywhere")
- **Implementation** (`app/tools.py`, `app/agent.py`, `tests/test_learning_log.py`, `homework/implementation/`).
  - `save_learning_log(title, content)` writes `learning_log/YYYY-MM-DD_<slug>.md` and appends, never overwrites.
  - Edge cases: empty title/content and content over 5000 chars are rejected. Titles are slugged (`../../etc` stays inside `learning_log/`, and the resolved path is checked).
  - `output_type=[str, DeferredToolRequests]`. `run_with_approvals()` loops: it prints the args, asks `Save this? [y/N]`, and sends `DeferredToolResults` (True or `ToolDenied(...)`). EOF means deny.
  - `--trace` now also prints usage from before the pause.
  - I also ported the upstream fix that lets `tests/test_agent.py` tolerate approval tools.
- **Advanced (a)** (`adk_agent/glossary_agent/`, `homework/advanced_a/`). Google ADK 2.13 `Agent` with the same `INSTRUCTIONS` and the same three plain functions. I ran the real `adk run adk_agent/glossary_agent` (transcript) and `adk_trace.py`, which uses a fresh session per question, ×2 runs, to compare with V0.
- **Advanced (b)** (`homework/advanced_b/`). I read Pi's `system-prompt.ts` and the tool files it pulls snippets from. I installed pi 1.5.0 into `/tmp/pi-sandbox` and ran one task there with its own HOME. The prompt it really sent is in `pi_run_trace.txt`.

### Results

**Basic: per-variant totals over 8 runs** (all 56 rows: `basic/table_all_runs.md`; raw traces: `basic/traces/`)

| Variant | tool calls Q1/Q2/Q3/Q4 (run1,run2) | requests | input tokens | exact "not in the glossary" on Q3 | ends with Lecture NN | ends with "?" |
|---|---|---|---|---|---|---|
| V0 baseline | 2,2 / 4,4 / 1,1 / 2,2 | 16 | 10568 | 2/2 | 7/8 | 0/8 |
| V1 no "Always check" | 2,2 / 4,4 / **6,6** / 2,2 | 26 | 24510 | 2/2 | 8/8 | 0/8 |
| V2 several terms per query | **1,1 / 2,2** / 1,1 / 2,2 | 18 | 10820 | 2/2 | 6/8 | 0/8 |
| V3 end with review question | 2,2 / 4,4 / 1,1 / 2,2 | 16 | 10568 | 2/2 | **0/8** | **7/8** |
| V4 no "not in glossary" rule | 2,2 / 4,4 / **7,7** / 2,2 | 28 | 25872 | **0/2** | 7/8 | 0/8 |
| V5 no "Use before answering" | 2,2 / 4,4 / 1,1 / 2,2 | 16 | 10216 | 2/2 | 5/8 | 0/8 |
| V6 V1+V5 | 2,2 / 3,4 / 1,6 / 2,2 | 23 | 18977 | 1/2 | 7/8 | 0/8 |

Trace excerpts:
```
V0 Q3:  search_glossary({'query': 'RLHF'})                         requests=2, input=893
V1 Q3:  search_glossary RLHF → get_lecture_summary 12, 5, 3, 2, 1  requests=7, input=8091
V4 Q3:  RLHF → 'Reinforcement Learning from Human Feedback' → summaries 7,5,3,2,1  requests=8, input=8817
V2 Q1:  search_glossary({'query': 'LoRA QLoRA'})                   1 call instead of 2
V2 Q2:  'PEFT LoRA rank quantization' → only 3 hits (MAX_RESULTS=3) → second search, requests=3
```

**Implementation** (`homework/implementation/`)

| Trace | Approval | Result | requests (before pause + after) |
|---|---|---|---|
| 1 deny | n | `ToolDenied` returned; `ls learning_log/` → does not exist | 2 + 1 |
| 2 approve | y | `Saved learning_log/2026-11-05_lora-vs-qlora.md` | 2 + 1 |
| 3 approve again | y | `Appended to learning_log/2026-11-05_lora-vs-qlora.md` | 2 + 1 |
| 4 no save asked | none | only `search_glossary`, no approval prompt | 2 |

```
[approval needed] save_learning_log
  title: LoRA vs QLoRA
Save this? [y/N] [approval] denied
[tool return] save_learning_log -> The user declined to save this learning log. Nothing was written; do not retry unless asked.
```
`pytest`: 22 passed (`pytest_output.txt`). The tests use TestModel only, with no API calls.

**Advanced (a): ADK vs Pydantic AI** (`advanced_a/adk_traces.txt`, `adk_run_transcript.txt`)

| | Pydantic AI V0 | ADK |
|---|---|---|
| Tool calls Q1–Q4, both runs | LoRA,QLoRA / PEFT,LoRA,rank,quantization / RLHF / summary(3),harness | identical |
| LLM calls per question | 2 | 2 (model responses) |
| Q3 (absent term) | "It is not in the glossary" + a short hint + Lecture line (1 of 2 runs wrote a wrong "Lecture 06") | "It is not in the glossary." only, no Lecture line |
| Tool return seen by model | raw string/JSON | wrapped as `{'result': ...}` |
| Code | `tool_plain` registration, model passed at run time, TestModel, `--trace`, approvals | plain functions in `tools=[...]`, model named in `Agent`, `adk run`/`adk web` UI |
| Session | single-shot CLI | `adk run` keeps one session across questions |

**Advanced (b): Pi** (`advanced_b/comparison.md`). Pi's prompt is assembled from sections (`preamble`, `<tools>`, `<rules>`, `<docs>`, `<project_context>`, `<skills>`, `<cwd>`). Each tool contributes its own snippet and guidelines, and only changed sections are re-sent. In the sandbox run, pi called `write` then `bash python3 hello.py` with no confirmation: 3 requests, 1312 input tokens on the first.

### Observations and questions

- The tool docstring alone is enough to keep searching. V1 and V5 each remove one "search first" sentence and still search on Q1/Q2/Q4. Even V6 (both removed) still searched; it only skipped one call on Q2 in run 1. Redundant guidance in two places made the agent robust, which matches Pi's choice of keeping rules with tools.
- Grounding rules also limit *cost*. Without them, an absent term set off a sweep of `get_lecture_summary` over sessions that don't exist (4, 7, 12), about 9× the input tokens. A rule like "If a search returns nothing, say so and stop" would also cap the loop.
- Rules can conflict. "End with (Lecture NN)" made the baseline invent "Lecture 06" for RLHF once (V0 Q3 run 2). V3's review question replaced the lecture reference entirely (0/8), so the two goals need separate wording.
- V2 shows the tool interface and the instructions need to match. A multi-term query saves a call, but `MAX_RESULTS=3` silently cut results, so the model had to search again.
- Runs were almost deterministic: same calls and same token counts in run 1 and run 2 for most cells. Variance showed up only on the absent term and in V6. 2 runs is too few to claim rates.
- Question: for approval, is it better to show the user the exact `content` (as I do) or a diff against the existing file when appending?
- Question: should "not found" be a tool result (structured), so the harness, not the prompt, decides to stop?
