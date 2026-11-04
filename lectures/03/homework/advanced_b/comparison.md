# Advanced (b): Pi's system prompt vs. our INSTRUCTIONS

Source read: `packages/coding-agent/src/core/system-prompt.ts` in github.com/earendil-works/pi,
commit 4bb837c (2026-11-05 00:15 CAT), 228 lines. Pi 1.5.0 was also installed and run once, in a
throwaway directory only (`/tmp/pi-sandbox`, own HOME, `--no-context-files --no-skills --no-extensions --no-mcp`).
The prompt it really sent is in `pi_run_trace.txt`.

## How Pi builds its prompt (from the code)

- The prompt is **assembled at runtime from ordered sections**, not a fixed string:
  `preamble` (untagged), then `<tools>`, `<rules>`, `<docs>`, optional `<addendum>`, `<project_context>`
  (AGENTS.md / CLAUDE.md files), `<skills>`, `<cwd>`, plus any extension sections.
- **Tools describe themselves.** Each tool file exports a one-line `snippet` and `guidelines`
  (e.g. read: "Use read to examine files instead of cat or sed."). `buildRules()` gathers the guidelines
  of the tools that are switched on, removes duplicates, and adds two fixed rules
  ("Be concise in your responses", "Show file paths clearly when working with files").
- **Rules depend on the tool set.** "Use bash for file operations like ls, rg, find" is added only when bash
  is on and grep/find/ls are not. Hidden tools are left out of both lists.
- Sections are tagged so `diffSystemPromptSections()` can send **only the sections that changed** later
  in a session. `--system-prompt` replaces the preamble+tools+rules+docs; `forceSystemPrompt` replaces everything.
- Measured: the default prompt plus tool schemas came to 1,312 input tokens on the first request.

## Comparison

| Aspect | Pi | Our INSTRUCTIONS (app/agent.py) |
|---|---|---|
| Form | Built by code from sections, XML-tagged | One fixed 6-line string |
| Role line | "coding assistant running inside pi, a coding agent harness" | "learning support agent for ... AIE2026" |
| Tool guidance | Lives next to each tool (snippet + guidelines), merged only for tools that are on | Tool names hard-coded in the rules ("Always check the glossary with search_glossary") |
| Grounding rule | None for facts. It is about *how* to use tools (read over cat, edit vs write) | Strong: check the glossary first, say "It is not in the glossary" |
| Output format | "Be concise", show file paths | End with "(Lecture NN)" |
| Behaviour limits | None in the prompt. Tools run without confirmation | Pedagogical: hints, not homework answers |
| Context | cwd, project AGENTS.md, skills, docs paths | None (the glossary is reached only via tools) |
| Safety / approval | Not in the prompt at all | Not in the prompt either; our approval for `save_learning_log` lives in code (`requires_approval`) |

## What I take from it

1. Pi puts tool advice in the tool, and our Basic homework agrees: removing the "Always check the glossary"
   rule (V1) did not stop searching on Q1/Q2/Q4, because the docstring line "Use before answering..."
   still said it. Rules that name a tool are better kept with that tool, as Pi does.
2. Pi has no "admit you don't know" rule, and that's fine for a coding agent: it can check facts with
   `read`/`bash`. Our agent can't, so the grounding line matters. Removing it (V4) made the model explain
   RLHF from its own knowledge after a 7-call sweep of lecture summaries.
3. Pi's rule list is short and practical. Ours has a format rule ("End with Lecture NN") that clashed with
   absent terms: the baseline once wrote "Lecture 06" for RLHF (V0 Q3 run 2). Pi avoids rules that force
   content.
4. Pi trusts the tools completely. In the run it called `write` and then `bash python3 hello.py` with no
   confirmation (3 requests: 1312/1444/1488 input tokens). Making changes only after approval is a
   harness feature in our code; Pi's prompt does not cover it. That is why I ran it only in a sandbox.

## Run (excerpt from pi_run_trace.txt)

```
=== ASSISTANT tool call: write({"path": "hello.py", "content": "print('hello from pi')\n"})
=== TOOL RESULT write: 'Successfully wrote to hello.py'
=== ASSISTANT tool call: bash({"timeout": null, "command": "python3 hello.py"})
=== TOOL RESULT bash: 'hello from pi\n'
```
