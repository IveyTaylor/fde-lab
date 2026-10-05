import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
BACKEND = os.getenv("LLM_BACKEND", "anthropic")   # "anthropic" or "ollama"

if BACKEND == "ollama":
    client = Anthropic(base_url="http://localhost:11434", api_key="ollama")
    MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
else:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")