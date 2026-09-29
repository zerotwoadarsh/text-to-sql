import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend -- safe for scripts/servers, no GUI needed
import matplotlib.pyplot as plt
import time

from sql_generator import call_with_fallback_raw

CHART_SYSTEM_PROMPT = """You are a data visualization expert. Given a question, \
the SQL used to answer it, and the resulting data's columns, decide the best \
way to chart this data.

Respond with ONLY a JSON object (no markdown, no explanation) in this exact format:
{
  "chart_type": "bar" | "line" | "scatter" | "none",
  "x_column": "<column name to use for x-axis>",
  "y_column": "<column name to use for y-axis>",
  "title": "<a short descriptive title for the chart>"
}

Rules:
- Use "line" for time-series / trend data (dates, sequential periods).
- Use "bar" for comparing categories (e.g. top N items, counts per group).
- Use "scatter" for relationships between two numeric variables.
- Use "none" if the data has only one row, or charting wouldn't be meaningful
  (e.g. a single aggregate number with no categories to compare).
- x_column and y_column MUST be exact column names from the provided list.
"""




def decide_chart(question: str, columns: list[str]) -> dict:
    user_prompt = f"""Question: {question}

Result columns: {columns}

Chart decision (JSON only):"""

    # Try up to 2 times total -- chart decisions are quick/cheap, and a
    # transient timeout shouldn't cost the user their chart if a second
    # attempt would succeed.
    for attempt in range(2):
        try:
            raw = call_with_fallback_raw([
                {"role": "system", "content": CHART_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ], max_tokens=200)
            break
        except Exception as e:
            print(f"[decide_chart] Attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                time.sleep(1)
            else:
                return {"chart_type": "none", "x_column": None, "y_column": None, "title": None}

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).strip()

    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"chart_type": "none", "x_column": None, "y_column": None, "title": None}

    return decision


def render_chart(data: pd.DataFrame, decision: dict, output_path: str = "chart.png") -> str | None:
    """
    Renders a chart based on the LLM's structured decision, using our own
    plotting code (never executes anything the LLM wrote). Saves to output_path
    and returns that path, or None if no chart was produced.
    """
    chart_type = decision.get("chart_type")

    if chart_type == "none" or chart_type is None:
        return None

    x_col = decision.get("x_column")
    y_col = decision.get("y_column")
    title = decision.get("title") or "Chart"

    if x_col not in data.columns or y_col not in data.columns:
        print(f"[render_chart] Column mismatch -- x:{x_col}, y:{y_col} not both in {list(data.columns)}")
        return None

    fig, ax = plt.subplots(figsize=(8, 5))

    if chart_type == "bar":
        ax.bar(data[x_col].astype(str), data[y_col])
        plt.xticks(rotation=45, ha="right")

    elif chart_type == "line":
        ax.plot(data[x_col], data[y_col], marker="o")

    elif chart_type == "scatter":
        ax.scatter(data[x_col], data[y_col])

    else:
        print(f"[render_chart] Unknown chart_type '{chart_type}', skipping.")
        plt.close(fig)
        return None

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    plt.tight_layout()

    fig.savefig(output_path)
    plt.close(fig)

    return output_path


if __name__ == "__main__":
    from sql_executor import execute_sql

    question = "What are the top 5 best-selling tracks by total quantity sold?"
    sql = "SELECT t.Name, SUM(il.Quantity) AS TotalQuantity FROM Track t JOIN InvoiceLine il ON t.TrackId = il.TrackId GROUP BY t.TrackId ORDER BY TotalQuantity DESC LIMIT 5;"

    result = execute_sql(sql)
    if result["success"]:
        data = result["data"]
        print("Data:\n", data)

        decision = decide_chart(question, list(data.columns))
        print("Chart decision:", decision)

        path = render_chart(data, decision)
        print("Chart saved to:" if path else "No chart produced.", path or "")
    else:
        print("Query failed:", result["error"])