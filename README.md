# Multi-Agent-Data-Analyst

# 🤖 Multi-Agent Data Analyst

A local-first, privacy-preserving data analysis system where **multiple specialized AI agents collaborate** to answer questions about your CSV/Excel files. Ask in plain English; the system profiles the data, writes SQL or Python, executes it safely, validates the result, draws charts, and generates a report, all running on your machine with **Ollama** and orchestrated by **LangGraph**.

> No API keys. No data leaves your laptop.

---

## ✨ Features

- **Multi-agent collaboration**: Router, SQL, Python, Visualization, Validator, and Report agents working as a graph
- **Local LLMs via Ollama**: different models for different roles (coder, reasoner, lightweight router)
- **CSV / Excel understanding**: automatic data profiling (schema, dtypes, nulls, stats, samples)
- **Python code generation + sandboxed execution**
- **SQL agent** on top of DuckDB / SQLite (read-only)
- **Visualization agent** that generates Plotly charts from results
- **Report generation**: Markdown → HTML/PDF with insights and charts
- **Self-healing error handling**: failed code is sent back to the agent with the traceback (max 3 retries)
- **Validation layer**: checks for empty results, NaNs, and whether the answer actually addresses the question
- **Agent trace UI**: watch each agent work in real time (Streamlit)

---

## 🏗️ Architecture

```
User question + CSV/Excel
        │
        ▼
┌──────────────────┐
│  Data Profiler   │  (no LLM: schema + samples, keeps the prompt small)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Router / Planner │  decides: SQL? Python? both?
└────────┬─────────┘
         ▼
┌──────────────┐        ┌──────────────┐
│  SQL Agent   │   or   │ Python Agent │
└──────┬───────┘        └──────┬───────┘
       └────────┬──────────────┘
                ▼
        ┌───────────────┐
        │ Safe Executor │  (sandbox: timeout, AST checks, read-only DB)
        └───────┬───────┘
                ▼
       ┌────────────────────┐
       │ Validator / Critic │── fail ──▶ back to the failed agent (retry ≤ 3)
       └────────┬───────────┘
                ▼ pass
       ┌──────────────────┐
       │ Visualization    │
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │  Report Agent    │ → Markdown / HTML / PDF
       └──────────────────┘
```

All agents share one **LangGraph state**:

```python
class AnalystState(TypedDict):
    question: str
    schema: str          # profiler output
    plan: dict           # router decision
    code: str            # generated SQL/Python
    result: Any          # execution output
    error: str | None
    valid: bool
    retry_count: int
    failed_agent: str | None
    charts: list[str]
    report: str
```

---

## 🧠 Model Selection

Different tasks need different models. Using one giant model for everything is slow and wasteful.

| Role | Suggested Ollama model | Why |
|---|---|---|
| SQL / Python code generation | `qwen2.5-coder:14b` (or `:32b`) | Strong open coding model |
| Planner / Validator | `qwen3:14b` or a `deepseek-r1` distill | Better multi-step reasoning |
| Router (classification) | `qwen3:4b` / `llama3.1:8b` | Fast and cheap |
| Report writing | `llama3.1:8b` / `qwen3:14b` | Good natural language |

