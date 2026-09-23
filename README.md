# Multi-Agent-Data-Analyst

# 🤖 Multi-Agent Data Analyst

> **A Jev-powered, local-first AI data analyst that combines fast decision-making with local LLMs to analyze CSV and Excel files.**

Ask questions about your data in plain English. The system automatically profiles the dataset, decides the best analysis strategy, generates SQL or Python using a local LLM, executes it safely, validates the result, creates visualizations, and generates a complete analytical report.

### **Jev decides. LLMs generate. LangGraph orchestrates.**

---

## ✨ Highlights

* 🧠 **Jev-powered decision engine**
* 🤖 **Local LLMs through Ollama**
* 📊 **CSV & Excel analysis**
* 🐍 **Python/Pandas analysis**
* 🗄️ **DuckDB SQL analytics**
* 🔄 **Self-healing agent workflow**
* 🛡️ **Sandboxed code execution**
* 📈 **Automatic Plotly visualizations**
* 📝 **AI-generated reports**
* 🔍 **Validation and confidence checks**
* 🕸️ **LangGraph multi-agent orchestration**
* 🖥️ **Interactive Streamlit interface**
* 🔐 **Local-first data processing**

---

# 🧠 Why Jev + LLM?

Instead of asking one LLM to perform every task, this project separates **decision-making** from **generation**.

```text
                 ┌─────────────────┐
                 │      Jev        │
                 │ Decision Engine │
                 └────────┬────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
       Routing        Validation        Retry
          │               │               │
          └───────────────┼───────────────┘
                          ↓
                 ┌─────────────────┐
                 │   Local LLM     │
                 │     Ollama      │
                 └────────┬────────┘
                          │
                 ┌────────┼────────┐
                 ↓        ↓        ↓
                SQL     Python   Reports
```

### Jev handles

* SQL vs Python vs BOTH decisions
* Agent selection
* Validation decisions
* Retry decisions
* Visualization selection
* Confidence-based routing
* Workflow branching

### LLMs handle

* SQL generation
* Python generation
* Code correction
* Data interpretation
* Insight generation
* Natural-language explanations
* Report generation

This prevents the generative LLM from being unnecessarily used for simple bounded decisions.

---

# 🏗️ Architecture

```text
                         User
                          │
                          ▼
                 ┌─────────────────┐
                 │   Streamlit UI  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Data Profiler  │
                 │ Pandas / DuckDB │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │      Jev        │
                 │ Planner/Router  │
                 └────────┬────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
           SQL Agent   Python Agent   BOTH
              │           │           │
              └───────────┼───────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Local LLM      │
                 │ Ollama + Coder  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Safe Executor  │
                 │ Python + DuckDB │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │      Jev        │
                 │    Validator    │
                 └────────┬────────┘
                          │
                    ┌─────┴─────┐
                    │           │
                   PASS        FAIL
                    │           │
                    ▼           ▼
             Visualization    Retry
                    │           │
                    │           └──────► Agent
                    ▼
             ┌───────────────┐
             │ Report Agent  │
             └───────┬───────┘
                     │
                     ▼
                HTML / PDF
```

---

# 🔄 How It Works

## 1. Upload Data

Supported formats:

```text
.csv
.xlsx
.xls
```

The system automatically profiles the dataset.

Example:

```text
Rows: 125,430

Columns:
- order_date
- customer_id
- category
- product
- quantity
- revenue

Missing Values:
- customer_id: 2.1%
- category: 0%
- revenue: 0%
```

---

## 2. Ask a Question

Example:

> **Which product category generated the highest revenue in 2024 and how did it trend month by month?**

---

## 3. Jev Plans the Analysis

Jev converts the question into a structured decision.

Example:

```json
{
  "method": "SQL",
  "requires_time_series": true,
  "group_by": ["category", "month"],
  "visualization": "line_chart",
  "validation": true
}
```

---

## 4. LLM Generates Code

The local coding model receives the structured plan and dataset schema.

Example:

```sql
SELECT
    category,
    DATE_TRUNC('month', order_date) AS month,
    SUM(revenue) AS revenue
FROM sales
WHERE EXTRACT(YEAR FROM order_date) = 2024
GROUP BY category, month
ORDER BY month;
```

---

## 5. Safe Execution

Generated code is checked before execution.

```text
Generated Code
      ↓
Safety Validation
      ↓
Sandbox
      ↓
Timeout
      ↓
Execution
      ↓
Result
```

---

## 6. Jev Validates the Result

Jev evaluates whether the execution should continue.

Possible decisions:

```text
ACCEPT
RETRY
SWITCH_METHOD
REJECT
```

---

## 7. Self-Healing

If the generated code fails:

```text
LLM
 ↓
Generated Code
 ↓
Execution
 ↓
ERROR
 ↓
Jev
 ↓
RETRY
 ↓
LLM
 ↓
Corrected Code
```

