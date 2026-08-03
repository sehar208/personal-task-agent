"""
Personal Task Agent — the loop.

This is the reason -> act -> observe loop from Class 3, now with the three
guardrails from Class 4 wired in:

  * APPROVAL  — risky tools ask a human before they run.
  * LOGGING   — every tool call, result, and approval is written to logs/.
  * CAP       — the loop stops after MAX_ITERATIONS no matter what.

The model provider is GROQ (see config.py). Groq speaks the OpenAI-style
chat-completions API, so if you'd rather use a different provider, you mostly
swap the client and the model name — the loop itself stays the same.

You should not need to change this file to finish the core project. Read it,
understand it, then do your work in tools.py.

Run it:
    python agent.py "Research the James Webb telescope, save notes, then email
                     a summary to me@example.com"
"""

import sys
import os
import json
import datetime
from groq import Groq, BadRequestError
from dotenv import load_dotenv

import config
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

# Read GROQ_API_KEY from the .env file you created (see .env.example).
load_dotenv()

client = Groq()


# ---------------------------------------------------------------------------
# Logging — the audit trail.
# ---------------------------------------------------------------------------

def _log_path() -> str:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(config.LOG_DIR, f"run-{stamp}.log")


LOG_FILE = _log_path()


def log(line: str) -> None:
    """Write one timestamped line to the console AND the log file."""
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"{stamp}  {line}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


# ---------------------------------------------------------------------------
# The human-in-the-loop approval gate.
# ---------------------------------------------------------------------------

def needs_approval(tool_name: str) -> bool:
    """A tool needs approval unless it's on the AUTO_APPROVE allowlist."""
    return tool_name not in config.AUTO_APPROVE


def ask_human(tool_name: str, tool_input: dict) -> bool:
    """Show the human what's about to happen and wait for y/n."""
    print("\n>>> APPROVAL NEEDED")
    print(f"    tool:  {tool_name}")
    for key, value in tool_input.items():
        preview = str(value)
        if len(preview) > 300:
            preview = preview[:300] + " ..."
        print(f"    {key}: {preview}")
    answer = input(">>> Approve this action? (y/n): ").strip().lower()
    return answer == "y"


# ---------------------------------------------------------------------------
# Act + Observe — run one tool the model asked for and package the result.
# ---------------------------------------------------------------------------

def run_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name, with the approval gate in front of risky ones."""
    if needs_approval(tool_name):
        if not ask_human(tool_name, tool_input):
            log(f"DENIED  {tool_name}  (human said no)")
            return "The human did not approve this action. Do not retry it."
        log(f"APPROVED {tool_name}  (human said yes)")

    func = TOOL_FUNCTIONS.get(tool_name)
    if func is None:
        log(f"ERROR   unknown tool: {tool_name}")
        return f"Error: no tool named {tool_name}."

    log(f"CALL    {tool_name}({tool_input})")
    try:
        result = func(**tool_input)
    except Exception as exc:  # keep the loop alive; tell the model what broke
        log(f"ERROR   {tool_name} raised {exc}")
        return f"The tool errored: {exc}"

    log(f"RESULT  {str(result)[:200]}")
    return str(result)


def tool_result_block(tool_call_id: str, content: str) -> dict:
    """Wrap a tool's output as a tool message the model can read (the Observe step)."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def assistant_block(message) -> dict:
    """
    Turn the model's reply into a plain dict we can put back in `messages`.

    The API needs to see its own tool_calls again on the next turn, so they have
    to be carried over verbatim alongside any text it wrote.
    """
    block = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        block["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return block


# ---------------------------------------------------------------------------
# The loop.
# ---------------------------------------------------------------------------

def run(goal: str) -> None:
    log(f"GOAL    {goal}")
    messages = [{"role": "user", "content": goal}]

    for turn in range(1, config.MAX_ITERATIONS + 1):
        log(f"--- turn {turn} / {config.MAX_ITERATIONS} ---")

        # REASON: ask the model what to do next.
        try:
            resp = client.chat.completions.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
        except BadRequestError as exc:
            # `tool_use_failed`: the model tried to call a tool but wrote the call
            # in broken syntax, so Groq rejected it instead of returning tool_calls.
            # It's a model slip, not a bug in your tools — nudge it and try again.
            # (Weaker models do this a lot, especially with long arguments. If you
            # see it repeatedly, switch MODEL in config.py.)
            if "tool_use_failed" not in str(exc):
                raise
            log("ERROR   model wrote a malformed tool call; asking it to retry")
            messages.append({
                "role": "user",
                "content": (
                    "Your last reply tried to call a tool, but the call was malformed "
                    "and was rejected before it ran. Call the tool again using the exact "
                    "tool-call format, with valid JSON arguments."
                ),
            })
            continue

        message = resp.choices[0].message
        messages.append(assistant_block(message))

        # No tool call means the model is done talking -> print and stop.
        if not message.tool_calls:
            log("DONE")
            print("\n=== FINAL ANSWER ===")
            print((message.content or "").strip())
            return

        # ACT + OBSERVE: run each requested tool, feed results back in.
        # Every tool_call MUST get exactly one tool message back, even on failure,
        # or the next request will be rejected.
        for call in message.tool_calls:
            try:
                # Groq sends arguments as a JSON *string*, not a dict.
                tool_input = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                log(f"ERROR   bad arguments for {call.function.name}: {exc}")
                messages.append(tool_result_block(
                    call.id,
                    f"Error: arguments were not valid JSON ({exc}). Try again.",
                ))
                continue

            output = run_tool(call.function.name, tool_input)
            messages.append(tool_result_block(call.id, output))

    # We only get here if the cap was hit.
    log(f"STOPPED hit the {config.MAX_ITERATIONS}-iteration cap")
    print("\n=== STOPPED: iteration cap reached ===")


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python agent.py "your goal in one sentence"')
        print('Example: python agent.py "Research black holes, save notes, '
              'then email a summary to me@example.com"')
        sys.exit(1)

    run(" ".join(sys.argv[1:]))
