# Lecture 06 answers

## Exercises

<!-- Paste the original [tool call] lines. Leave unfinished steps blank. -->

- Tool name in STEP 1 — glossary_search_glossary (`app.agent` lists only `search_materials`; `app.mcp_agent` lists `glossary_search_glossary` with the same docstring and a `{"query": {"title": "Query", "type": "string"}}` schema, so the model sees the same thing either way, just with the `glossary_` prefix)
- STEP 2 [tool call] — `glossary_search_glossary({"query":"homework levels"})` → returned the "3 homework levels" entry, 2 model responses, 543 in / 159 out tokens
- STEP 3 [tool call] — `fetch_fetch({"url":"https://modelcontextprotocol.io/"})`
- STEP 4 [tool call] — `aws_aws___search_documentation({"search_phrase":"Amazon S3 versioning overview"})` → 7 tools visible (glossary 1, fetch 1, aws 5), 2 model responses, 5,539 input tokens
- Observations and questions —
  - Run setup: on 26 Nov my Gemini API key returned `402 prepayment credits depleted`. I ran the same model (`gemini-3.5-flash-lite`) through OpenRouter with a small local runner that only replaces `build_model()`. The repo code and `mcp_servers.json` are unchanged, and `--list-tools` and pytest need no key.
  - STEP 3 failed the first time, and that turned out to be a useful failure. My sandbox's DNS resolves every host to `198.18.0.1`, so fetch's private-IP guard refused the page: `[tool error] fetch_fetch -> Error executing tool fetch: Refused to fetch https://modelcontextprotocol.io/robots.txt: ... resolves to 198.18.0.1, which is not a public address`. The model then answered "unable to access that external website". This is the default described in "What to check before adding external tools". A rerun with `--allow-private-ips`, done locally and not committed, returned the page (it followed a 307 redirect to the 2026-07-28 intro doc) and gave a correct 3-line summary. In Codespaces the plain config should work.
  - Extra servers cost tokens on every question. With glossary only, STEP 2 used 543 input tokens. With all 9 tools, even "Lecture 99" (a one-line tool result) used 4,952, because every tool schema is sent with each request.
  - The instruction "end with Lecture N" makes the agent add "Lecture 1" even to S3 and MCP-website answers. Should that rule only apply when a course tool was used?
  - Tool names become `aws_aws___search_documentation` because the server already prefixes its own names. Prefixes stack.

## Homework

<!-- Complete one of the Basic, Implementation, or Advanced levels. -->

- Level attempted (Basic / Implementation / Advanced) — Advanced (Basic and Implementation done as well)
- What you did —
  - **Basic:** added `server.tool()(tools.get_lecture_summary)` under the TODO in `app/mcp_server.py`.
  - **Implementation:** wrote `make_quiz(lecture, num_questions=3)` with `@server.tool()` in `app/mcp_server.py`. It builds 4-choice questions from that lecture's glossary entries, masks the term in its own definition and pulls distractors from the same lecture. For an unknown lecture (anything outside 01–04 and 06; the glossary has no Lecture 05 terms) or `num_questions` outside 1–5, it *returns* a message that says what to do next. I compared three versions of the out-of-range branch (`return`, `raise ValueError`, `raise ToolError`), 3 live runs each, then ran a description ablation (sharp vs `"""Quiz."""`, 2 prompts × 3 runs each). I added `tests/test_mcp_homework.py` with 17 tests.
  - **Advanced:** on 2026-11-26 I read the official MCP docs for Claude Code, Codex, Gemini CLI and VS Code, and mapped `app/mcp_servers.json` onto each one.
