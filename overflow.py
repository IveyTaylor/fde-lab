import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

CHUNK = "Whats the diff between a data lakehouse and data lake. " * 200
messages = []

for i in range(60):
        messages.append({"role": "user", "content": CHUNK})

        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=messages,
        )

        reply_text = response.content[0].text
        messages.append({"role": "assistant", "content": reply_text})

        print(f"turn {i+1} | in tokens {response.usage.input_tokens} | out tokens {response.usage.output_tokens} | stop reasonn {response.stop_reason}")
