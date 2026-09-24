from dotenv import load_dotenv
from openai import OpenAI
import os
import time

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

FALLBACK_MODELS = [
    "qwen/qwen3.8-27b:free",
    "google/gemma-4-31b-it:free",
    "z-ai/glm-5.2:free",
]

def call_with_fallback(messages, max_tokens=50):
    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            print(f"Success with model: {model}")
            return response
        except Exception as e:
            print(f"Failed with {model}: {e}")
            time.sleep(2)
    raise RuntimeError("All fallback models failed.")

response = call_with_fallback(
    [{"role": "user", "content": "Say 'connection successful' and nothing else."}]
)
print(response.choices[0].message.content)