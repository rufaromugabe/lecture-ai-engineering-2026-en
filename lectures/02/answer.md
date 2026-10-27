# Lecture 02 Answers

## Exercises

- Model and settings used (from `config` in `result.json`): `Qwen/Qwen3.5-0.8B` (revision 2fc0636), LoRA without quantization, seed 42, 20 epochs (40 steps), lr 2e-4, warmup 6, `lora_r` 16, `lora_alpha` 32, max_seq_len 512, greedy decoding (max_new_tokens 96). Colab T4 GPU; transformers 5.18.0, peft 0.21.1, trl 1.14.2, torch 2.11.0.
- Did you run training yourself (`executed_training_myself`): Yes (ran the whole notebook, sections 0–7, twice on a Colab T4)
- Before training: `format_rate` = 0.952 (20/21) / `content_rate` = 0.381 (8/21)
- After training: `format_rate` = 1.000 (21/21) / `content_rate` = 0.952 (20/21)
- Training: trainable params 6,389,760 (0.84%), final loss 0.0145 at step 40, 204 s.
- Questions that regressed: none (the `regressed` list is empty).
- Failures remaining after training and their types: one. "Do office hours require an appointment?" (not in the FAQ, gold `needs_review: true`) got `{"answer": "Questions are welcome during office hours every Tuesday from 17:00 to 18:00.", "needs_review": false}`. This is an **assertion without evidence**: the model applied a nearby FAQ item (office hours) to a question the FAQ does not answer.
- Before training, the failures were different: one broken format (the model dumped the whole FAQ into a long answer for "Where should I submit my work?"), seven **evasions** (correct FAQ answer but `needs_review: true` on covered questions), and five **assertions without evidence** (e.g. "Will lecture recordings be made available?" → "No", `needs_review: false`).
- Results of knowledge questions (section 6; classification before → after training):

| Question | In FAQ | Before | After |
|---|---|---|---|
| When is the final assignment deadline for this course? | No | asserted ("September 30 at 23:59") | asserted ("The assignment deadline is September 30 at 23:59 (Japan time).") |
| What is the instructor's name? | No | needs_review (answer "None") | needs_review ("This FAQ does not contain that information. Confirmation ... is needed.") |
| What is the topic of the next lecture? | No | needs_review | needs_review (same fixed confirmation sentence) |
| When is the assignment deadline? (control) | Yes | asserted | asserted |

  Observation: training made the confirmation wording uniform, but it did not fix the judgement. The "final assignment deadline" question is not in the FAQ, yet it is close in wording to the "assignment deadline" item, so the model confidently reuses that answer before and after training.
- What changed and what stayed the same with training: the **format** changed a lot. Every output became one valid JSON line, answers use the FAQ's exact wording, and the "not in the FAQ" reply became a fixed sentence. Content accuracy rose from 38% to 95%, mostly because the model stopped setting `needs_review: true` on questions it had answered correctly. What **stayed the same** is the underlying judgement on unseen questions: when a question is semantically close to an FAQ item, the model still asserts that item's answer instead of asking for confirmation (office hours appointment, final assignment deadline). Training taught the format and the specific training cases, not a reliable sense of "I don't know".

## Homework

- Level attempted: **Basic, Implementation and Advanced** (all three; highest level: Advanced)

### Basic: change `lora_r` and retrain

- Settings or data changed: `lora_r` 16 → 4 (everything else identical, including `lora_alpha` 32, lr, epochs and seed). Restarted the session and ran from the top. Results are in `result.json` (r=16) and `result_lora_r4.json` (r=4).
- Results (comparison tables or numbers):

| Setting | Trainable params | Final loss (step 40) | Training time | format before → after | content before → after | Regressed |
|---|---|---|---|---|---|---|
| `lora_r` = 16 (original) | 6,389,760 (0.842%) | 0.0145 | 204 s | 0.952 → 1.000 | 0.381 → 0.952 | none |
| `lora_r` = 4 | 1,597,440 (0.212%) | 0.0141 | 197 s | 0.952 → 1.000 | 0.381 → 0.952 | none |

  Loss curve for r=4: 1.672 (step 10) → 0.059 (step 20) → 0.017 (step 30) → 0.014 (step 40). The remaining failure (office hours appointment, asserted without evidence) and the section 6 knowledge results were identical for both ranks; only the wording of a few outputs differed slightly.
- Discussion: cutting the rank by 4x cut the trainable parameters by 4x (and the adapter size with it) with no loss in either metric and only a small speed gain, because on a 0.8B model the cost is dominated by the frozen base model's forward/backward pass, not the adapter. For a narrow task like a fixed JSON format with 14 examples, a low rank is enough; a higher rank adds capacity that this task does not need. Both runs reached near-zero loss on 14 examples, which is a sign of memorisation, so the real test is the held-out questions, and there both ranks make the same mistake.

### Implementation: own topic (Kage app FAQ)

