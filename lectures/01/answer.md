# Lecture 01 Answers

## Exercises

- Model's answer to the course-specific question (the 3 homework levels; a summary is fine):
  `gemini-3.5-flash-lite` confidently answered "Level 1 Basic/Foundations, Level 2 Intermediate/Application, Level 3 Advanced/Research & Challenge", and added that they "may also be referred to as Core, Practice, and Mastery".
- What you noticed when comparing it with the correct meaning in the glossary:
  The glossary (`homework-levels`) says the levels are Basic (review lecture content), Implementation (write your own code) and Advanced (research and experimentation), that completing any one level completes the homework, and that it is not graded as a rule. The model got the general "three levels of difficulty" idea right but invented the names and descriptions, and it said nothing about "any one level is enough". It never said "I don't know". A second run gave a much shorter, different answer (45 output tokens instead of 215), so the answers are inconsistent as well as made up.
- Token counts you displayed (input / output):
  "What is LoRA?" gave 6 / 618. "What are the 3 homework levels in the AIE2026 course?" gave 18 / 215 (both on `gemini-3.5-flash-lite`).

## Homework

- Level attempted: Advanced
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
  - Question: does thinking-token usage count against the free-tier token-per-minute limit in the same way as output tokens?c