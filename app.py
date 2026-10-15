"""
Streamlit UI for Multi-Agent Data Analyst
Phase 7: Advanced features — Multi-file joins, Auto EDA, Dataset Versioning,
         Jev vs LLM Benchmarking, Model Performance Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from io import BytesIO

from agents.profiler import DataProfiler
from agents.ollama_client import OllamaClient
from agents.auto_eda_agent import AutoEDAAgent
from agents.multi_file_joiner import MultiFileJoiner, JoinConfig
from agents.dataset_versioning import DatasetVersionManager
from decision.jev_client import JevClient
from graph import AnalystWorkflow
from eval.performance_dashboard import ModelPerformanceDashboard
from eval.jev_vs_llm_benchmark import JevVsLLMBenchmark
import config

# ──────────────────────────────────────────────────────────────────────
#  Page configuration
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Data Analyst",
    page_icon="🤖",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────
#  Session state initialisation
# ──────────────────────────────────────────────────────────────────────
defaults = {
    "df": None,
    "profile": None,
    "file_path": None,
    "workflow_result": None,
    "question_history": [],
    # Phase 7
    "joiner": None,
    "joined_df": None,
    "joined_profile": None,
    "eda_report": None,
    "version_manager": DatasetVersionManager(),
    "perf_dashboard": ModelPerformanceDashboard(),
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────
#  Header
# ──────────────────────────────────────────────────────────────────────
st.title("🤖 Multi-Agent Data Analyst")
st.markdown(
    "A Jev-powered, local-first AI data analyst — "
    "Phase 7: Multi-file joins, Auto EDA, Dataset versioning, Benchmarking & Performance dashboard."
)

# ──────────────────────────────────────────────────────────────────────
#  Sidebar
# ──────────────────────────────────────────────────────────────────────
st.sidebar.header("Configuration")

st.sidebar.subheader("Ollama Status")
ollama_client = OllamaClient()
if ollama_client.check_connection():
    st.sidebar.success("✅ Ollama Connected")
    models = ollama_client.list_models()
    if models:
        st.sidebar.write(f"Models: {', '.join(models[:4])}")
else:
    st.sidebar.error("❌ Ollama Not Connected")
    st.sidebar.info("Start with: `ollama serve`")

st.sidebar.subheader("Jev Status")
jev_client = JevClient()
if jev_client.check_connection():
    st.sidebar.success("✅ Jev Connected")
else:
    st.sidebar.warning("⚠️ Jev fallback active")

# Docker status
from sandbox.docker_sandbox import DockerSandbox
docker = DockerSandbox()
st.sidebar.subheader("Docker Sandbox")
if docker.is_available:
    st.sidebar.success("🐳 Docker Available")
else:
    st.sidebar.info("🔒 Local sandbox active (Docker optional)")

# ──────────────────────────────────────────────────────────────────────
#  Main Tabs
# ──────────────────────────────────────────────────────────────────────
tab_upload, tab_ask, tab_join, tab_eda, tab_versions, tab_benchmark, tab_perf, tab_history = st.tabs([
    "📁 Data Upload",
    "❓ Ask Questions",
    "🔗 Multi-File Join",
    "🔍 Auto EDA",
    "🗂️ Versioning",
    "⚡ Benchmark",
    "📈 Performance",
    "📊 History",
])

# ══════════════════════════════════════════════════════════════════════
#  TAB 1 — Data Upload
# ══════════════════════════════════════════════════════════════════════
with tab_upload:
    st.header("📁 Upload Your Data")

    uploaded_file = st.file_uploader(
        "Upload a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Supported: CSV, Excel (.xlsx, .xls)",
    )

    if uploaded_file:
        file_path = os.path.join(config.DATA_DIR, uploaded_file.name)
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.file_path = file_path

        try:
            profiler = DataProfiler()
            df = profiler.load_data(file_path)
            st.session_state.df = df

            profile = profiler.profile_data(df)
            st.session_state.profile = profile

            st.success(f"✅ Loaded: {uploaded_file.name}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Rows", f"{profile['row_count']:,}")
            c2.metric("Columns", profile["column_count"])
            c3.metric("Missing Cols", sum(1 for v in profile["missing_values"].values() if v > 0))

            st.subheader("📊 Schema")
            st.text(profile["schema"])

            st.subheader("👁️ Preview")
            st.dataframe(df.head(10), use_container_width=True)

            st.subheader("📋 Column Details")
            cols_df = pd.DataFrame(profile["columns"])[
                ["name", "dtype", "null_count", "null_percentage", "unique_count"]
            ]
            cols_df.columns = ["Column", "Type", "Null #", "Null %", "Unique"]
            st.dataframe(cols_df, use_container_width=True)

            # Auto-save version
            auto_save = st.checkbox("Auto-save as a dataset version", value=True)
            if auto_save:
                vm: DatasetVersionManager = st.session_state.version_manager
                dataset_name = os.path.splitext(uploaded_file.name)[0]
                version = vm.save_version(
                    dataset_name, df,
                    source_file=file_path,
                    description=f"Uploaded via UI — {uploaded_file.name}",
                )
                st.info(f"💾 Saved as version **{version.version_id}** for dataset `{dataset_name}`")

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.df = None
    else:
        st.info("👆 Upload a CSV or Excel file to begin.")

# ══════════════════════════════════════════════════════════════════════
#  TAB 2 — Ask Questions
# ══════════════════════════════════════════════════════════════════════
with tab_ask:
    st.header("❓ Ask Questions About Your Data")

    # Allow selecting joined or primary dataset
    active_df = st.session_state.joined_df if st.session_state.joined_df is not None else st.session_state.df
    active_profile = st.session_state.joined_profile if st.session_state.joined_profile is not None else st.session_state.profile

    if active_df is None:
        st.warning("⚠️ Please upload a file in the Data Upload tab first.")
    else:
        if st.session_state.joined_df is not None:
            st.info("🔗 Using **joined dataset** from Multi-File Join tab.")
        
        # Show dataset info
        col1, col2, col3 = st.columns(3)
        col1.metric("Rows", f"{len(active_df):,}")
        col2.metric("Columns", len(active_df.columns))
        col3.metric("History", f"{len(st.session_state.question_history)}")
        
        st.markdown("---")
        
        # Quick Actions Section
        st.subheader("⚡ Quick Actions")
        
        # Get column names for quick actions
        columns = active_df.columns.tolist()
        numeric_cols = active_df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = active_df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Quick action buttons
        quick_cols = st.columns(4)
        with quick_cols[0]:
            if st.button("📊 Show Summary", use_container_width=True):
                st.session_state["quick_action"] = "summary"
        with quick_cols[1]:
            if st.button("📈 Correlation", use_container_width=True, disabled=len(numeric_cols) < 2):
                st.session_state["quick_action"] = "correlation"
        with quick_cols[2]:
            if st.button("🔍 Show Head", use_container_width=True):
                st.session_state["quick_action"] = "head"
        with quick_cols[3]:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.question_history = []
                st.session_state.workflow_result = None
                st.session_state["quick_action"] = None
                st.rerun()
        
        # Column-specific quick actions
        if numeric_cols:
            st.markdown("**Quick Analysis for Numeric Columns:**")
            quick_num_cols = st.columns(min(4, len(numeric_cols)))
            for i, col in enumerate(quick_num_cols):
                if i < len(numeric_cols):
                    with quick_num_cols[i]:
                        if st.button(f"📉 {col}", use_container_width=True, key=f"quick_{col}"):
                            st.session_state["quick_action"] = f"analyze_{col}"
        
        if categorical_cols:
            st.markdown("**Quick Analysis for Categorical Columns:**")
            quick_cat_cols = st.columns(min(4, len(categorical_cols)))
            for i, col in enumerate(quick_cat_cols):
                if i < len(categorical_cols):
                    with quick_cat_cols[i]:
                        if st.button(f"📊 {col}", use_container_width=True, key=f"quick_cat_{col}"):
                            st.session_state["quick_action"] = f"count_{col}"
        
        st.markdown("---")
        
        # Suggested Questions
        st.subheader("💡 Suggested Questions")
        suggestions = []
        
        if len(numeric_cols) >= 2:
            suggestions.append(f"What is the correlation between {numeric_cols[0]} and {numeric_cols[1]}?")
        if len(categorical_cols) >= 1:
            suggestions.append(f"Count of {categorical_cols[0]} by category")
        if len(numeric_cols) >= 1:
            suggestions.append(f"What is the average {numeric_cols[0]}?")
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            suggestions.append(f"Average {numeric_cols[0]} by {categorical_cols[0]}")
        
        if suggestions:
            selected_suggestion = st.selectbox("Or try one of these:", [""] + suggestions)
            if selected_suggestion:
                st.session_state["suggested_question"] = selected_suggestion
        
        st.markdown("---")
        
        # Main Question Input
        st.subheader("🤖 Ask Your Question")
        
        # Use suggested question if selected
        default_question = st.session_state.get("suggested_question", "")
        if default_question:
            st.info(f"💡 Selected: {default_question}")
        
        question = st.text_input(
            "Your question:",
            placeholder="e.g., What is the average revenue by category?",
            value=default_question,
            key="question_input",
        )
        
        # Auto-complete for column names
        if columns:
            st.markdown("**Available columns:**")
            col_tags = " | ".join([f"`{col}`" for col in columns[:10]])
            if len(columns) > 10:
                col_tags += f" ... and {len(columns) - 10} more"
            st.markdown(col_tags)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            analyze = st.button("🚀 Analyze", type="primary", use_container_width=True)
        with col2:
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.question_history = []
                st.session_state.workflow_result = None
                st.session_state["quick_action"] = None
                st.session_state["suggested_question"] = None
                st.rerun()
        
        # Handle Quick Actions
        if st.session_state.get("quick_action") == "summary":
            with st.spinner("Generating summary..."):
                st.subheader("📊 Dataset Summary")
                st.dataframe(active_df.describe(), use_container_width=True)
                st.session_state["quick_action"] = None
        
        elif st.session_state.get("quick_action") == "correlation":
            with st.spinner("Calculating correlation..."):
                st.subheader("🔥 Correlation Matrix")
                corr = active_df[numeric_cols].corr()
                fig = px.imshow(
                    corr,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    title="Correlation Matrix",
                    aspect="auto",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.session_state["quick_action"] = None
        
        elif st.session_state.get("quick_action") == "head":
            st.subheader("👁️ First 10 Rows")
            st.dataframe(active_df.head(10), use_container_width=True)
            st.session_state["quick_action"] = None
        
        elif st.session_state.get("quick_action", "").startswith("analyze_"):
            col = st.session_state["quick_action"].replace("analyze_", "")
            with st.spinner(f"Analyzing {col}..."):
                st.subheader(f"📊 Analysis of {col}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Mean", f"{active_df[col].mean():.2f}")
                c2.metric("Max", f"{active_df[col].max():.2f}")
                c3.metric("Min", f"{active_df[col].min():.2f}")
                
                fig = px.histogram(active_df, x=col, title=f"Distribution of {col}")
                st.plotly_chart(fig, use_container_width=True)
                st.session_state["quick_action"] = None
        
        elif st.session_state.get("quick_action", "").startswith("count_"):
            col = st.session_state["quick_action"].replace("count_", "")
            with st.spinner(f"Counting {col}..."):
                st.subheader(f"📊 Count of {col}")
                value_counts = active_df[col].value_counts()
                
                c1, c2 = st.columns(2)
                with c1:
                    st.dataframe(value_counts.to_frame(), use_container_width=True)
                with c2:
                    fig = px.bar(
                        x=value_counts.index,
                        y=value_counts.values,
                        title=f"Distribution of {col}",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                st.session_state["quick_action"] = None
        
        # Handle regular question analysis
        if analyze and question:
            with st.spinner("🤖 Running multi-agent analysis..."):
                try:
                    workflow = AnalystWorkflow()
                    workflow.executor.setup_duckdb(active_df, table_name="data")
                    result = workflow.run(
                        question=question,
                        df=active_df,
                        schema=active_profile["schema"],
                        data_profile=active_profile,
                        record_metrics=True,
                    )
                    st.session_state.workflow_result = result
                    st.session_state.question_history.append({"question": question, "result": result})
                    st.session_state["suggested_question"] = None
                    workflow.close()
                    st.success("✅ Analysis complete!")
                except Exception as e:
                    st.error(f"❌ {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # Display Results
        if st.session_state.workflow_result:
            result = st.session_state.workflow_result

            st.markdown("---")
            st.subheader("🔍 Agent Trace")
            tc1, tc2, tc3, tc4 = st.columns(4)
            tc1.metric("Agent", result.get("selected_agent", "N/A"))
            tc2.metric("Confidence", f"{result.get('confidence', 0):.2f}")
            tc3.metric("Validation", "✅" if result.get("valid") else "❌")
            tc4.metric("Latency", f"{result.get('latency_ms', 0):.0f}ms")

            if result.get("code"):
                with st.expander("💻 Generated Code"):
                    st.code(result["code"], language=result.get("code_type", "python"))

            if result.get("result") is not None:
                st.subheader("📊 Results")
                if isinstance(result["result"], pd.DataFrame):
                    st.dataframe(result["result"], use_container_width=True)
                else:
                    st.write(result["result"])

            if result.get("report"):
                st.subheader("📝 Report")
                st.markdown(result["report"])
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "📄 Download Markdown",
                        result["report"],
                        file_name="report.md",
                        mime="text/markdown",
                    )
                with c2:
                    html = f"<html><body>{result['report'].replace(chr(10), '<br>')}</body></html>"
                    st.download_button(
                        "🌐 Download HTML",
                        html,
                        file_name="report.html",
                        mime="text/html",
                    )
        
        # Display History
        if st.session_state.question_history:
            st.markdown("---")
            st.subheader("📜 Question History")
            
            # Search and filter
            search_term = st.text_input("🔍 Search history:", key="history_search")
            
            # Display history with option to rerun
            for idx, item in enumerate(reversed(st.session_state.question_history)):
                with st.expander(f"Q: {item['question'][:50]}...", expanded=False):
                    st.markdown(f"**Question:** {item['question']}")
                    
                    if item.get("result"):
                        res = item["result"]
                        st.markdown(f"**Agent:** {res.get('selected_agent', 'N/A')}")
                        st.markdown(f"**Confidence:** {res.get('confidence', 0):.2f}")
                        
                        if res.get("result") is not None:
                            if isinstance(res["result"], pd.DataFrame):
                                st.dataframe(res["result"].head(), use_container_width=True)
                            else:
                                st.write(res["result"][:500] if isinstance(res["result"], str) else res["result"])
                        
                        if st.button(f"🔄 Rerun Analysis", key=f"rerun_{idx}"):
                            st.session_state["suggested_question"] = item["question"]
                            st.rerun()
                    
                    if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                        del st.session_state.question_history[-(idx + 1)]
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════
#  TAB 3 — Multi-File Join (Phase 7)
# ══════════════════════════════════════════════════════════════════════
with tab_join:
    st.header("🔗 Multi-File Join")
    st.markdown("Upload multiple datasets and join them for cross-dataset analysis.")

    if st.session_state.joiner is None:
        st.session_state.joiner = MultiFileJoiner()

    joiner: MultiFileJoiner = st.session_state.joiner

    # Register current primary dataset automatically
    if st.session_state.df is not None and st.session_state.file_path:
        primary_name = os.path.splitext(os.path.basename(st.session_state.file_path))[0]
        if primary_name not in joiner.list_datasets():
            joiner.register_dataset(primary_name, st.session_state.df)
            st.info(f"Auto-registered primary dataset as **{primary_name}**")

    # Upload additional files
    st.subheader("1. Upload Additional Datasets")
    extra_files = st.file_uploader(
        "Upload additional CSV/Excel files to join",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="join_files",
    )

    for f in (extra_files or []):
        name = os.path.splitext(f.name)[0]
        if name not in joiner.list_datasets():
            try:
                profiler = DataProfiler()
                tmp_path = os.path.join(config.DATA_DIR, f.name)
                with open(tmp_path, "wb") as out:
                    out.write(f.getbuffer())
                df_extra = profiler.load_data(tmp_path)
                joiner.register_dataset(name, df_extra)
                st.success(f"✅ Registered **{name}** ({len(df_extra):,} rows)")
            except Exception as e:
                st.error(f"Error loading {f.name}: {e}")

    # Show registered datasets
    datasets = joiner.list_datasets()
    if datasets:
        st.subheader("2. Registered Datasets")
        reg_rows = []
        for ds in datasets:
            p = joiner.dataset_profiles.get(ds, {})
            reg_rows.append({"Name": ds, "Rows": p.get("row_count", 0), "Columns": p.get("column_count", 0)})
        st.dataframe(pd.DataFrame(reg_rows), use_container_width=True)

        if len(datasets) >= 2:
            st.subheader("3. Configure Join")
            left_ds = st.selectbox("Left dataset", datasets, key="join_left")
            right_ds = st.selectbox("Right dataset", [d for d in datasets if d != left_ds], key="join_right")
            join_type = st.selectbox("Join type", ["INNER", "LEFT", "RIGHT", "FULL"], key="join_type")

            # Auto-detect keys
            if st.button("🔍 Auto-detect Join Keys"):
                candidates = joiner.detect_join_keys(left_ds, right_ds)
                if candidates:
                    st.session_state["join_candidates"] = candidates
                    st.success(f"Found {len(candidates)} candidate key(s)")
                else:
                    st.warning("Could not detect join keys automatically.")

            candidates = st.session_state.get("join_candidates", [])
            if candidates:
                st.write("**Detected Candidates:**")
                cand_df = pd.DataFrame(candidates)
                st.dataframe(cand_df, use_container_width=True)

            # Manual key selection
            left_cols = list(joiner.dataset_profiles.get(left_ds, {}).get("columns", {}).keys())
            right_cols = list(joiner.dataset_profiles.get(right_ds, {}).get("columns", {}).keys())

            default_left = candidates[0]["left_key"] if candidates else (left_cols[0] if left_cols else "")
            default_right = candidates[0]["right_key"] if candidates else (right_cols[0] if right_cols else "")

            col_l, col_r = st.columns(2)
            with col_l:
                left_key = st.selectbox(
                    f"Join key from {left_ds}",
                    left_cols,
                    index=left_cols.index(default_left) if default_left in left_cols else 0,
                    key="join_left_key",
                )
            with col_r:
                right_key = st.selectbox(
                    f"Join key from {right_ds}",
                    right_cols,
                    index=right_cols.index(default_right) if default_right in right_cols else 0,
                    key="join_right_key",
                )

            if st.button("🔗 Execute Join", type="primary"):
                with st.spinner("Joining datasets..."):
                    cfg = JoinConfig(
                        left_table=left_ds,
                        right_table=right_ds,
                        left_key=left_key,
                        right_key=right_key,
                        join_type=join_type,
                    )
                    result = joiner.join_datasets([cfg], result_name="joined_data")

                if result["success"]:
                    joined_df = result["result"]
                    st.session_state.joined_df = joined_df

                    # Build profile for the joined dataset
                    profiler = DataProfiler()
                    st.session_state.joined_profile = profiler.profile_data(joined_df)

                    st.success(
                        f"✅ Join successful: {result['row_count']:,} rows × {result['column_count']} columns"
                    )
                    st.subheader("SQL Used")
                    st.code(result["sql"], language="sql")
                    st.subheader("Result Preview")
                    st.dataframe(joined_df.head(20), use_container_width=True)
                    st.info("The joined dataset is now available in the Ask Questions tab.")
                else:
                    st.error(f"Join failed: {result['error']}")
    else:
        st.info("Upload your primary file in the Data Upload tab, then add more files here.")

# ══════════════════════════════════════════════════════════════════════
#  TAB 4 — Auto EDA (Phase 7)
# ══════════════════════════════════════════════════════════════════════
with tab_eda:
    st.header("🔍 Automatic Exploratory Data Analysis")

    active_df = st.session_state.joined_df if st.session_state.joined_df is not None else st.session_state.df

    if active_df is None:
        st.warning("⚠️ Upload a dataset first.")
    else:
        dataset_label = "joined dataset" if st.session_state.joined_df is not None else "uploaded dataset"
        st.write(f"Running EDA on **{dataset_label}** ({len(active_df):,} rows × {len(active_df.columns)} columns)")

        run_eda = st.button("🚀 Run Auto EDA", type="primary")
        if run_eda:
            with st.spinner("Running exploratory data analysis..."):
                eda_agent = AutoEDAAgent()
                report = eda_agent.run_eda(active_df, dataset_label)
                st.session_state.eda_report = report

        if st.session_state.eda_report:
            r = st.session_state.eda_report
            ov = r["overview"]

            # Metrics row
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows", f"{ov['rows']:,}")
            c2.metric("Columns", ov["columns"])
            c3.metric("Memory", f"{ov['memory_mb']} MB")
            c4.metric("Missing %", f"{r['missing_values']['total_missing_pct']:.1f}%")

            # Insights
            st.subheader("💡 Key Insights")
            for insight in r["insights"]:
                st.markdown(f"- {insight}")

            st.subheader("✅ Recommendations")
            for rec in r["recommendations"]:
                st.markdown(f"- {rec}")

            # Numeric stats table
            if r["numeric_analysis"]:
                st.subheader("📊 Numeric Columns")
                num_df = pd.DataFrame(r["numeric_analysis"])
                display_cols = [c for c in ["column", "mean", "std", "min", "max", "outlier_pct", "skewness"] if c in num_df.columns]
                st.dataframe(num_df[display_cols].round(3), use_container_width=True)

                # Outlier chart
                if "outlier_pct" in num_df.columns:
                    fig = px.bar(
                        num_df.sort_values("outlier_pct", ascending=False).head(10),
                        x="column", y="outlier_pct",
                        title="Outlier % by Column (IQR method)",
                        labels={"outlier_pct": "Outlier %", "column": "Column"},
                        color="outlier_pct", color_continuous_scale="Reds",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # Categorical stats
            if r["categorical_analysis"]:
                st.subheader("🏷️ Categorical Columns")
                cat_df = pd.DataFrame(r["categorical_analysis"])
                display_cols = [c for c in ["column", "unique_count", "unique_pct", "most_frequent", "most_frequent_pct", "entropy"] if c in cat_df.columns]
                st.dataframe(cat_df[display_cols].round(3), use_container_width=True)

            # Correlation heatmap
            corr = r["correlation_analysis"]
            if corr.get("available") and corr.get("matrix"):
                st.subheader("🔥 Correlation Heatmap")
                matrix_data = corr["matrix"]
                corr_df = pd.DataFrame(matrix_data)
                fig = px.imshow(
                    corr_df,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    title="Correlation Matrix",
                    aspect="auto",
                )
                st.plotly_chart(fig, use_container_width=True)

                if corr["high_correlation_pairs"]:
                    st.subheader("High Correlation Pairs")
                    st.dataframe(pd.DataFrame(corr["high_correlation_pairs"]), use_container_width=True)

            # Missing values
            mv = r["missing_values"]
            if mv["columns_with_missing"]:
                st.subheader("⚠️ Missing Values")
                mv_df = pd.DataFrame(mv["columns_with_missing"])
                fig = px.bar(
                    mv_df, x="column", y="missing_pct",
                    title="Missing % by Column",
                    labels={"missing_pct": "Missing %", "column": "Column"},
                    color="missing_pct", color_continuous_scale="Oranges",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Export EDA report
            eda_agent_for_export = AutoEDAAgent()
            eda_agent_for_export.results = r
            md_report = eda_agent_for_export.to_markdown()
            st.download_button(
                "📥 Download EDA Report (Markdown)",
                md_report,
                file_name="eda_report.md",
                mime="text/markdown",
            )

# ══════════════════════════════════════════════════════════════════════
#  TAB 5 — Dataset Versioning (Phase 7)
# ══════════════════════════════════════════════════════════════════════
with tab_versions:
    st.header("🗂️ Dataset Versioning")
    st.markdown("Track, compare, and restore dataset versions.")

    vm: DatasetVersionManager = st.session_state.version_manager
    all_datasets = vm.list_all_datasets()

    if not all_datasets:
        st.info("No dataset versions saved yet. Upload a dataset to begin tracking.")
    else:
        selected_dataset = st.selectbox("Select dataset", all_datasets)
        versions = vm.list_versions(selected_dataset)

        if versions:
            st.subheader(f"Version History: {selected_dataset}")
            version_df = vm.to_dataframe(selected_dataset)
            if not version_df.empty:
                st.dataframe(version_df, use_container_width=True)

            # Version comparison
            if len(versions) >= 2:
                st.subheader("🔄 Compare Two Versions")
                v_ids = [v.version_id for v in versions]
                col_a, col_b = st.columns(2)
                with col_a:
                    ver_a = st.selectbox("Version A", v_ids, index=0, key="ver_a")
                with col_b:
                    ver_b = st.selectbox("Version B", v_ids, index=len(v_ids) - 1, key="ver_b")

                if st.button("Compare Versions") and ver_a != ver_b:
                    diff = vm.compare_versions(selected_dataset, ver_a, ver_b)
                    if "error" not in diff:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Row Change", f"{diff['row_count_change']:+,}")
                        c2.metric("Schema Changed", "Yes" if diff["schema_changed"] else "No")
                        c3.metric("Identical", "Yes" if diff["identical_checksums"] else "No")

                        if diff["added_columns"]:
                            st.success(f"Added columns: {', '.join(diff['added_columns'])}")
                        if diff["removed_columns"]:
                            st.error(f"Removed columns: {', '.join(diff['removed_columns'])}")

                        if diff["numeric_drift"]:
                            st.subheader("Numeric Column Drift")
                            drift_df = pd.DataFrame(diff["numeric_drift"])
                            st.dataframe(drift_df.round(4), use_container_width=True)
                    else:
                        st.error(diff["error"])

            # Restore a version
            st.subheader("🔁 Restore a Version")
            restore_ver = st.selectbox("Choose version to restore", [v.version_id for v in versions], key="restore_ver")
            if st.button("Restore Version"):
                restored_df = vm.load_version(selected_dataset, restore_ver)
                if restored_df is not None:
                    st.session_state.df = restored_df
                    profiler = DataProfiler()
                    st.session_state.profile = profiler.profile_data(restored_df)
                    st.success(f"✅ Restored {selected_dataset} {restore_ver} — {len(restored_df):,} rows")
                else:
                    st.error("Could not restore version.")

            # Manual version save
            st.subheader("💾 Save Current Dataset as New Version")
            if st.session_state.df is not None:
                description = st.text_input("Version description (optional)", key="version_desc")
                if st.button("Save Version"):
                    new_ver = vm.save_version(
                        selected_dataset,
                        st.session_state.df,
                        source_file=st.session_state.file_path or "",
                        description=description,
                    )
                    st.success(f"Saved as **{new_ver.version_id}**")
                    st.rerun()
        else:
            st.info("No versions for this dataset yet.")

# ══════════════════════════════════════════════════════════════════════
#  TAB 6 — Jev vs LLM Benchmark (Phase 7)
# ══════════════════════════════════════════════════════════════════════
with tab_benchmark:
    st.header("⚡ Jev vs LLM Benchmark")
    st.markdown(
        "Compare routing decision accuracy and latency between "
        "the **Jev rule-based engine** and the **local LLM**."
    )

    benchmark = JevVsLLMBenchmark()

    # Jev decider function
    def _jev_decider(question: str, schema: str) -> dict:
        from agents.jev_planner import JevPlanner
        planner = JevPlanner()
        plan = planner.plan_analysis(
            question=question,
            schema=schema,
            data_profile={"row_count": 1000, "column_count": 9, "data_types": {}, "missing_values": {}},
        )
        return {
            "method": plan.get("method", "SQL"),
            "visualization": plan.get("visualization", ""),
            "confidence": plan.get("confidence", 0.5),
            "reasoning": plan.get("reasoning", ""),
        }

    col1, col2 = st.columns([1, 1])
    with col1:
        run_jev_only = st.button("▶️ Run Jev-only Benchmark", type="primary", use_container_width=True)
    with col2:
        run_desc = st.text_input("Run description", "Phase 7 Jev benchmark", key="bench_desc")

    if run_jev_only:
        with st.spinner("Running benchmark..."):
            cases = benchmark.default_test_suite()
            run = benchmark.run(
                cases=cases,
                jev_decider=_jev_decider,
                description=run_desc,
            )
            benchmark.save_run(run)
            comparison = benchmark.compare_engines(run)
            st.session_state["bench_comparison"] = comparison
            st.session_state["bench_run"] = run
            st.success(f"✅ Benchmark complete — {len(cases)} cases")

    if "bench_comparison" in st.session_state:
        comp = st.session_state["bench_comparison"]
        run_obj = st.session_state["bench_run"]

        for engine, metrics in comp.get("engines", {}).items():
            st.subheader(f"{engine.upper()} Results")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Accuracy", f"{metrics['accuracy_pct']:.1f}%")
            mc2.metric("Correct", f"{metrics['correct']}/{metrics['total_cases']}")
            mc3.metric("Mean Latency", f"{metrics['mean_latency_ms']:.1f}ms")
            mc4.metric("Mean Confidence", f"{metrics['mean_confidence']:.3f}")

        # Detailed results table
        st.subheader("Detailed Results")
        results_df = pd.DataFrame([r.to_dict() for r in run_obj.results])
        if not results_df.empty:
            display_cols = [c for c in ["case_id", "engine", "decision", "correct", "confidence", "latency_ms", "error"] if c in results_df.columns]
            st.dataframe(results_df[display_cols], use_container_width=True)

            # Accuracy chart by case
            if "correct" in results_df.columns:
                fig = px.bar(
                    results_df,
                    x="case_id", y="latency_ms",
                    color="correct",
                    color_discrete_map={True: "green", False: "red"},
                    title="Latency per Case (green=correct, red=incorrect)",
                    labels={"latency_ms": "Latency (ms)", "case_id": "Case ID"},
                )
                st.plotly_chart(fig, use_container_width=True)

    # Historical benchmark runs
    st.subheader("Previous Runs")
    saved_runs = benchmark.list_runs()
    if saved_runs:
        st.dataframe(pd.DataFrame(saved_runs), use_container_width=True)
    else:
        st.info("No previous benchmark runs saved.")

# ══════════════════════════════════════════════════════════════════════
#  TAB 7 — Performance Dashboard (Phase 7)
# ══════════════════════════════════════════════════════════════════════
with tab_perf:
    st.header("📈 Model Performance Dashboard")
    st.markdown("Live metrics from all analysis runs recorded in this session and previously.")

    dashboard: ModelPerformanceDashboard = st.session_state.perf_dashboard

    col1, col2 = st.columns([1, 1])
    with col1:
        refresh = st.button("🔄 Refresh", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear Metrics", use_container_width=True):
            dashboard.clear()
            st.rerun()

    stats = dashboard.summary_stats()

    if stats.get("total_runs", 0) == 0:
        st.info("No performance data yet. Run some analyses in the Ask Questions tab.")
    else:
        # Top metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Runs", stats["total_runs"])
        c2.metric("Success Rate", f"{stats['success_rate_pct']:.1f}%")
        c3.metric("Mean Latency", f"{stats['mean_latency_ms']:.0f}ms")
        c4.metric("Mean Retries", f"{stats['mean_retries']:.2f}")
        c5.metric("Mean Quality", f"{stats['mean_quality_score']:.3f}")

        # Recent trend
        trends = dashboard.recent_trends(20)
        if trends:
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("Recent Success Rate (last 20)", f"{trends['success_rate_recent']*100:.1f}%")
            tc2.metric("Recent Mean Latency", f"{trends['mean_latency_recent']:.0f}ms")
            tc3.metric("Recent Mean Quality", f"{trends['mean_quality_recent']:.3f}")

        # Agent comparison
        agent_comp = dashboard.agent_comparison()
        if agent_comp:
            st.subheader("Agent Comparison")
            st.dataframe(pd.DataFrame(agent_comp), use_container_width=True)

            fig = px.bar(
                pd.DataFrame(agent_comp),
                x="agent", y="success_rate_pct",
                title="Success Rate by Agent",
                color="success_rate_pct",
                color_continuous_scale="Greens",
                labels={"success_rate_pct": "Success %", "agent": "Agent"},
            )
            st.plotly_chart(fig, use_container_width=True)

        # Latency distribution
        buckets = dashboard.latency_buckets()
        if buckets:
            st.subheader("Latency Distribution")
            lat_df = pd.DataFrame(
                [{"Bucket": k, "Count": v} for k, v in buckets.items()]
            )
            fig = px.bar(
                lat_df, x="Bucket", y="Count",
                title="Latency Buckets",
                color="Count", color_continuous_scale="Blues",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Retry distribution
        retry_dist = dashboard.retry_distribution()
        if retry_dist:
            st.subheader("Retry Distribution")
            ret_df = pd.DataFrame(
                [{"Retries": k, "Count": v} for k, v in retry_dist.items()]
            )
            fig = px.bar(
                ret_df, x="Retries", y="Count",
                title="Retry Count Distribution",
                color="Count", color_continuous_scale="Reds",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Error breakdown
        errors = dashboard.error_breakdown()
        if errors:
            st.subheader("Error Breakdown")
            st.dataframe(pd.DataFrame(errors), use_container_width=True)

        # Raw metrics table
        with st.expander("Raw Metrics Data"):
            all_metrics_df = dashboard.export_to_dataframe()
            if not all_metrics_df.empty:
                st.dataframe(all_metrics_df, use_container_width=True)
                st.download_button(
                    "📥 Download as CSV",
                    all_metrics_df.to_csv(index=False),
                    file_name="performance_metrics.csv",
                    mime="text/csv",
                )

# ══════════════════════════════════════════════════════════════════════
#  TAB 8 — Analysis History
# ══════════════════════════════════════════════════════════════════════
with tab_history:
    st.header("📊 Analysis History")

    if not st.session_state.question_history:
        st.info("No history yet. Ask questions in the Ask Questions tab.")
    else:
        for i, item in enumerate(reversed(st.session_state.question_history), 1):
            with st.expander(f"Q{i}: {item['question']}", expanded=False):
                r = item["result"]
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Agent:** {r.get('selected_agent', 'N/A')}")
                c2.write(f"**Status:** {'✅' if not r.get('error') else '❌'}")
                c3.write(f"**Latency:** {r.get('latency_ms', 0):.0f}ms")

                if r.get("result") is not None:
                    if isinstance(r["result"], pd.DataFrame):
                        st.dataframe(r["result"])
                    else:
                        st.write(r["result"])
                if r.get("report"):
                    st.markdown(r["report"])

# ──────────────────────────────────────────────────────────────────────
#  Footer
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "**Multi-Agent Data Analyst** | Phase 7: Multi-file joins · Auto EDA · "
    "Dataset versioning · Jev vs LLM benchmarking · Performance dashboard  \n"
    "Built with Jev · Ollama · LangGraph · DuckDB · Pandas · Streamlit"
)

