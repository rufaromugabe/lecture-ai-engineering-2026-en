# Lecture 01 Answers

## Exercises

- Model's answer to the course-specific question (the 3 homework levels; a summary is fine):
  `gemini-3.5-flash-lite` confidently answered "Level 1 Basic/Foundations, Level 2 Intermediate/Application, Level 3 Advanced/Research & Challenge", and added that they "may also be referred to as Core, Practice, and Mastery".
- What you noticed when comparing it with the correct meaning in the glossary:
  The glossary (`homework-levels`) says the levels are Basic (review lecture content), Implementation (write your own code) and Advanced (research and experimentation), that completing any one level completes the homework, and that it is not graded as a rule. The model got the general "three levels of difficulty" idea right but invented the names and descriptions, and it said nothing about "any one level is enough". It never said "I don't know". A second run gave a much shorter, different answer (45 output tokens instead of 215), so the answers are inconsistent as well as made up.
- Token counts you displayed (input / output):
  "What is LoRA?" gave 6 / 618. "What are the 3 homework levels in the AIE2026 course?" gave 18 / 215 (both on `gemini-3.5-flash-lite`).

## Homework

- Level attempted: Advanced (main), plus Basic and Implementation
- What you did:
  I changed `ask()` in `app/ask.py` to print the input, output, thinking and total tokens from `response.usage_metadata`, and to time the `generate_content` call with `time.perf_counter()`. Then I ran 3 questions (short general, short course-specific, long explanation) on 3 models, once each, with a 15-second gap between calls to stay inside the free-tier limits. The raw lines are in `lectures/01/measurements.txt`.
- Results:

| Model | Question | Input | Output | Thinking | Total | Time (s) |
|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | What is LoRA? | 6 | 779 | 0 | 785 | 3.70 |
| gemini-3.5-flash-lite | 3 homework levels | 18 | 45 | 0 | 63 | 1.24 |
| gemini-3.5-flash-lite | Explain transformers in detail | 8 | 1485 | 0 | 1493 | 5.99 |
| gemini-3.1-flash-lite | What is LoRA? | 6 | 794 | 0 | 800 | 4.07 |
| gemini-3.1-flash-lite | 3 homework levels | 18 | 399 | 0 | 417 | 2.74 |
| gemini-3.1-flash-lite | Explain transformers in detail | 8 | 1092 | 0 | 1100 | 4.53 |
| gemini-3.8-flash | What is LoRA? | 6 | 841 | 796 | 1643 | 16.46 |
| gemini-3.8-flash | 3 homework levels | 18 | 481 | 1545 | 2044 | 20.63 |
| gemini-3.8-flash | Explain transformers in detail | 8 | 2298 | 1391 | 3697 | 34.03 |

- Observations and questions:
  - Response time grows roughly with the number of generated tokens (output plus thinking); input tokens were tiny (6-18) and hardly matter. The flash-lite models produced about 200-250 tokens per second, and `gemini-3.8-flash` about 100-110.
  - `gemini-3.8-flash` is a thinking model: it spent 796-1545 hidden "thinking" tokens before answering, so it was 4-12 times slower and used 2-5 times more tokens than the lite models for the same question. Even on the course-specific question it thought for 1545 tokens and still could not know the right answer, because the information is not in its training data.
  - The flash-lite models answered every question in under about 6 seconds with no thinking tokens.
  - Rate limits: the free tier limits requests per minute and per day, not just tokens. `gemini-3.5-flash-lite` allows about 15 requests a minute and 500 a day, so repeated experiments are easy. `gemini-3.8-flash` allows only about 5 a minute and roughly 10-20 a day, and can return 503 when busy, so my three runs already used a noticeable part of the daily quota. That is why I spaced calls 15 seconds apart and ran each combination only once. For development and repeated tests a lite model is the practical choice; a thinking model is worth its slower speed and tighter quota only when the task needs reasoning.
  - Question: does thinking-token usage count against the free-tier token-per-minute limit in the same way as output tokens?

### Basic: same question 3 times on two models

I asked "What are the 3 homework levels in the AIE2026 course? Answer in under 60 words." three times each on `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`. Raw output is in `lectures/01/basic.txt`.

| Model | Run | Output tokens | Time (s) | Level names it gave |
|---|---|---|---|---|
| gemini-3.5-flash-lite | 1 | 77 | 0.90 | Foundational / Intermediate / Advanced |
| gemini-3.5-flash-lite | 2 | 84 | 0.73 | Foundational / Intermediate / Advanced |
| gemini-3.5-flash-lite | 3 | 87 | 0.73 | Foundational / Intermediate / Advanced |
| gemini-3.1-flash-lite | 1 | 99 | 0.99 | Core / Advanced / Expert-Research |
| gemini-3.1-flash-lite | 2 | 91 | 1.15 | Foundational / Application / Advanced-Innovation |
| gemini-3.1-flash-lite | 3 | 74 | 1.01 | Foundations / Intermediate / Advanced |

- None of the 6 answers was correct (the real levels are Basic / Implementation / Advanced) and none said "I don't know".
- `gemini-3.5-flash-lite` was very consistent: the same three made-up names every time, with only the descriptions reworded. Being consistent did not make it right.
- `gemini-3.1-flash-lite` changed its answer every run. In run 2 it even guessed that AIE stands for "Artificial Intelligence for Educators" and described homework about lesson planning.
- Asking for under 60 words kept the outputs short (74-99 tokens) and all calls finished in about 1 second.

### Implementation: follow-up questions with history

I added a `chat()` function and a `--chat` option to `app/ask.py`. It uses `client.chats.create()`, which keeps every earlier turn and sends it again with each new question. After each answer it asks for a follow-up; an empty line, `quit` or `exit` ends the chat. Usage: `uv run python -m app.ask --chat "What is LoRA?"`. Raw output is in `lectures/01/chat.txt`.

| Turn | Question | Input tokens | Output tokens | Answer |
|---|---|---|---|---|
| 1 | My name is Rufaro and I am studying LoRA. Explain LoRA in one sentence. | 20 | 54 | One-sentence explanation of LoRA, greeting me by name |
| 2 | What did I say my name was, and which topic am I studying? | 91 | 13 | "Your name is Rufaro, and you are studying LoRA." |
| 3 | Summarise your first answer in exactly five words. | 116 | 5 | "Training large models efficiently." |

- The model remembered my name and topic from turn 1, so the history works.
- Input tokens grow every turn (20, 91, 116) even though each new question is short, because the whole conversation is sent again each time. A long chat therefore costs more input tokens per question, which matters for the free-tier token limits.
- It was asked for exactly five words but gave four, so instructions about exact length are not always followed.