- Settings or data changed: replaced `FAQ`, `GROUNDED`, `UNGROUNDED` (and the test-only extras and section 6 knowledge questions) with an FAQ about **Kage**, my own desktop app that reads Zoom live captions and speaks them in English to listeners. Five items: captions requirement, listener link, offline fallback voice, leader/standby failover, how it joins the meeting. The JSON `{"answer", "needs_review"}` format, the `needs_review` design, the split rules (14 train / 7 valid / 21 test), and all `CONFIG` values (r=16, lr 2e-4, 20 epochs) are unchanged. The only prompt change is "course FAQ" to "FAQ questions about the Kage app", and the fixed confirmation sentence names "the Kage developer". Notebook: `implementation/lora_kage_faq.ipynb`; results: `implementation/result.json`, `eval_before.json`, `eval_after.json`.
- How I prepared questions "without evidence": every candidate was checked against the five FAQ sentences so that the FAQ really cannot answer it, then built in three deliberate kinds:
  1. **Off-FAQ product questions** (price, macOS, Microsoft Teams, source languages): obviously unanswerable, a sanity check.
  2. **Near-misses** that reuse FAQ vocabulary but ask something the FAQ does not say ("How many listeners can join at once?", "Does the listener page need a password?", "How big is the offline voice download?"). These are the hard cases, because a nearby FAQ sentence looks relevant.
  3. **Plausible features that do not exist in the FAQ** ("Does Kage record the meeting?", "Does Kage save a transcript?", "Can the host see that Kage is in the meeting?").
  Some of these have real answers outside the FAQ, which is the point: the model must flag them because *the FAQ* is silent, not because the fact is unknowable.
- Results:

| | format_rate | content_rate | grounded correct | ungrounded correct |
|---|---|---|---|---|
| Before training | 1.000 | 0.048 (1/21) | 1/15 | 0/6 |
| After training | 1.000 | 0.905 (19/21) | 15/15 | 4/6 |

  Training: trainable 0.84%, loss 2.268 (step 10), 0.136 (20), 0.018 (30), 0.012 (40), 232 s on a T4. Regressions: none.
  Before training the format was already perfect but the content was not: the model gave short fragments ("Kokoro", "The leader", "No") and set `needs_review: true` on 9 of the 15 questions that the FAQ answers (evasion), while asserting "No" to ungrounded questions such as the password and transcript ones (assertion without evidence).
  After training both remaining failures are **near-misses** (kind 2), answered with a neighbouring FAQ sentence and `needs_review: false`:
  - "How many listeners can join at once?" got the leader/standby sentence (shares "several"/"join").
  - "Does the listener page need a password?" got the listener-link sentence ("they do not need to install anything").
  Every kind 1 and kind 3 question was correctly flagged. Section 6: "Does Kage work with the Zoom web client?" moved from asserted to needs_review, the two clearly absent questions stayed needs_review, and the control stayed correctly asserted.
- Observation: with my own topic the picture from the exercise repeats. LoRA fixed the answer style completely (exact FAQ sentences, no more evasion on covered questions), but the questions it still gets wrong are precisely the ones that look most like an FAQ item. The model learned "match the closest FAQ sentence", not "check whether the FAQ actually answers this".

### Advanced: train on the course glossary and compare with glossary search

Files: `advanced/lora_glossary.ipynb` (notebook, data embedded so it runs in Colab without uploads), `advanced/glossary_sft.jsonl` (output of `scripts/make_sft_dataset.py`, unmodified script, sha256 `df11fef8…`), `advanced/eval_set.json` (my evaluation set with expected answers and a "why" note per question), `advanced/result_plain.json`, `advanced/result_augmented.json`, and per-question outputs `eval_before_*.json`, `eval_after_*.json`, `eval_search_*.json`.

- Data: 58 glossary terms × 2 templates = **116 records** in `messages` format, passed straight to `Dataset.from_list` and trained with the section 4 `SFTTrainer` (r 16, alpha 32, lr 2e-4, 3 epochs = 45 steps). Questions are plain user messages, the same format as training (no FAQ system prompt).
- Second variant (my addition, same settings): **augmented, 217 records** = the 116 + 85 alias questions ("What does {alias} mean?") + 16 abstention examples ("That term is not in the course glossary.") for 8 AI terms that are not in the glossary (DPO, KV cache, perplexity, BLEU, …). These 8 are training-only, none is used in evaluation. 84 steps. This tests whether training can also teach alias recall and "I don't know".
- Own evaluation set (35 questions, expected answer = the glossary definition plus 2–3 hand-picked distinctive keywords, e.g. `gemini-3.5-flash-lite` / `AIE_MODEL` for the default model):
  - **in glossary (12)**: the exact training templates ("What is LoRA?"). Measures memorisation.
  - **paraphrased (13)**: new wording or an alias ("What does HITL mean in agent design?", "Why would I get a 429 error from an LLM API?", "Explain quantisation of model weights." with British spelling).
  - **absent (10)**: real AI terms checked to be absent from every glossary term and alias (RAG, RLHF, vector database, embedding, beam search, knowledge distillation, Mixture of Experts, prompt injection, top-p, chain-of-thought). The correct behaviour is to say the term is not in the glossary. "Prompt injection" is a deliberate trap for search because it contains the glossary term "Prompt".
  - Metrics: keyword hit (all keywords present), token F1 against the glossary definition, and abstain vs assert for absent terms.
