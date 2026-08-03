# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A teaching template (Module 3 · Week 4 project) for a single-file agentic loop built directly on a
provider SDK — no framework. It researches a topic, saves notes, and "emails" a summary, with three
guardrails wired in: a human approval gate, an audit log, and a hard iteration cap.

The provider is **Groq** (`groq` SDK, `client.chat.completions.create`, OpenAI-style tool calling).
That choice is documented for students in [README.md](README.md) along with what to change to swap
providers — treat Groq as the default, not a hard assumption, and keep the loop provider-shaped
rather than Groq-specific.

Two tools are deliberately left as starters with `TODO` comments — `research()` (returns model
recollection rather than real search results) and `send_email()` (dry-run print, sends nothing).
Those TODOs are the assignment; see the checklist in the README. Don't "fix" them unless asked, and
don't remove the guardrails.

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste a real GROQ_API_KEY (console.groq.com/keys)

python agent.py "Research the James Webb telescope, save the notes to webb.md, then email a summary to me@example.com"
```

The goal is joined from all argv, so quoting is optional but recommended. There is no test suite or
build step; a Ruff hook lints files on write.

Each run appends to a new `logs/run-<YYYYmmdd-HHMMSS>.log`. `notes/` and `logs/` are gitignored
(only their `.gitkeep` files are tracked), so a run's output never shows up in `git status`.

## Architecture

Three modules, one direction of dependency: `agent.py` → `tools.py` → `config.py`.

**[agent.py](agent.py)** — the reason → act → observe loop, and the only place with control flow.
`run()` keeps a growing `messages` list, calls `chat.completions.create()` with `TOOL_SCHEMAS`, and
branches on whether the reply carries `tool_calls`: none means the model is finished, print
`message.content` and return. Otherwise each `tool_call` is dispatched through `run_tool()`.
The `for turn in range(1, MAX_ITERATIONS + 1)` is the cap — falling out of the loop is the only
other exit.

Two message-shaping helpers carry the API's requirements, and both are load-bearing:
- `assistant_block()` converts the SDK's message object back into a plain dict **including its
  `tool_calls` verbatim** — the API rejects a follow-up request whose history lost them.
- `tool_result_block()` builds the `{"role": "tool", "tool_call_id": ...}` reply. Every single
  `tool_call` must get exactly one of these back, which is why JSON-argument parse failures append
  an error string instead of `continue`-ing silently.

Tool arguments arrive as a **JSON string** in `call.function.arguments`, not a dict — `json.loads`
in the loop, then `func(**tool_input)` in `run_tool`.

The `create()` call is wrapped for `BadRequestError` / `tool_use_failed`, which is Groq rejecting a
malformed tool call the model wrote (no `tool_calls` come back at all — it's an API error, not a
parse problem downstream). The handler appends a corrective user message and burns a turn rather
than crashing; anything else re-raises.

**[tools.py](tools.py)** — each tool is a *pair*: a `*_schema` dict (what the model sees) and a
plain Python function (what actually runs). Both are registered at the bottom in `TOOL_SCHEMAS`
(the list handed to the API) and `TOOL_FUNCTIONS` (name → callable). Adding a tool means adding to
both, and the schema's `parameters` property names must match the function's parameter names
exactly — a mismatch is a `TypeError` at call time. Schemas use the OpenAI function wrapper
(`{"type": "function", "function": {"name", "description", "parameters"}}`); the JSON schema inside
`parameters` is portable across providers, the wrapper is not. Tool `description` strings are prompt
surface, not documentation: they are how the model decides when to reach for a tool.

**[config.py](config.py)** — every knob lives here rather than inline: `MODEL`, `MAX_TOKENS`,
`MAX_ITERATIONS`, `NOTES_DIR`, `LOG_DIR`, and `AUTO_APPROVE`. Groq retires model names periodically;
if a run fails with `model_not_found`, `MODEL` is the thing to update. `MODEL` must be a strong
tool-caller — `llama-3.3-70b-versatile` reliably malforms tool calls with long arguments (a saved
note body), which is why the default is `openai/gpt-oss-120b`. `MAX_TOKENS` is 4096 for the same
reason: a note's full text travels inside the tool call, and a tight cap truncates it mid-JSON.

## The guardrails (load-bearing — preserve when editing)

- **Approval gate.** `needs_approval()` is deny-by-default: a tool runs unattended only if its name
  is in `config.AUTO_APPROVE`. Everything else hits `ask_human()`, which blocks on `input()` and
  requires a literal `y`. On denial the model gets the string `"The human did not approve this
  action. Do not retry it."` rather than an error, so the loop continues cleanly. Rule of thumb
  encoded here: reading/searching is auto-approved, sending/deleting/spending is not — `send_email`
  is intentionally absent from `AUTO_APPROVE`.
- **Logging.** `log()` writes one timestamped line to stdout *and* to `LOG_FILE`, which is fixed at
  import time. Every call, result (truncated to 200 chars), approval, denial, and error goes
  through it.
- **Error containment.** `run_tool()` catches every exception from a tool and returns the message as
  a normal tool result. Tool bugs are visible to the model, never fatal to the run.

## Conventions

- Secrets come only from `.env` via `load_dotenv()`; `Groq()` is constructed with no arguments and
  picks up `GROQ_API_KEY` from the environment. Never inline a key.
- `save_note()` runs `os.path.basename()` on the filename so writes can only land inside `notes/`.
  Keep that containment if you touch file-writing tools.
- Both `agent.py` and `tools.py` call `load_dotenv()` and construct their own client; `tools.py`
  needs one because `research()` itself calls the model (an agent-calls-model-inside-a-tool pattern).
- The code is written to be read by students: long explanatory docstrings, `# ---` section banners,
  comments explaining *why*. Match that register in edits.
