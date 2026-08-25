import json
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

# Only allow specific services
ALLOWED_SERVICES = ["shredding", "scanning", "hard drive destruction"]

def validate(record):
    problems = []

    expected = ["company","contact_name","service_type","box_count","volume_stated_as","urgency"]

    for key in expected:
        if key not in record:
            problems.append(f"missing key:  {key}")

    box = record.get("box_count")
    if box is not None and not isinstance(box, int):
        problems.append(f"box_count must be an integer or null. Its {type(box).__name__}: {box!r}")

    service_type = record.get("service_type")
    if service_type is not None and service_type.lower() not in ALLOWED_SERVICES:
        problems.append(
            f"service_type was {service_type!r}, which is not a service this business "
            f"offers. Choose exactly one of: {ALLOWED_SERVICES}, or null."
        )


    PLACEHOLDERS = ["not provided", "unknown", "n/a", "not specified"]

    for key, value in record.items():
        # print(key)
        # print(value)
        if isinstance(value, str) and value.lower() in PLACEHOLDERS:
            problems.append(f"placeholder in {key} of {value!r}")

    return problems

# Okay here is the next section
MAX_ATTEMPTS = 3

messages = [
    {"role": "user", "content": EMAIL},
]

for attempt in range(1, MAX_ATTEMPTS + 1):
    print(f"\n--- attempt {attempt} ---")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=messages + [{"role": "assistant", "content": PREFILL}],
    )

    raw = PREFILL + response.content[0].text
    print(repr(raw))
    print("that was raw")

    try:
        data = json.loads(raw)
        problems = validate(data)
    except json.JSONDecodeError as e:
        data = None
        problems = [f"response was not valid JSON {e}"]

    if not problems:
        print("VALIDATION PASSED")
        break

    print("VALIDATION FAILED:")
    for p in problems:
        print(f"  - {p}")

    feedback = "The JSON had these problems:\n"+"\n".join(f"- {p}" for p in problems)
    feedback += "\n\nReturn the corrected JSON object only."
    messages.append({"role": "assistant", "content": raw})
    messages.append({"role": "user", "content": feedback})
    outgoing = messages + [{"role": "assistant", "content": PREFILL}]
    # print(messages)
    print(json.dumps(outgoing, indent=2))
    print("that was messages")
    
else:
    print(f"gave up after {MAX_ATTEMPTS} attempts")

if data is not None and not problems:
    print("VALIDATION SUCCESS! AYBABTU!")
    print(data)
else:
    print("no usable record after retries")