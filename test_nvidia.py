from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

response = client.chat.completions.create(
    model="deepseek-ai/deepseek-v4.1-flash",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say 'connection successful' and nothing else."}]
)

print(response.choices[0].message.content)





array =[ "inclusionai/ling-3.0-flash-fin:free",
 "qwen/qwen3.8-27b:free",
 "dots-studio/dots-3-note-preview:free",
 "liquid/lfm-2.5-2.6b:free",
 "nvidia/nemotron-3.5-lightning:free",
 "thinkingmachines/inkling-small:free",
 "poolside/laguna-s-2.1:free",
 "thinkingmachines/inkling:free",
 "poolside/laguna-xs-2.1:free",
 "cohere/north-mini-code:free",
 "nvidia/nemotron-3.5-content-safety:free",
 "nvidia/nemotron-3-ultra-550b-a55b:free",
 "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
 "google/gemma-4-26b-a4b-it:free",
 "google/gemma-4-31b-it:free",
 "nvidia/nemotron-3-super-120b-a12b:free",]
for items in array:
    print(f'(openrouter_client, "{items}"),')