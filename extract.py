import json
import sys
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PREFILL = '{"company":'

MODEL = "claude-haiku-4-5-20251001"

# The messy input. Triple quotes so it can span lines
EMAIL = """Hi — we're closing out our old records room and need to get rid of
a bunch of files, probably a few boxes, maybe more once we get into the back
closet. Some of it is patient billing stuff from before we switched systems so
it needs to be done right. Can you give me a price and let me know how soon
someone could come out? We're off Highway 21 near the Food Lion."""

SYSTEM = """You extract structured data from inbound customer emails for a
records destruction company. 

Return ONLY a JSON object. No markdown fences, no commentary before or after.

Keys: 

  company           - string or null
  contact_name      - string or null
  service_type      - string or null
  box_count         - integer or null. Never a string. Null if not stated numerically.
  volume_stated_as  - the customer's EXACT words about quantity, copied verbatim. Null if absent.
  urgency           - string or null

Use null for anything not stated. Never use "not provided", "Unknown", or any otehr placeholder string.  
"""

# TODO 5: add the prefill turn
#   the model continues from wahtever the last assistant turn contains.
#   Start it mid-object and it cannot emit a preamble.

messages = [
        {"role": "user", "content": EMAIL},
        {"role": "assistant", "content": "{"},
]

print("Ivey, this is messages")
print(messages)

# TODO 1: build the messages list and make the call
#   Same shape as chat.py, but one user turn instead of a growing history
#   The content shold be the EMAIL

response = client.messages.create(
    model=MODEL,
    max_tokens=1000,
    system=SYSTEM,
    messages=[
        {"role": "user", "content": EMAIL},
        {"role": "assistant", "content": PREFILL},
    ]
)

# TODO 2: pull the text out. Same as chat.py
raw = PREFILL + response.content[0].text     # prepend happens HERE, once
# raw = response.content[0].text"

print("Ivey this is repr(raw)")
print(repr(raw))

# TODO 4 try to parse it. Expect this to blow up.
data = json.loads(raw)
print(data)

with open("output.json", "w") as f:
    json.dump(data, f, indent=2)

# TODO 3: look at it before you touch it
#   The rer() is deliberate -- it shows you newlines and quotes literally
#   Which is exactly wehre parse failures hide
print("--- RAW ---")
print(repr(raw))
print("--- END RAW ---")
# print(raw)

# TODO 6: Put the brace back
#   response.content[0].text will NOT include teh "{" you prefilled
#   the model only returns what IT generated. Prepend BEFORE parsing

# raw = "{" + response.content[0].text