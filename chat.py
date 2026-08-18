import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"
PROMPTS = {
    "terse": "You are a terse assitant. Ansewr in one or two sentences",
    "scoped": """You only answer quetsions about data platforms and analytics. 
    For anything outside that, say you can't help and suggest they ask elsewhere.""",
    "constrained": """You are a data engineer explaining concepts to a non-technical business stakeholder.
    Never use a technical term without defining it in the same sentence.
    End every response with a question that checks their understanding.""",
}
SYSTEM = PROMPTS["constrained"]


messages = []       # lives OUT here -- this is the memory, outside of the loop

while True:
    user_input = input("\nyou: ")
    if user_input.lower() in ("quit", "exit"):
        break

    #   TODO 1: append the users turn to messages
    #       shape: {"role": "user", "content": user_input}

    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=messages,
    )

    # TODO 2 pull the text out of the response
    #   response.content is a LIST of blocks, not a string

    reply_text = response.content[0].text
    print(reply_text)
    print(f"[in: {response.usage.input_tokens} | out: {response.usage.output_tokens}]")
    messages.append({"role": "assistant", "content": reply_text})

