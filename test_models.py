from dotenv import load_dotenv
import os
import requests

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY")

response = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {key}"}
)

print("Status:", response.status_code)
data = response.json()

# Print only free models
free_models = [m["id"] for m in data.get("data", []) if m["id"].endswith(":free")]
print("Free models available right now:")
for m in free_models:
    print(" -", m)