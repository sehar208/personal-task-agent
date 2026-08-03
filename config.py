"""
Central knobs for the agent. Change behaviour here, not scattered through the code.
"""
from dotenv import load_dotenv

load_dotenv()

# Which provider/model the agent uses.
#
# This template runs on GROQ. Groq speaks the OpenAI-style chat-completions API,
# which is the same shape most providers use, so swapping providers later is a
# small edit rather than a rewrite.
#
# Pick a model that is GOOD AT TOOL CALLING — that's the whole job here. A model
# that writes lovely prose but garbles its function-call syntax will crash the run
# with a `tool_use_failed` 400 before your tool ever executes.
#   "openai/gpt-oss-120b"       <- the default; reliable at tool calls
#   "openai/gpt-oss-20b"        <- smaller/cheaper, still decent
#   "llama-3.3-70b-versatile"   <- capable, but frequently malforms tool calls
#                                  when an argument is long. Not recommended here.
# If this string ever stops working, check the current model list in the Groq docs.
MODEL = "openai/gpt-oss-120b"

# The seatbelt. The loop will stop after this many turns no matter what,
# so a confused agent can never spend money forever. Do NOT remove this.
MAX_ITERATIONS = 8

# Cap on how long any single model reply can be. Needs headroom: when the agent
# saves a note, the whole note body travels inside the tool call, so a tight cap
# can truncate the call mid-JSON and break it.
MAX_TOKENS = 4096

# Least privilege: tools listed here run WITHOUT asking a human.
# Everything else must be approved before it runs.
# Rule of thumb: reading/searching is safe; sending/deleting/spending is not.
AUTO_APPROVE = {
    "research",    # only reads/looks things up -> safe
    "save_note",   # writes only inside the notes/ folder -> safe enough
    # "send_email" is deliberately NOT here -> it will require your approval.
}

# Where things land.
NOTES_DIR = "notes"
LOG_DIR = "logs"
from dotenv import load_dotenv


