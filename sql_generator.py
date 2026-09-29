import re
import time
import os

from dotenv import load_dotenv
from openai import OpenAI

from schema_inspector import get_schema_context

load_dotenv()

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

gemini_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY"),
)


FALLBACK_MODELS = [
    (nvidia_client, "deepseek-ai/deepseek-v4.1-flash"),
    (openrouter_client, "qwen/qwen3.8-27b:free"),
    (openrouter_client, "google/gemma-4-31b-it:free"),
    (openrouter_client, "google/gemma-4-26b-a4b-it:free"),
    (gemini_client, "gemini-3.8-flash"),
]

SYSTEM_PROMPT = """You are a SQL expert. Given a database schema and a question, \
generate a single SQLite SELECT query that answers the question.

Rules:
- Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
- Return ONLY the raw SQL query. No explanation, no markdown code fences, no preamble.
- Use table and column names exactly as given in the schema.
- Use proper JOINs based on the foreign key relationships provided.
"""


def extract_sql(text: str) -> str | None:
    """
    Extracts the SQL statement from a raw LLM response, which may include
    markdown fences or (for reasoning models) chain-of-thought text before
    the actual query.

    Returns None if no SQL could be confidently identified.
    """
    fence_match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # SQL may begin with WITH (a CTE) or directly with SELECT. We must match
    # whichever keyword appears first -- searching for SELECT alone would
    # incorrectly strip off a leading "WITH cte_name AS (" clause, since the
    # first SELECT in a CTE query is *inside* the WITH block, not at the
    # true start of the statement.
    match = re.search(r"\b(WITH|SELECT)\b.*", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()

    return None


def call_with_fallback(messages, max_tokens=1500) -> str:
    """
    Tries each (client, model) pair in FALLBACK_MODELS in order until one
    produces usable SQL. Returns the extracted SQL string directly.
    Raises RuntimeError if every option fails or produces unusable output.
    """
    for client, model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            raw_content = response.choices[0].message.content

            if not raw_content or not raw_content.strip():
                print(f"[Model {model} returned empty content, trying next]")
                print(f"  DEBUG - full response object: {response}")
                continue

            content = extract_sql(raw_content)

            if content is None:
                print(f"[Model {model} never produced a SELECT statement (likely still reasoning), trying next]")
                continue

            print(f"[Using model: {model}]")
            return content

        except Exception as e:
            print(f"[Failed with {model}: {e}]")
            time.sleep(.5)

    raise RuntimeError("All fallback models failed.")

def call_with_fallback_raw(messages, max_tokens=500) -> str:
    """
    Tries each (client, model) pair in FALLBACK_MODELS in order until one
    returns non-empty content. Returns the RAW response text, unprocessed --
    callers are responsible for any format-specific extraction (SQL, JSON, etc).
    Raises RuntimeError if every option fails or returns empty content.
    """
    for client, model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            raw_content = response.choices[0].message.content

            if not raw_content or not raw_content.strip():
                print(f"[Model {model} returned empty content, trying next]")
                continue

            print(f"[Using model: {model}]")
            return raw_content

        except Exception as e:
            print(f"[Failed with {model}: {e}]")
            time.sleep(0.5)

    raise RuntimeError("All fallback models failed.")


def call_with_fallback(messages, max_tokens=500) -> str:
    """
    SQL-specific wrapper: calls call_with_fallback_raw, then extracts and
    validates that the response actually contains a SQL statement (WITH/SELECT).
    Used by the SQL generation pipeline specifically.
    """
    for client, model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            raw_content = response.choices[0].message.content

            if not raw_content or not raw_content.strip():
                print(f"[Model {model} returned empty content, trying next]")
                continue

            content = extract_sql(raw_content)

            if content is None:
                print(f"[Model {model} never produced a SELECT statement (likely still reasoning), trying next]")
                continue

            print(f"[Using model: {model}]")
            return content

        except Exception as e:
            print(f"[Failed with {model}: {e}]")
            time.sleep(0.5)

    raise RuntimeError("All fallback models failed.")

def generate_sql(question: str) -> str:
    """
    Standalone helper for quick manual testing of this file alone.
    """
    schema = get_schema_context()

    user_prompt = f"""Schema:
{schema}

Question: {question}

SQL query:"""

    sql = call_with_fallback([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    return sql



if __name__ == "__main__":
    questions = [
        "How many customers are there?",
        "What are the top 5 best-selling tracks by total quantity sold?",
        "Which country has the most customers?",
    ]
    for q in questions:
        print(f"\nQuestion: {q}")
        sql = generate_sql(q)
        print("Generated SQL:", sql)

