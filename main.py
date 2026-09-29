from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import os

from agent_graph import graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://textedsql.vercel.app/", "http://textedsql.vercel.app/"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask_question(request: QuestionRequest):
    initial_state = {
        "question": request.question,
        "sql": None,
        "error": None,
        "data": None,
        "retry_count": 0,
        "max_retries": 3,
        "success": False,
        "chart_path": None,
    }

    final_state = graph.invoke(initial_state)

    data_records = (
        final_state["data"].to_dict(orient="records")
        if final_state["data"] is not None
        else None
    )

    chart_base64 = None
    if final_state["chart_path"] and os.path.exists(final_state["chart_path"]):
        with open(final_state["chart_path"], "rb") as f:
            chart_base64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "success": final_state["success"],
        "sql": final_state["sql"],
        "error": final_state["error"],
        "retry_count": final_state["retry_count"],
        "data": data_records,
        "chart_base64": chart_base64,
    }