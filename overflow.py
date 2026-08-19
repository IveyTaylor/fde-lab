import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

QUESTIONS = [
    """Explain the difference between a data lake and a warehouse.
Cover storage formats, schema enforcement, and typical query patterns.
Describe when each is the better choice and what drives that decision.
Include the cost implications of each approach at enterprise scale.""" * 40,
    "why do governments fail?"*40,
    "how does electrolysis work?"*40,
    "What is better between Snowflake and Databricks?"*40,
    "What is the best truck to buy in 2026?"*40,
    "Is python the best programming language?"*40,
    "Why did the Khmer Rouge kill all those people?"*40,
    "What's the cheepest place to visit in the first worle?"*40,
    "Does communism work anywhere in the world right now?"*40,
    "How many planets are in all of existance?"*40,
    "How does the sun generate energy?"*40,
    "Whats the best breed of dog?"*40,
]
# CHUNK = "Whats the diff between a data lakehouse and data lake. " * 200
messages = []

with open("notes/varied-run.md", "w", encoding="utf-8") as run_log:
    for i in range(12):
        messages.append({"role": "user", "content": QUESTIONS[i % len(QUESTIONS)]})

        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=messages,
        )

        reply_text = response.content[0].text
        messages.append({"role": "assistant", "content": reply_text})

        print(f"turn {i+1} | in tokens {response.usage.input_tokens} | out tokens {response.usage.output_tokens} | stop reasonn {response.stop_reason}")
        print(f"This is message {len(messages)} because thats what len(messages) is telling me right now")
        print(f"\n>>> SENT: {QUESTIONS[i % len(QUESTIONS)][:150]}")
        print(f"<<< GOT: {reply_text[:300]}")

        run_log.write(f"\n## Turn {i+1}\n")
        run_log.write(f"in: {response.usage.input_tokens} | out: {response.usage.output_tokens} | {response.stop_reason}\n\n")
        run_log.write(f"**Sent:** {QUESTIONS[i % len(QUESTIONS)][:200]}\n\n")
        run_log.write(f"**Got:** {reply_text}\n")