Retries are limited to prevent infinite loops.

---

## 8. Visualization

The system automatically selects an appropriate chart.

Supported visualizations include:

* Line charts
* Bar charts
* Scatter plots
* Histograms
* Box plots
* Time-series charts
* Category comparisons

Charts are generated using **Plotly**.

---

## 9. Report Generation

The report agent produces:

* Executive summary
* Key insights
* Data tables
* Visualizations
* Analysis methodology
* Validation status

Export formats:

```text
Markdown
HTML
PDF
```

---

# 🧠 Multi-Agent System

| Component           | Responsibility      | Technology      |
| ------------------- | ------------------- | --------------- |
| Data Profiler       | Schema & statistics | Pandas          |
| Planner             | Analysis strategy   | **Jev**         |
| SQL Agent           | SQL generation      | Local LLM       |
| Python Agent        | Python generation   | Local LLM       |
| Executor            | Safe execution      | Python / DuckDB |
| Validator           | Result validation   | **Jev + LLM**   |
| Visualization Agent | Chart generation    | Plotly          |
| Report Agent        | Report generation   | Local LLM       |
| Orchestrator        | Workflow management | LangGraph       |
| UI                  | User interface      | Streamlit       |

---

# 🧩 Shared LangGraph State

```python
class AnalystState(TypedDict):
    question: str
    schema: str

    # Jev decisions
    decision: dict
    confidence: float

    # Agent execution
    selected_agent: str
    code: str
    code_type: str

    # Results
    result: Any
    error: str | None

    # Validation
    valid: bool
    validation_reason: str

    # Retry
    retry_count: int
    failed_agent: str | None

    # Output
    charts: list[str]
    insights: list[str]
    report: str
```

---

# 🧠 Model Strategy

The project uses different models for different tasks.

### Decision Layer

**Jev**

Used for:

```text
Routing
Classification
Agent selection
Validation
Retry decisions
Workflow branching
```

### Generation Layer

Local models through Ollama.

Recommended starting models:

```text
Qwen3-Coder
Qwen3
```

Example configuration:

```python
CODER_MODEL = "qwen3-coder"
REASONING_MODEL = "qwen3"
```

Models can be changed through the project configuration without changing the architecture.

---

# 🛠️ Tech Stack

| Category        | Technology                |
| --------------- | ------------------------- |
| Decision Engine | **Jev**                   |
| LLM Runtime     | **Ollama**                |
| Coding LLM      | **Qwen3-Coder**           |
| Reasoning LLM   | **Qwen3**                 |
| Orchestration   | **LangGraph**             |
| Data Processing | **Pandas**                |
| SQL Analytics   | **DuckDB**                |
| Excel           | **OpenPyXL**              |
| Visualization   | **Plotly**                |
| UI              | **Streamlit**             |
| Templates       | **Jinja2**                |
| Reports         | **Markdown / WeasyPrint** |
| Testing         | **Pytest**                |

---

# 📁 Project Structure

```text
multi-agent-analyst/
│
├── app.py
├── graph.py
├── state.py
├── config.py
│
├── agents/
│   ├── profiler.py
│   ├── jev_planner.py
│   ├── sql_agent.py
│   ├── python_agent.py
│   ├── viz_agent.py
│   ├── jev_validator.py
│   └── report_agent.py
│
├── decision/
│   ├── jev_client.py
│   ├── schemas.py
│   └── policies.py
│
├── sandbox/
│   ├── executor.py
│   └── safety.py
│
├── prompts/
│   ├── sql.txt
│   ├── python.txt
│   └── report.txt
│
├── templates/
│   └── report.html
│
├── eval/
│   ├── questions.json
│   └── run_eval.py
│
├── data/
│   └── sample.csv
│
├── reports/
│
├── tests/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 🚀 Installation

## Prerequisites

* Python 3.10+
* Ollama
* Jev access/configuration
* Git
* 16 GB RAM recommended for larger local models

---

## 1. Clone

```bash
git clone https://github.com/<your-username>/multi-agent-analyst.git

cd multi-agent-analyst
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Local Models

Start Ollama and pull the models configured for the project.

Example:

```bash
ollama pull qwen3-coder
ollama pull qwen3
```

---

## 5. Configure Environment

Create a `.env` file:

```env
JEV_API_KEY=your_jev_key
JEV_MODEL=your_jev_model

OLLAMA_BASE_URL=http://localhost:11434

CODER_MODEL=qwen3-coder
REASONING_MODEL=qwen3
```

### Never commit `.env`

Make sure:

```text
.env
```

is included in `.gitignore`.

---

## 6. Run

```bash
streamlit run app.py
```

Then upload your dataset and start asking questions.

---

# 🔐 Security

Generated code is treated as **untrusted input**.

## Python Protection

The execution layer can enforce:

* AST validation
* Restricted imports
* Subprocess execution
* Execution timeouts
* Restricted filesystem access
* Network restrictions

