# Text-to-SQL Analytics Agent

A natural language interface to a SQL database. Ask a question in plain English, and the agent inspects the database schema, generates SQL, validates and executes it safely, self-corrects if the query fails, and produces a chart of the results — all through a React frontend backed by a LangGraph agent.

**Live demo:** [https://textedsql.vercel.app/]

---

## What it does

1. You type a question like *"What are the top 5 best-selling tracks by total quantity sold?"*
2. The agent inspects the database's schema (tables, columns, foreign keys) at runtime
3. An LLM generates a SQL query using that schema as context
4. The query is validated (read-only, single-statement, SQL-injection-safe) and executed against a live SQLite database
5. If the query fails, the error is fed back to the LLM, which corrects itself — up to 3 retries
6. On success, the LLM decides on an appropriate chart type, and a chart is rendered
7. Results (SQL, data table, chart) are streamed back to the UI in real time, with live status updates

---

## Architecture

```
┌─────────────┐      HTTP/SSE      ┌──────────────┐
│   React     │ ─────────────────► │   FastAPI    │
│  Frontend   │ ◄───────────────── │   Backend    │
└─────────────┘                    └──────┬───────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │  LangGraph Agent │
                                  └─────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
            ┌───────────────┐    ┌────────────────┐    ┌──────────────────┐
            │ generate_sql  │───►│  execute_sql    │───►│  generate_chart  │
            │ (LLM call)    │    │ (validated,     │    │ (LLM decision +  │
            │               │    │  read-only)     │    │  matplotlib)     │
            └───────▲───────┘    └────────┬────────┘    └──────────────────┘
                    │                     │
                    └─────── on error ────┘
                        (retry, up to 3x)
```

### The retry loop, in detail

```
[generate_sql] → [execute_sql] ──success──► [generate_chart] → [END]
       ▲                │
       └────error────────┘
      (loop back, up to max_retries; exhausted → give up gracefully)
```

This is the core "agentic" behavior: when generated SQL fails (syntax error, hallucinated column name, etc.), the actual error message is fed back into the next prompt along with the failed query, and the LLM attempts a correction. The graph tracks retry count and gives up gracefully — returning a clear error instead of looping forever — if the limit is exceeded.

---

## Tech stack, and why

| Choice | Reasoning |
|---|---|
| **SQLite + Chinook sample DB** | Realistic relational schema (customers, invoices, tracks), zero setup, free |
| **SQLAlchemy** for schema introspection | Database-agnostic — the same code works against Postgres/MySQL by changing one connection string |
| **LangGraph** for orchestration | The core requirement is a *loop* (generate → execute → retry on error), not a linear chain. A state graph models this naturally |
| **sqlglot** for SQL validation | Parses and verifies the LLM's output is a single, safe `SELECT` statement before it ever touches the database — rejects `DROP`, `DELETE`, multi-statement injection attempts, etc. |
| **Multi-provider LLM fallback** (NVIDIA NIM, OpenRouter, Gemini) | Free-tier LLM APIs are individually unreliable (rate limits, quota exhaustion, model deprecation). A fallback chain across providers makes the agent resilient to any single provider being temporarily unavailable |
| **FastAPI** backend | OpenAI-compatible async framework, trivial to wrap the LangGraph agent in an HTTP API, built-in request validation via Pydantic |
| **React + Vite + Tailwind** frontend | Fast dev experience, utility-first styling for quick iteration |
| **Server-Sent Events (SSE)** | Streams live status updates ("Generating SQL...", "Running query...") to the frontend as the agent works, rather than a silent multi-second wait |

---

## Key design decisions

**Read-only database access, enforced at two layers.** The SQLite connection itself is opened in read-only mode (`mode=ro`) at the OS/file level, *and* every query is independently validated with `sqlglot` to confirm it's a single `SELECT` statement before execution. Neither layer trusts the other — this is deliberate defense in depth, since relying on a single safeguard against LLM-generated SQL felt insufficient.

**Chart generation never executes LLM-written code.** The LLM only returns a structured JSON decision (chart type, axis columns, title) — the actual plotting is done by fixed, pre-written matplotlib code that branches on the decision. This avoids the much harder problem of safely sandboxing arbitrary generated Python, at the cost of a fixed menu of chart types.

**Failures are handled explicitly at every layer**, not just caught generically:
- Empty LLM responses (some models return nothing under certain conditions) are detected and treated as a failure, triggering fallback to the next model
- Reasoning-style models that exhaust their token budget "thinking" before producing an answer are detected via `finish_reason == "length"` and skipped
- SQL extraction correctly handles both plain `SELECT` queries and `WITH`-prefixed CTE queries — matching whichever keyword appears first, since a naive `SELECT`-only match truncates CTEs
- Chart generation failures are non-fatal — the agent still returns valid data and SQL even if charting fails

---

## Example: the retry loop in action

Given the intentionally ambiguous question *"What's the average invoice total per customer, but only for customers whose favorite genre is Rock, ordered by their spending rank?"* — there is no `favorite_genre` column in the schema, so the agent must derive it.

**Attempt 1** failed (truncated CTE, incomplete reasoning). **Attempt 2** produced a working query:

```sql
WITH customer_genre_qty AS (
    SELECT i.CustomerId, g.Name AS GenreName, SUM(il.Quantity) AS Qty
    FROM Invoice i
    JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId
    JOIN Track t ON t.TrackId = il.TrackId
    JOIN Genre g ON g.GenreId = t.GenreId
    GROUP BY i.CustomerId, g.Name
),
ranked_genres AS (
    SELECT CustomerId, GenreName, Qty,
           ROW_NUMBER() OVER (PARTITION BY CustomerId ORDER BY Qty DESC, GenreName) AS rn
    FROM customer_genre_qty
),
rock_fans AS (
    SELECT CustomerId FROM ranked_genres WHERE rn = 1 AND GenreName = 'Rock'
),
customer_invoices AS (
    SELECT i.CustomerId, AVG(i.Total) AS AvgInvoiceTotal, SUM(i.Total) AS TotalSpending
    FROM Invoice i
    JOIN rock_fans rf ON rf.CustomerId = i.CustomerId
    GROUP BY i.CustomerId
)
SELECT c.CustomerId, c.FirstName, c.LastName, ci.AvgInvoiceTotal,
       RANK() OVER (ORDER BY ci.TotalSpending DESC) AS SpendingRank
FROM customer_invoices ci
JOIN Customer c ON c.CustomerId = ci.CustomerId
ORDER BY SpendingRank, c.CustomerId;
```

The agent correctly inferred "favorite genre" as the genre with the highest purchase quantity per customer, using a `ROW_NUMBER()` window function — a non-trivial query it derived entirely on its own from an ambiguous English question.

---

## Notable challenges solved during development

- **Environment isolation**: a silently-active conda `base` environment was shadowing the project's venv, causing dependency and Python-version mismatches that produced confusing, unrelated-looking errors
- **Free-tier LLM reliability**: individual providers hit daily/per-minute quotas mid-session; solved with an ordered multi-provider fallback chain and explicit detection of "successful but empty" responses
- **Reasoning-model token exhaustion**: some models spent their entire token budget on visible chain-of-thought reasoning before writing an answer, returning `content: None`; detected via the response's `finish_reason` field and handled by skipping to the next model
- **SQL extraction regex bug**: an early regex matched the first occurrence of `SELECT` anywhere in the text, which incorrectly truncated `WITH ... AS (` CTE prefixes; fixed by matching whichever of `WITH`/`SELECT` appears first
- **CORS deployment issue**: a trailing-slash mismatch between the configured allowed origin and the browser's actual `Origin` header (which never includes a trailing slash) caused all cross-origin requests to be silently rejected

---

## Limitations and possible future work

- Free-tier LLMs are inherently unreliable for a production setting; a paid tier or self-hosted model would remove most of the retry/fallback complexity
- Chart generation is limited to a fixed set of types (bar, line, scatter) since it avoids executing LLM-generated code
- No conversational memory — each question is independent, no follow-up question support
- Schema context is sent in full on every request; a larger database would need retrieval-based schema selection instead
- Deployed on free-tier hosting (Render + Vercel), which has cold-start delays and resource constraints

---

## Running locally

### Backend
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# create a .env file with: NVIDIA_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

---

## Tech stack summary

**Backend:** Python, FastAPI, LangGraph, SQLAlchemy, sqlglot, pandas, matplotlib
**Frontend:** React, Vite, Tailwind CSS
**Database:** SQLite (Chinook sample dataset)
**LLM providers:** NVIDIA NIM, OpenRouter, Google Gemini (free tiers, multi-provider fallback)
**Deployment:** Render (backend), Vercel (frontend)