- Results —
  - **Basic:** `--list-tools` shows 9 tools including `glossary_get_lecture_summary`. "What will we learn in Lecture 02?" → `[tool call] glossary_get_lecture_summary({"lecture":2})`, 2 responses.
  - **Implementation, valid:** "Quiz me on Lecture 02 with 2 questions." → `glossary_make_quiz({"lecture":2,"num_questions":2})`. The agent showed the questions and choices and held back the answers, as the description asks. "Give me 8 review questions on Lecture 06." → the model read "1 to 5" in the description and called it twice (`num_questions` 5, then 3) instead of sending 8. So the bad value never reached my range check.
  - **Implementation, out of range ("Make a quiz for Lecture 99."), 3 runs each:**

    | Branch | What the model received | Responses / input tokens | Answer |
    |---|---|---|---|
    | `return` | `[tool return] glossary_make_quiz -> No quiz for Lecture 99: the glossary has no terms for it. Lectures with quiz terms: 01, 02, 03, 04, 06. Ask the learner …` | 2 / 4,952 | lists 01–04, 06 and asks me to pick (3/3) |
    | `raise ValueError` | `[tool error]  glossary_make_quiz -> Error executing tool make_quiz` (the reason is dropped) | 3 / 7,455 | retried with `glossary_get_lecture_summary({"lecture":99})` and answered from that (3/3) |
    | `raise ToolError` | `[tool error]  glossary_make_quiz -> Error executing tool make_quiz: No quiz for Lecture 99: …` | 2 / 4,967 | same as `return` (3/3) |

  - **Ablation (tool calls per run, 3 runs each):**

    | Prompt | Sharp description | `"""Quiz."""` |
    |---|---|---|
    | "Give me a few practice questions on fine-tuning and LoRA…" | 3/3 `search_glossary` → `make_quiz(lecture=2)` | 0/3 call `make_quiz`; the model writes its own questions from one glossary hit |
    | "Test me on MCP." | 3/3 end on `make_quiz(lecture=6)` (1 run tried lecture 3 first, 4 responses) | 3/3 `make_quiz(lecture=3)`, because the top glossary hit for "MCP" is tagged Lecture 3, and only 1 of Lecture 3's 13 terms is about MCP |

  - **Tests:** `uv run pytest -q` went from 21 passed (baseline) to **38 passed**. The new tests cover the three tools being listed, `get_lecture_summary(2)` over MCP, grounded quizzes for every lecture (choices from that lecture, no repeats, term masked), lectures 0/5/99/-1, `num_questions` 0/6, a schema rejection for `"two"`, and the three return/raise cases through the real Pydantic AI MCP client.
  - **Advanced comparison (checked 2026-11-26):**

    | | This repo | Claude Code | Codex (CLI/IDE/desktop) | Gemini CLI | VS Code (Copilot harness) |
    |---|---|---|---|---|---|
    | Where | `app/mcp_servers.json`, `mcpServers` | `.mcp.json` (project) or `~/.claude.json` (local/user); `claude mcp add` | TOML `[mcp_servers.<name>]` in `~/.codex/config.toml` or `.codex/config.toml`; `codex mcp add` | `mcpServers` in `~/.gemini/settings.json` or `.gemini/settings.json`; `gemini mcp add` | `mcpServers` in `~/.copilot/mcp-config.json` or workspace-root `.mcp.json` (`.vscode/mcp.json` `servers` format is the deprecated Local harness) |
    | `command` | `"command"`, `"args"` | same keys; `claude mcp add name -- uvx …` | `command = "uvx"`, `args = [...]` | same keys | same keys plus `"type": "stdio"` |
    | `url` | `{"url": …}` (Streamable HTTP) | needs `"type": "http"`; a `url` with no `type` is read as stdio and **skipped** | `url = "…"` (Streamable HTTP) | `httpUrl`; plain `url` means **SSE** | `"type": "http", "url": …` |
    | Scope / precedence | one project | local > project > user; whole entry wins, no field merge | CLI flags > project (closest wins) > profile > user > system | system override > project > user > system defaults | user file vs workspace file; precedence for duplicate names not stated |
    | Untrusted repo | starts whatever is listed | `.mcp.json` servers wait for approval; a repo can't approve itself; but `claude -p`/SDK load them without asking | project `.codex/` ignored unless the project is trusted | with folder trust on: workspace settings ignored and no MCP servers connect. Folder trust is **off by default** | `.mcp.json` follows Workspace Trust; Restricted mode blocks it; once trusted, no separate MCP prompt |

    Docs (all returned 200 on 2026-11-26):
    https://code.claude.com/docs/en/mcp ·
    https://learn.chatgpt.com/docs/extend/mcp?surface=cli (developers.openai.com/codex/mcp now redirects here) ·
    https://learn.chatgpt.com/docs/config-file/config-basic ·
    https://geminicli.com/docs/tools/mcp-server/ ·
    https://geminicli.com/docs/reference/configuration/ ·
    https://geminicli.com/docs/cli/trusted-folders/ ·
    https://code.visualstudio.com/docs/agents/reference/mcp-configuration ·
    https://code.visualstudio.com/docs/agents/run/manage-mcp-servers
- Observations and questions —
  - `raise ValueError` is the worst choice in this stack. MCP SDK 2.3 treats it as a crash and sends only "Error executing tool make_quiz", so the model has to guess. Here it happened to find another tool, at 3 responses and +50% tokens. `ToolError` passes the reason on but marks it as a retry (Pydantic AI allows 1 by default; a model that repeats the same call ends the run, as my test shows). For an argument the user got wrong, a plain `return` is the cleanest result.
  - The description acts as validation before the call. "1 to 5" made the model split 8 into 5 + 3, and "for one lecture… Quiz me on Lecture 02" is what turned a topic into a lecture number. With `"""Quiz."""` the tool was skipped for LoRA and given the wrong lecture for MCP.
  - The same `mcp_servers.json` is not portable. The `glossary`/`fetch` entries drop straight into Claude Code, Gemini CLI and VS Code. The `aws` line breaks in three ways: skipped by Claude Code (no `type`), treated as SSE by Gemini CLI (needs `httpUrl`), and needs `"type": "http"` in VS Code. Codex is the only one where `url` alone means Streamable HTTP, but it uses TOML.
  - Trust defaults differ. Codex and VS Code ignore a cloned repo's servers until you trust it. Claude Code asks per server, except in `-p`/SDK runs. Gemini CLI connects project servers unless you turn folder trust on. Our course agent has no trust step at all: `uv run` starts whatever the JSON says.
  - Gemini CLI warns against underscores in server names because it splits `mcp_server_tool` at the first underscore. Our `server_tool` prefix has the same ambiguity: a server named `my_glossary` would be hard to tell apart.
  - Limitations: 3 runs per cell is a small sample. Quizzes use `random`, so runs differ. Some definitions still hint at the answer through related terms (the QLoRA definition mentions LoRA). Lecture 05 has no glossary terms, so it gets no quiz. All model runs went through OpenRouter, not the Gemini API directly.
