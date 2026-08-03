# Personal Task Agent — Starter Template

Module 3 · Week 4 · Project

An agent that completes a real multi-step task on one command — out of the box,
research a topic, save notes to a file, and email a summary — **with a leash
on**: a human approval step, full logging, and a hard cap so the loop can't
run forever.

The scary parts (the loop, the approval gate, logging, the iteration cap) are
already done. Your job is to fill in a few small TODOs, or repoint the whole
thing at a different personal task assistant of your choosing, and make it
yours.

---

## Which model provider does this use?

**This template runs on [Groq](https://console.groq.com).** Groq is free to start,
very fast, and its API is the OpenAI-style `chat.completions` shape that most
providers use — so what you learn here transfers.

**You can absolutely swap in your own provider.** Nothing about the agent loop is
Groq-specific. To switch, change three things:

1. `requirements.txt` — install your provider's SDK instead of `groq`.
2. `.env` / `.env.example` — your provider's API key variable name.
3. `config.py` (`MODEL`) and the client + call sites in `agent.py` / `tools.py`
   (`Groq()` → your client, `client.chat.completions.create(...)` → your call).

If your provider is OpenAI-compatible (OpenAI, Together, Fireworks, OpenRouter,
Ollama, vLLM, …) that last step is usually just a different base URL and the tool
schemas in `tools.py` don't change at all. If you go to a provider with a different
tool-calling format (e.g. Anthropic), you'll also need to reshape the schemas in
`tools.py` and the way tool results are appended in `agent.py` — the two places the
format actually shows up.

---

## What's in here

```
personal-task-agent/
  agent.py        # the reason->act->observe loop + approval + logging + cap
  tools.py        # the 3 tools: research, save_note, send_email  (your TODOs)
  config.py       # model, caps, and which tools auto-run vs need approval
  .env.example    # copy to .env and paste your API key
  requirements.txt
  README.md       # you are here
  notes/          # save_note writes here
  logs/           # every run writes an audit log here
```

---

## Setup (about 5 minutes)

1. **Install the dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your API key**
   ```bash
   cp .env.example .env
   ```
   Grab a free key from https://console.groq.com/keys, then open `.env` and paste
   it after `GROQ_API_KEY=`. Never commit `.env` — it's already in `.gitignore`.

3. **Run it once** (it works out of the box; the email is a safe dry-run)
   ```bash
   python agent.py "Research the James Webb telescope, save the notes to webb.md, then email a summary to me@example.com"
   ```
   Watch the loop run in your terminal, approve the email when it asks,
   then check the new files in `notes/` and `logs/`.

---

## Your assignment

The template runs, but two tools are only starters. Pick one of two paths — the
underlying objectives are identical either way:

**Path A — Extend this research agent.** Give it more or better capabilities
instead of building something new:

- [ ] **Fill in `research()` in `tools.py`.** Right now it just asks the model to
      summarise what it already knows. Make it return *real, useful* notes —
      use a search-enabled model on Groq, or plug in a search API (Tavily, Brave,
      SerpAPI…) and summarise the results.
- [ ] **(Stretch) Add web search as its own tool.** Separate "search the web" from
      "write notes" into two distinct tools instead of one blob, so the model
      chooses when to search vs. when to save.
- [ ] **(Stretch) Add a paper/PDF extraction tool.** Pull structured notes out of
      arXiv abstracts or a PDF (e.g. via `pypdf`) — a second, genuinely different
      research tool alongside web search.
- [ ] **Write a good email step.** Make sure the agent turns the saved notes into
      a clean, readable summary in the email body — not a wall of raw text.
- [ ] **(Stretch) Send a real email.** Only if you want to. Keep it behind the
      approval gate. A Gmail MCP connector or a transactional email API is safer
      than raw SMTP.

**Path B — Build your own personal task assistant.** Keep the loop in
`agent.py` and swap out the tools in `tools.py` for a different assistant
entirely. Some ideas:

- A **LinkedIn engagement agent** — draft posts or comments, queue them, and
  gate the actual posting behind approval.
- A **blog post writer** — research a topic, draft a post, save it to disk, and
  hold publishing behind approval.
- Anything else with a similar shape: gather information, produce a draft or
  artifact, take one action a human should sign off on.

Whichever path you pick, hit the same bar:

- [ ] **At least two tools**, one read-only (auto-approved) and one that takes an
      action a human should sign off on (gated).
- [ ] **Check your permissions.** Look at `AUTO_APPROVE` in `config.py`. Confirm
      that any tool with a real-world side effect (sending, posting, publishing,
      deleting, spending) is NOT on it, so it always asks first.
- [ ] **Keep the guardrails.** The approval gate, the audit log, and the
      iteration cap in `agent.py` / `config.py` stay in place no matter which
      path or tools you build — don't remove or weaken them.

---

## Definition of done

Your project is done when **all** of these are true, whichever path you built:

1. **One command** runs the whole task end to end, using **more than one tool**.
2. Any tool with a real-world side effect **waits for your approval** — typing
   `n` skips it, `y` runs it.
3. A **log file** in `logs/` shows every tool call, its result, the approval, and
   a timestamp.
4. The **iteration cap** is in place (it is — don't remove it).
5. Your **API key is in `.env`**, not pasted into any `.py` file.

Bring a clean run and its log to the next class — you'll demo it live.

---

## How the guardrails work (so you can explain them)

- **Approval gate** — In `config.py`, `AUTO_APPROVE` lists the tools that run
  without asking. Everything else calls `ask_human()` first and only runs on `y`.
  Least privilege: reading is safe, sending is not.
- **Logging** — `log()` in `agent.py` writes every call, result, and approval to
  both the console and a timestamped file in `logs/`.
- **Iteration cap** — `MAX_ITERATIONS` in `config.py` stops the loop after N turns
  no matter what, so a confused agent can never spend money forever.

---

## Troubleshooting

- **`AuthenticationError`** — your key isn't loaded. Check `.env` exists and has a
  real `GROQ_API_KEY`, and that you ran `pip install -r requirements.txt` (which
  installs `python-dotenv`).
- **`model_not_found` / decommissioned model** — Groq retires model names fairly
  often. Check the current list at https://console.groq.com/docs/models and update
  `MODEL` in `config.py`.
- **`BadRequestError ... 'code': 'tool_use_failed'`** — the model tried to call a
  tool but wrote the call in broken syntax, so Groq rejected it. Nothing is wrong
  with your tools. The loop now catches this and asks the model to try again, but
  if you see it repeatedly it means your model is weak at tool calling — especially
  with long arguments like a full note body. `llama-3.3-70b-versatile` fails this
  way often; `openai/gpt-oss-120b` (the default) handles it. Also make sure
  `MAX_TOKENS` is high enough that a long tool call isn't truncated mid-JSON.
- **A tool never gets called** — its `description` in `tools.py` is probably too
  vague. Describe it like you're briefing a new teammate.
- **`TypeError` when a tool runs** — your `parameters` property names must match
  the function's argument names exactly.
- **It loops and stops at the cap** — the model is stuck. Make your goal more
  specific, or check that each tool returns something useful.