**Limited hardware?** Use `qwen2.5-coder:7b` for everything and rely on the validation loop.
Rough guide: 8B ≈ 8 GB RAM/VRAM, 14B ≈ 12–16 GB, 32B ≈ 24 GB+.
Model lineups change quickly, so check [ollama.com/library](https://ollama.com/library) for newer versions.

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph |
| LLM runtime | Ollama (+ `langchain-ollama`) |
| Data | Pandas, DuckDB |
| Visualization | Plotly |
| Reporting | Jinja2, Markdown, WeasyPrint |
| UI | Streamlit |
| Testing | Pytest |

---

## 📁 Project Structure

```
multi-agent-analyst/
├── app.py                  # Streamlit UI
├── graph.py                # LangGraph definition (nodes + edges)
├── state.py                # Shared state schema
├── config.py               # Model names, retry limits, timeouts
├── agents/
│   ├── profiler.py         # Non-LLM data profiling
│   ├── router.py           # Decides SQL / Python / both
│   ├── sql_agent.py
│   ├── python_agent.py
│   ├── viz_agent.py
│   ├── validator.py
│   └── report_agent.py
├── sandbox/
│   ├── executor.py         # Subprocess execution with timeout
│   └── safety.py           # AST checks, SQL allow-list
├── prompts/                # Prompt templates per agent
├── templates/report.html   # Jinja2 report template
├── eval/
│   ├── questions.json      # Test questions with known answers
│   └── run_eval.py         # Accuracy per model
├── data/                   # Sample datasets
├── reports/                # Generated reports
├── tests/
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running
- 16 GB RAM recommended (8 GB works with smaller models)

### 2. Clone and install

```bash
git clone https://github.com/<your-username>/multi-agent-analyst.git
cd multi-agent-analyst

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Pull the models

```bash
ollama pull qwen2.5-coder:14b
ollama pull qwen3:14b
ollama pull qwen3:4b
```

### 4. Run the app

```bash
streamlit run app.py
```

Upload a CSV/Excel file and start asking questions.

### `requirements.txt`

```
langgraph
langchain
langchain-ollama
ollama
pandas
openpyxl
duckdb
plotly
streamlit
jinja2
markdown
weasyprint
pytest
```

---

## 💬 Example Usage

**Question:** *"Which product category had the highest revenue in 2024, and how did it trend month by month?"*

| Step | Agent | What happens |
|---|---|---|
| 1 | Profiler | Extracts schema: `order_date`, `category`, `revenue`, ... |
| 2 | Router | Plans a SQL aggregation plus a time-series chart |
| 3 | SQL Agent | Writes `SELECT category, SUM(revenue) ...` |
| 4 | Executor | Runs the query in read-only DuckDB |
| 5 | Validator | Confirms the result is non-empty and answers the question |
| 6 | Viz Agent | Generates a Plotly line chart |
| 7 | Report Agent | Writes the insights and exports an HTML/PDF report |

---

## 🛡️ Error Handling & Safety

**Self-healing loop:** on failure, the `traceback + original code + schema` go back to the agent, which fixes most errors in 1–2 tries. After 3 failed retries the system returns a partial answer with an explanation instead of looping forever.

**Validator checks:**
- Did execution succeed?
- Is the result empty, all-NaN, or suspiciously large?
- Does the result actually answer the question? (LLM judge)
- Cross-check: key numbers computed via both SQL and Pandas must match

**Sandbox rules:**
- Code runs in a **subprocess with a 30s timeout** (Docker recommended for stronger isolation)
- `ast` parsing blocks `os`, `subprocess`, `open`, `eval`, `exec`, and network imports before execution
- SQL is **`SELECT`-only** on a read-only connection; `DROP`/`DELETE`/`UPDATE`/`INSERT` are rejected

---

## 🧩 Key Design Decisions

| Decision | Reasoning |
|---|---|
| **Profiler is non-LLM** | Local models have small context windows. Sending only schema + samples (not full data) is the biggest accuracy and speed win. |
| **DuckDB for SQL** | Reads CSV/Excel directly, fast for analytics, no server to run. |
| **Different models per role** | Small models handle routing quickly; larger coder models are reserved for code generation. |
| **LangGraph, not a plain loop** | Gives explicit state, conditional edges, retry cycles, and checkpointing, which error handling needs. |
| **Structured (JSON) LLM output** | Makes parsing reliable and avoids brittle regex over free text. |
| **Column names injected into prompts** | Most code hallucinations come from wrong column names. |
| **Retry cap of 3** | Prevents infinite loops while still fixing most errors. |

---

## 🧪 Evaluation

A test set of questions with known answers lives in `eval/questions.json`.

```bash
python eval/run_eval.py --model qwen2.5-coder:14b
```

Tracks execution success rate, answer accuracy, average retries, and latency, so you can compare models objectively.

---

## 🗺️ Roadmap

- [x] Phase 1: Data loading + profiler + Ollama setup
- [ ] Phase 2: Individual agents (SQL, Python, Viz, Report)
- [ ] Phase 3: Safe execution sandbox
- [ ] Phase 4: LangGraph orchestration
- [ ] Phase 5: Validator + self-healing retries
- [ ] Phase 6: Streamlit UI + report export
- [ ] Phase 7: Planner agent for complex questions, auto-EDA mode, multi-file joins, Docker sandbox

---

## ⚠️ Known Limitations

- Local models can still generate incorrect code, so always review critical results.
- Very large files (millions of rows) should be handled through DuckDB rather than loaded into memory.
- Answer quality depends heavily on model size and available hardware.

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes and open a Pull Request

---

## 📄 License

MIT License. See `LICENSE` for details.

---

## 👤 Author

**Premanshu**
B.Tech Data Science, Lovely Professional University
GitHub: [@your-username](https://github.com/your-username)

---

⭐ If you found this useful, consider starring the repo!