Potentially dangerous operations such as:

```text
os
subprocess
socket
requests
eval
exec
```

should be blocked according to the configured sandbox policy.

For stronger isolation, Docker-based execution is recommended.

---

## SQL Protection

The SQL agent is restricted to analytical queries.

Allowed:

```sql
SELECT ...
```

Blocked:

```text
DROP
DELETE
UPDATE
INSERT
ALTER
CREATE
ATTACH
```

DuckDB is used for local analytical workloads.

---

# 🔄 Error Handling

The system supports automatic recovery from generated-code failures.

```text
           Generate
               ↓
            Execute
               ↓
             Error?
           /       \
         NO         YES
         ↓           ↓
     Validate       Jev
                     ↓
               Retry decision
                     ↓
                  LLM Agent
                     ↓
                Correct code
                     ↓
                  Execute
```

Maximum retries:

```python
MAX_RETRIES = 3
```

If all retries fail, the system returns an explanation instead of looping indefinitely.

---

# 🧪 Evaluation

The project includes an evaluation framework for measuring agent performance.

Metrics include:

* Execution success rate
* Answer accuracy
* Jev routing accuracy
* Validation accuracy
* Average retries
* Average latency
* LLM calls per question
* Failed executions

Example:

```bash
python eval/run_eval.py
```

---

# 📊 Jev vs LLM Benchmark

One of the project's experimental goals is to measure the difference between specialized decision-making and generative decision-making.

```text
                  Decision Task
                       │
              ┌────────┴────────┐
              ↓                 ↓
             Jev               LLM
              │                 │
              └────────┬────────┘
                       ↓
                  Evaluation
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       Accuracy      Latency       Cost
```

This can help determine where a specialized decision model provides an advantage over using an LLM for every workflow decision.

---

# 🗺️ Roadmap

## Phase 1 — Foundation

* [x] Project architecture
* [ ] CSV/Excel upload
* [ ] Data profiler
* [ ] Ollama integration
* [ ] Jev integration

## Phase 2 — Agents

* [ ] Jev Planner
* [ ] SQL Agent
* [ ] Python Agent
* [ ] Visualization Agent
* [ ] Report Agent

## Phase 3 — Execution

* [ ] DuckDB execution
* [ ] Python sandbox
* [ ] AST safety checks
* [ ] Timeout handling
* [ ] SQL allow-list

## Phase 4 — LangGraph

* [ ] Shared state
* [ ] Conditional edges
* [ ] Jev decision nodes
* [ ] Agent nodes
* [ ] Retry cycles

## Phase 5 — Validation

* [ ] Jev validator
* [ ] Result validation
* [ ] Empty-result detection
* [ ] NaN detection
* [ ] SQL/Pandas cross-check
* [ ] Self-healing retries

## Phase 6 — UI

* [ ] Streamlit dashboard
* [ ] Agent trace
* [ ] SQL/Python viewer
* [ ] Interactive charts
* [ ] Report export

## Phase 7 — Advanced

* [ ] Multi-file joins
* [ ] Automatic EDA
* [ ] Docker sandbox
* [ ] Dataset versioning
* [ ] Jev vs LLM benchmarking
* [ ] Model performance dashboard

---

# ⚠️ Limitations

* Local LLMs may generate incorrect SQL or Python.
* Decision quality depends on the Jev configuration and decision schema.
* Complex questions may require multiple analysis steps.
* Very large datasets should primarily be processed using DuckDB.
* Strong isolation should use Docker or another hardened sandbox.
* Local LLM performance depends on available hardware.
* Model capabilities and names can change over time.

---

# 🎯 Project Goal

The goal is to build a **decision-driven AI Data Analyst**, rather than another simple LLM chatbot.

The system separates:

```text
Decision Making
       ↓
      Jev

Generation & Reasoning
       ↓
     Local LLM

Workflow
       ↓
   LangGraph

Data
       ↓
Pandas + DuckDB
```

This architecture makes the system more modular, testable, and suitable for experimenting with different decision models and LLMs.

---

# 🤝 Contributing

Contributions are welcome.

```bash
git checkout -b feature/your-feature
```

Make your changes, add tests, and submit a pull request.

## 👥 Contributors

* **Cloud**

---

# 📄 License

This project is licensed under the **MIT License**.

See `LICENSE` for details.

---

# 👤 Author

### Premanshu Kumar

**B.Tech Computer Science Engineering — Data Science**

Lovely Professional University

GitHub: **@Premanshu-Kumar**

---

# ⭐ Project Summary

> **Ask your data anything. Jev decides the path. Local LLMs generate the solution. LangGraph orchestrates the workflow. The system validates, visualizes, and explains the answer.**

### Built With

**Jev · Ollama · Qwen3-Coder · Qwen3 · LangGraph · DuckDB · Pandas · Plotly · Streamlit · Python**

⭐ If you find this project useful, consider giving it a star!