- Search mechanism compared: deterministic lookup over `glossary.json` (whole-word match on term, parenthesised parts and aliases, longest match wins, then a difflib fuzzy fallback at 0.88; otherwise "not in the glossary").

Results (Colab T4, `executed_training_myself: true`):

| | in glossary: keyword hit / F1 | paraphrased: keyword hit / F1 | absent: abstained | training |
|---|---|---|---|---|
| Before training (base model) | 0.00 / 0.18 | 0.00 / 0.20 | 0/10 | – |
| After, plain (116 records) | 0.08 / 0.41 | 0.00 / 0.33 | 0/10 | 45 steps, 102 s, final loss 1.02 |
| After, augmented (217 records) | **0.58 / 0.77** | 0.15 / 0.34 | 1/10 | 84 steps, 191 s, final loss 0.25 |
| Glossary search | **1.00 / 1.00** | **0.69 / 0.76** | **9/10** | none, ~25 ms per question |

Regressions: none in either variant (no question that passed before failed after).

What the outputs show:
- **Before training** the model answers from general knowledge in long Markdown, so nothing matches the course definitions. It even gets "Hallucination" wrong for this context ("a mental disorder characterized by the false perception…").
- **Plain training learned the style but not the facts.** After 3 epochs (each definition seen 6 times) answers became one or two sentences in the glossary's voice, and F1 doubled, but the content is often confabulated: "What is Default model?" gave "The model that Pydantic AI uses by default when calling tools…", and "What does HITL mean?" gave a made-up definition about an HTTP client. Loss was still 1.02, so the definitions were not memorised.
- **Augmented training memorised much more** (in-glossary keyword hit 0.58; "Default model" now correctly answers `gemini-3.5-flash-lite`, "Explain quantisation of model weights." is correct), but **paraphrases barely improved** (keyword hit 0.15). It still invents a definition for HITL, and "Why do LLMs make up facts?" does not map to the Hallucination entry.
- **Abstention did not generalise.** With 16 abstention examples, only 1 of 10 unseen absent terms (knowledge distillation) got "not in the glossary". The other nine got fluent, plausible definitions that look like course content, e.g. RAG: "…A representative example is Quiz…". Worse, the abstention leaked onto a covered question: "In LoRA, what does the r hyperparameter control?" now answers "That term is not in the course glossary." The model learned the sentence, not the rule.
- **Search** is exact on known terms and abstains correctly on 9/10 absent terms in about 25 ms with no GPU. Its failures are the reverse of the model's: it misses paraphrases without the term or an alias (the default-model and "make up facts" questions find nothing), and it is fooled by surface overlap ("prompt injection" returns the definition of Prompt, and "name collisions" returns the MCP entry).

Advantages and disadvantages of training the model, compared with search:
- Training **advantages**: answers in the glossary's tone and length with no retrieval step at inference, and some tolerance to wording (it does attempt every paraphrase instead of returning nothing).
- Training **disadvantages**: (1) it does not reliably store facts. Even with 217 records the model only reproduces about half of the definitions it was trained on, and less for paraphrases. (2) Its errors are **silent and confident**: wrong answers look exactly like right ones, and absent terms get invented course-style definitions, which is worse than no answer. (3) Teaching "I don't know" with a few examples does not generalise and can over-trigger on covered questions. (4) Any glossary change needs retraining, and there is no citation to show where an answer came from.
- Search **advantages**: exact, traceable to an entry, updates instantly when the glossary changes, abstains cleanly, nearly free. **Disadvantages**: brittle to rewording and to partial term matches.
- Conclusion: for a glossary, the facts should come from **search (or retrieval with embeddings), with the LLM writing the answer from the retrieved entry and abstaining when nothing is retrieved**, the same evidence-or-confirm design as the `needs_review` FAQ. Fine-tuning is worth adding only for the format or tone of the answer, not as the source of the definitions.

### Overall

- Discussion of when fine-tuning is and is not suitable: fine-tuning is suitable for teaching **how** to answer: a strict output format (like this JSON), a tone, or a fixed refusal phrase, where there are many examples of the desired behaviour and the rules do not change often. It is not suitable for teaching **what** is true, especially facts that change (deadlines, instructor names, schedules) or for guaranteeing that a model says "I don't know" on unseen questions: all three of my runs show the trained model still asserts answers for near-miss questions (office hours, the Kage listener questions, absent glossary terms). For facts, retrieval (search the FAQ or documents and quote them) plus a rule such as "set `needs_review` when nothing was retrieved" is more reliable and easier to update; fine-tuning can then be added on top to make the output format consistent.
