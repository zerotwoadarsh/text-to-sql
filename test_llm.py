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
    "nex-agi/nex-n2.5-mini:free",
    "nex-agi/nex-n2.5-pro:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "inclusionai/ling-3.0-flash-fin:free",
    "qwen/qwen3.8-27b:free",
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "thinkingmachines/inkling-small:free",
    "poolside/laguna-s-2.1:free",
    "thinkingmachines/inkling:free",
    "poolside/laguna-xs-2.1:free",
    "cohere/north-mini-code:free",
    "z-ai/glm-5.2:free",
    "nvidia/nemotron-3.5-content-safety:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free"
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