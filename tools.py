"""
The agent's toolbox.

Each tool is two things:
  1. A SCHEMA  -> what the model sees (name, description, parameters).
     The description is how the model decides WHEN to use the tool, so write it well.
  2. A FUNCTION -> the real code that runs when the model asks for that tool.

The schemas use the OpenAI-style "function" shape, because that's what Groq speaks
(and most other providers too). If you switch providers, the JSON schema inside
"parameters" usually stays exactly the same — only the wrapper changes.

TOOL_SCHEMAS is the menu handed to the model.
TOOL_FUNCTIONS maps a tool name to the function that does the work.
"""

import os
import datetime
from groq import Groq
from dotenv import load_dotenv

import config

load_dotenv()

# One shared client for tools that need to call the model (e.g. research).
# Groq() reads GROQ_API_KEY from the environment — never pass a key here.
_client = Groq()


# ---------------------------------------------------------------------------
# TOOL 1 — research
# ---------------------------------------------------------------------------

research_schema = {
    "type": "function",
    "function": {
        "name": "research",
        "description": (
            "Research a topic and return a short, factual set of notes about it. "
            "Use this when you need information before writing anything."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The subject to research, e.g. 'the James Webb telescope'.",
                }
            },
            "required": ["topic"],
        },
    },
}


def research(topic: str) -> str:
    """
    Return notes about `topic`.

    STARTER VERSION: asks the model to summarise what it knows. This works, but it
    can be out of date and it cannot see today's news.

    TODO (required): make this return REAL, useful notes. Options:
      - use one of Groq's browser/search-enabled models or its built-in web search, or
      - call a search API you like (Tavily, Brave, SerpAPI, ...) and summarise the results.
    Keep the output to a few tight paragraphs.
    """
    prompt = (
        f"Write concise, factual research notes about: {topic}.\n"
        "Use short paragraphs or bullets. No preamble, just the notes."
    )
    resp = _client.chat.completions.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# TOOL 2 — save_note  (fully working, nothing to change)
# ---------------------------------------------------------------------------

save_note_schema = {
    "type": "function",
    "function": {
        "name": "save_note",
        "description": (
            "Save text to a note file so it can be reused later. "
            "Use this to store research findings before writing a summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name only, e.g. 'webb-notes.md'. No folders.",
                },
                "content": {
                    "type": "string",
                    "description": "The text to save.",
                },
            },
            "required": ["filename", "content"],
        },
    },
}


def save_note(filename: str, content: str) -> str:
    """Write `content` to notes/<filename>. Stays inside the notes folder on purpose."""
    os.makedirs(config.NOTES_DIR, exist_ok=True)

    # Safety: strip any path tricks so a note can only ever land in notes/.
    safe_name = os.path.basename(filename)
    path = os.path.join(config.NOTES_DIR, safe_name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Saved {len(content)} characters to {path}"


# ---------------------------------------------------------------------------
# TOOL 3 — send_email  (dry-run by default; the approval gate protects it)
# ---------------------------------------------------------------------------

send_email_schema = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": (
            "Send an email summary to a recipient. "
            "Use this as the final step once the notes are ready."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body": {"type": "string", "description": "The full email body."},
            },
            "required": ["to", "subject", "body"],
        },
    },
}


def send_email(to: str, subject: str, body: str) -> str:
    """
    STARTER VERSION: DRY RUN. It does not send anything — it just prints what it
    WOULD send. That's on purpose: nobody spams a real inbox while building.

    TODO (stretch): wire up a real send only if you want to. Safer options than
    raw SMTP: a Gmail MCP connector, or a transactional email API. Whatever you use,
    keep this tool behind the human approval gate.
    """
    when = datetime.datetime.now().strftime("%H:%M:%S")
    print("\n----- DRY-RUN EMAIL -------------------------------")
    print(f"time:    {when}")
    print(f"to:      {to}")
    print(f"subject: {subject}")
    print("body:")
    print(body)
    print("---------------------------------------------------\n")
    return f"(dry-run) email to {to} prepared but not actually sent"


# ---------------------------------------------------------------------------
# Registries the agent uses.
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [research_schema, save_note_schema, send_email_schema]

TOOL_FUNCTIONS = {
    "research": research,
    "save_note": save_note,
    "send_email": send_email,
}
