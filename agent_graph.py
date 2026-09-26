from langgraph.graph import StateGraph, START, END

from agent_state import AgentState
from schema_inspector import get_schema_context
from sql_generator import call_with_fallback, SYSTEM_PROMPT
from sql_executor import execute_sql


def generate_sql_node(state: AgentState) -> dict:
    print(f"\n[generate_sql] Attempt {state['retry_count'] + 1}")
    schema = get_schema_context()

    if state.get("error"):
        user_prompt = f"""Schema:
{schema}

Question: {state['question']}

Your previous SQL attempt was:
{state['sql']}

It failed with this error:
{state['error']}

Please fix the SQL and return only the corrected query."""
    else:
        user_prompt = f"""Schema:
{schema}

Question: {state['question']}

SQL query:"""

    try:
        sql = call_with_fallback([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
    except RuntimeError as e:
        return {
            "sql": None,
            "error": f"SQL generation failed: {e}",
            "retry_count": state["retry_count"] + 1,
        }

    return {"sql": sql}

def execute_sql_node(state: AgentState) -> dict:
    if state["sql"] is None:
        print("[execute_sql] Skipping execution -- no SQL was generated.")
        return {
            "data": None,
            "error": state.get("error", "No SQL was generated."),
            "success": False,
            # Note: retry_count was already incremented in generate_sql_node's
            # except block when generation failed, so we don't increment again here.
        }

    print(f"[execute_sql] Running SQL:\n{state['sql']}")
    result = execute_sql(state["sql"])

    if result["success"]:
        print("[execute_sql] SUCCESS")
        return {"data": result["data"], "error": None, "success": True}
    else:
        print(f"[execute_sql] FAILED: {result['error']}")
        return {
            "data": None,
            "error": result["error"],
            "success": False,
            "retry_count": state["retry_count"] + 1,
        }

def route_after_execution(state: AgentState) -> str:
    """Decides whether to retry, give up, or finish."""
    if state["success"]:
        return "done"
    if state["retry_count"] >= state["max_retries"]:
        return "give_up"
    return "retry"


# --- Build the graph ---
builder = StateGraph(AgentState)

builder.add_node("generate_sql", generate_sql_node)
builder.add_node("execute_sql", execute_sql_node)

builder.add_edge(START, "generate_sql")
builder.add_edge("generate_sql", "execute_sql")

builder.add_conditional_edges(
    "execute_sql",
    route_after_execution,
    {
        "done": END,
        "give_up": END,
        "retry": "generate_sql",
    },
)

graph = builder.compile()


if __name__ == "__main__":
    initial_state = {
        "question": "What's the average invoice total per customer, but only for customers whose favorite genre is Rock, ordered by their spending rank?",
        "sql": None,
        "error": None,
        "data": None,
        "retry_count": 0,
        "max_retries": 3,
        "success": False,
    }

    final_state = graph.invoke(initial_state)

    print("\n--- FINAL STATE ---")
    print("Success:", final_state["success"])
    print("SQL used:", final_state["sql"])
    print("Retry count:", final_state["retry_count"])
    if final_state["success"]:
        print("Data:\n", final_state["data"])
    else:
        print("Final error:", final_state["error"])