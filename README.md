# Multi-Agent-Data-Analyst


Multi-Agent Data Analyst: Phase-wise Architecture
Big picture
User question + CSV/Excel
        │
        ▼
┌──────────────────┐
│  Router/Planner  │  decides: SQL? Python? Chart? Report?
└──────┬───────────┘
       ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Data Profiler│──▶│  SQL Agent   │   │ Python Agent │
└──────────────┘   └──────┬───────┘   └──────┬───────┘
                          └────────┬─────────┘
                                   ▼
                        ┌────────────────────┐
                        │ Validator / Critic │──fail──▶ back to agent (max 3 retries)
                        └─────────┬──────────┘
                                  ▼ pass
                    ┌──────────────────────┐
                    │  Visualization Agent │
                    └─────────┬────────────┘
                              ▼
                    ┌──────────────────────┐
                    │   Report Agent       │ → Markdown / PDF / HTML
                    └──────────────────────┘

Shared LangGraph state carries everything between agents: question, schema, plan, code, result, error, retry_count, charts, report.

Phase 1: Foundation (Data + LLM setup)

Goal: load a file, understand it, talk to a local LLM.

Install Ollama and pull models.
Build a file loader: CSV/Excel → Pandas DataFrame.
Build a Data Profiler (no LLM needed): columns, dtypes, nulls, unique counts, sample rows, basic stats. Output is a compact text summary.
Load the DataFrame into SQLite or DuckDB so the SQL agent has a real database.

Why the profiler is non-LLM: a local model has a small context window. Sending 1M rows would break it, so you send only the schema and a few sample rows. This one decision improves accuracy the most.

Why DuckDB: it reads CSV/Excel directly, runs fast analytical queries, and needs no server.

Phase 2: Single agents (build each one alone first)
Agent	Input	Output
SQL Agent	question + schema	SQL query → result table
Python Agent	question + profile	Pandas code → result
Viz Agent	result data + question	Plotly/Matplotlib code → chart
Report Agent	all results	Written insights

Test each with 10-20 fixed questions before connecting anything.

Code generation rules:

Force structured output (JSON with a code field) so parsing is reliable.
Give the model the exact column names in the prompt. Most hallucinations come from wrong column names.
Use few-shot examples (2-3 good question→code pairs).
Phase 3: Safe execution sandbox

Never exec() LLM code directly in your main process.

Minimum: run the code in a subprocess with a timeout (~30s), restricted imports, and no network.
Better: run it in a Docker container with no network and limited memory.
SQL safety: allow only SELECT. Block DROP, DELETE, UPDATE, INSERT, and use a read-only connection.
Static check: parse the code with Python's ast module and reject os, subprocess, open, and eval before running it.
Phase 4: LangGraph orchestration

Nodes: profiler, router, sql_agent, python_agent, executor, validator, viz_agent, report_agent

Conditional edges are what make it a real multi-agent system rather than a linear chain:

python
def route(state):
    return state["plan"]["tool"]          # "sql" | "python" | "both"

def after_validation(state):
    if state["valid"]:
        return "viz_agent"
    if state["retry_count"] >= 3:
        return "report_agent"             # fail gracefully
    return state["failed_agent"]          # retry the same agent with the error message

Why LangGraph over a plain loop: it gives you explicit state, conditional branching, retry cycles, and checkpointing. Those are what error handling needs.

Phase 5: Error handling + validation (the advanced part)
Self-healing loop: if execution fails, send the traceback + original code + schema back to the agent. This fixes most errors in 1-2 tries.
Validator/Critic agent checks:
Did the code run without errors?
Is the result empty, all NaN, or suspiciously huge?
Does the result actually answer the question? (LLM judge)
Cross-check: for important numbers, compute the answer via SQL and Pandas and compare. A mismatch triggers a retry.
Retry cap and fallback: after 3 failures, return a partial answer with an explanation instead of looping forever.
Logging: log every prompt, code, error, and retry. It's great for debugging and looks impressive in a demo.
Phase 6: Reporting + UI
Report Agent takes the results, charts, and insights and produces a Markdown report, then converts it to HTML or PDF (Jinja2 template + WeasyPrint).
Streamlit UI with file upload, chat box, live agent trace ("SQL Agent running..."), chart display, and a download-report button.
Memory: keep chat history so follow-ups like "now break that down by region" work.
Phase 7 (optional): Advanced extras
Planner agent that breaks a big question ("why did sales drop?") into sub-questions, runs them in parallel, then merges.
Auto-EDA mode with no question needed: it finds trends, outliers, and correlations by itself.
Multiple files with automatic join detection.
Evaluation set: 30-50 questions with known answers, with accuracy tracked per model. This is very strong for a resume.
Which local LLM to use

Don't use one model for everything. Match model size to task:

Role	Suggested model (Ollama)	Why
Code + SQL generation	Qwen2.5-Coder 14B / 32B	Among the best open coding models
Planner / Validator (reasoning)	Qwen3 (14B-32B) or a DeepSeek-R1 distill	Better multi-step reasoning
Router / simple classification	Qwen3 4B–8B or Llama 3.x 8B	Fast and cheap
Report writing	Llama 3.x 8B / Qwen3 14B	Good natural-language quality

Rough hardware guide: 8B needs about 8 GB RAM/VRAM, 14B about 12-16 GB, and 32B about 24 GB+. If your laptop is limited, use Qwen2.5-Coder 7B for everything and lean on the validation loop. Model lineups change fast, so check ollama.com/library for the newest versions of these families.

Use LangChain's ChatOllama or the ollama Python library, with format="json" for structured outputs.

Suggested folder structure
multi-agent-analyst/
├── app.py                 # Streamlit UI
├── graph.py               # LangGraph definition
├── state.py               # TypedDict state
├── agents/
│   ├── router.py
│   ├── profiler.py
│   ├── sql_agent.py
│   ├── python_agent.py
│   ├── viz_agent.py
│   ├── validator.py
│   └── report_agent.py
├── sandbox/executor.py    # safe code execution
├── prompts/               # prompt templates
├── eval/questions.json    # test set
└── reports/
