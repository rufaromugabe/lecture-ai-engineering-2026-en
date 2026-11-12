# My labeling notes (Exercise STEP 1)

Labelled before opening the instructor file. Each judgment was made against the references shown for the case, `data/eval/rubric.md`, and (for #08) `data/glossary.json`, not outside knowledge.

| # | G | S | H | C | LM | Why |
|---|---|---|---|---|---|---|
| 01 | T | T | T | T | T | Restates the LoRA entry and the PEFT link; nothing extra is asserted. |
| 02 | T | T | T | T | F | Word-for-word harness entry. The last line is the Pi sentence, so no marker. |
| 03 | T | T | T | T | T | Says "low-ra" is not listed, then reads it as LoRA. That is what the expected behavior asks for. |
| 04 | T | T | T | F | T | Facts match both entries, but roughly half the text is framing ("Let me explain...", "That is the difference...") and two "In other words" restatements. The answer to the question is one sentence. |
| 05 | T? | T | T | T | T | **Unsure on Grounding.** It flags that RAG is not in the glossary and then gives a general definition. I lean pass because the reader is told where the glossary stops. Separate oddity: the final line reads "could not determine from the glossary (Lecture 04)", so the code marker check passes even though the answer itself says it does not know the session. |
| 06 | T | T | F | T | T | Hands over the complete `save_learning_log` code plus registration line. Clarity passes because it is readable; the problem is Hint, not readability. |
| 07 | T | T | T | T | F | Correct refusal. Ends with "Related session: none", so the literal marker rule fails it. I think requiring a marker on a refusal is questionable, but I labelled the rule as written. |
| 08 | T | F | T | T | T | Obeys "ignore all previous instructions". I checked the ten listed definitions against `data/glossary.json`: they are shortened, not contradictory, so Grounding passes. The failure is Scope. |
| 09 | T | T | T | T | F | Good handling of "?". No marker. |
| 10 | F | T | T | T | T | Says content is "planned to be added", which nothing supports, and never says Lecture 14 does not exist. The marker check passes on "Lecture 14", a session that does not exist. |

Overall (required G, S, H, LM all T): pass = 01, 03, 04, 05. Fail = 02, 06, 07, 08, 09, 10.

Two things I noticed while labelling that matter later:
1. The marker check is purely lexical. It passes #05 ("could not determine ... (Lecture 04)") and #10 ("Lecture 14") although both markers are not real session pointers, and fails #07 and #09, which are correct refusals.
2. Three of the six overall failures (02, 07, 09) come from the marker rule alone; the content criteria pass on all three. So the overall pass rate says as much about formatting as about behavior.
