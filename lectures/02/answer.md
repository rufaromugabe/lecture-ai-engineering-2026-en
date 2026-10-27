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

- Level attempted: Basic
- Settings or data changed: `lora_r` 16 → 4 (everything else identical, including `lora_alpha` 32, lr, epochs and seed). Restarted the session and ran from the top. Results are in `result.json` (r=16) and `result_lora_r4.json` (r=4).
- Results (comparison tables or numbers):

| Setting | Trainable params | Final loss (step 40) | Training time | format before → after | content before → after | Regressed |
|---|---|---|---|---|---|---|
| `lora_r` = 16 (original) | 6,389,760 (0.842%) | 0.0145 | 204 s | 0.952 → 1.000 | 0.381 → 0.952 | none |
| `lora_r` = 4 | 1,597,440 (0.212%) | 0.0141 | 197 s | 0.952 → 1.000 | 0.381 → 0.952 | none |

  Loss curve for r=4: 1.672 (step 10) → 0.059 (step 20) → 0.017 (step 30) → 0.014 (step 40). The remaining failure (office hours appointment, asserted without evidence) and the section 6 knowledge results were identical for both ranks; only the wording of a few outputs differed slightly.
- Discussion: cutting the rank by 4x cut the trainable parameters by 4x (and the adapter size with it) with no loss in either metric and only a small speed gain, because on a 0.8B model the cost is dominated by the frozen base model's forward/backward pass, not the adapter. For a narrow task like a fixed JSON format with 14 examples, a low rank is enough; a higher rank adds capacity that this task does not need. Both runs reached near-zero loss on 14 examples, which is a sign of memorisation, so the real test is the held-out questions, and there both ranks make the same mistake.
- Discussion of when fine-tuning is and is not suitable: fine-tuning is suitable for teaching **how** to answer: a strict output format (like this JSON), a tone, or a fixed refusal phrase, where there are many examples of the desired behaviour and the rules do not change often. It is not suitable for teaching **what** is true, especially facts that change (deadlines, instructor names, schedules) or for guaranteeing that a model says "I don't know" on unseen questions: my run shows the trained model still asserts answers for near-miss questions. For facts, retrieval (search the FAQ or documents and quote them) plus a rule such as "set `needs_review` when nothing was retrieved" is more reliable and easier to update; fine-tuning can then be added on top to make the output format consistent.
