"""
Streamlit UI for Multi-Agent Data Analyst
Phase 6: Enhanced UI with full workflow integration
"""
import streamlit as st
import pandas as pd
import os
from agents.profiler import DataProfiler
from agents.ollama_client import OllamaClient
from decision.jev_client import JevClient
from graph import AnalystWorkflow
import config
import plotly.graph_objects as go
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Data Analyst",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'profile' not in st.session_state:
    st.session_state.profile = None
if 'file_path' not in st.session_state:
    st.session_state.file_path = None
if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None
if 'question_history' not in st.session_state:
    st.session_state.question_history = []

# Title and description
st.title("🤖 Multi-Agent Data Analyst")
st.markdown("""
A Jev-powered, local-first AI data analyst that combines fast decision-making with local LLMs to analyze CSV and Excel files.
""")

# Sidebar
st.sidebar.header("Configuration")

# Ollama connection check
st.sidebar.subheader("Ollama Status")
ollama_client = OllamaClient()
if ollama_client.check_connection():
    st.sidebar.success("✅ Ollama Connected")
    models = ollama_client.list_models()
    if models:
        st.sidebar.write(f"Available models: {', '.join(models[:5])}")
        if len(models) > 5:
            st.sidebar.write(f"... and {len(models) - 5} more")
else:
    st.sidebar.error("❌ Ollama Not Connected")
    st.sidebar.info("Make sure Ollama is running: `ollama serve`")

# Jev connection check
st.sidebar.subheader("Jev Status")
jev_client = JevClient()
if jev_client.check_connection():
    st.sidebar.success("✅ Jev Connected")
else:
    st.sidebar.warning("⚠️ Jev Not Configured (using fallback logic)")

# Main content - Tabs
tab1, tab2, tab3 = st.tabs(["📁 Data Upload", "❓ Ask Questions", "📊 Analysis History"])

# Tab 1: Data Upload
with tab1:
    st.header("📁 Upload Your Data")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Supported formats: CSV, Excel (.xlsx, .xls)"
    )
    
    if uploaded_file:
        # Save uploaded file
        file_path = os.path.join(config.DATA_DIR, uploaded_file.name)
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.file_path = file_path
        
        # Load and profile data
        try:
            profiler = DataProfiler()
            df = profiler.load_data(file_path)
            st.session_state.df = df
            
            profile = profiler.profile_data(df)
            st.session_state.profile = profile
            
            # Display success message
            st.success(f"✅ Successfully loaded: {uploaded_file.name}")
            
            # Display data overview
            col1, col2, col3 = st.columns(3)
            col1.metric("Rows", f"{profile['row_count']:,}")
            col2.metric("Columns", profile['column_count'])
            col3.metric("Missing Values", f"{sum(1 for v in profile['missing_values'].values() if v > 0)}")
            
            # Display schema
            st.subheader("📊 Data Schema")
            st.text(profile['schema'])
            
            # Display data preview
            st.subheader("👁️ Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Display column details
            st.subheader("📋 Column Details")
            
            columns_df = pd.DataFrame(profile['columns'])
            columns_df = columns_df[['name', 'dtype', 'null_count', 'null_percentage', 'unique_count']]
            columns_df.columns = ['Column', 'Data Type', 'Null Count', 'Null %', 'Unique Values']
            st.dataframe(columns_df, use_container_width=True)
            
            # Missing values visualization
            if any(v > 0 for v in profile['missing_values'].values()):
                st.subheader("⚠️ Missing Values")
                missing_df = pd.DataFrame([
                    {'Column': col, 'Missing %': pct}
                    for col, pct in profile['missing_values'].items()
                    if pct > 0
                ])
                st.bar_chart(missing_df.set_index('Column'))
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.session_state.df = None
            st.session_state.profile = None
    
    else:
        # Show instructions when no file is uploaded
        st.info("""
        👆 Upload a CSV or Excel file to get started.
        
        The system will automatically:
        - Profile your data
        - Extract schema information
        - Identify missing values
        - Display statistics and previews
        """)

# Tab 2: Ask Questions
with tab2:
    st.header("❓ Ask Questions About Your Data")
    
    if st.session_state.df is None:
        st.warning("⚠️ Please upload a file first in the Data Upload tab")
    else:
        # Question input
        question = st.text_input(
            "Enter your question about the data:",
            placeholder="e.g., What is the average value by category?",
            key="question_input"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            analyze_button = st.button("🚀 Analyze", type="primary", use_container_width=True)
        with col2:
            clear_button = st.button("🗑️ Clear History", use_container_width=True)
        
        if clear_button:
            st.session_state.question_history = []
            st.session_state.workflow_result = None
            st.rerun()
        
        if analyze_button and question:
            with st.spinner("🤖 Running multi-agent analysis..."):
                try:
                    # Initialize workflow
                    workflow = AnalystWorkflow()
                    workflow.executor.setup_duckdb(st.session_state.df, table_name="data")
                    
                    # Run analysis
                    result = workflow.run(
                        question=question,
                        df=st.session_state.df,
                        schema=st.session_state.profile['schema'],
                        data_profile=st.session_state.profile
                    )
                    
                    # Store result
                    st.session_state.workflow_result = result
                    st.session_state.question_history.append({
                        'question': question,
                        'result': result
                    })
                    
                    workflow.close()
                    
                    st.success("✅ Analysis complete!")
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        
        # Display latest result
        if st.session_state.workflow_result:
            result = st.session_state.workflow_result
            
            # Agent Trace
            st.subheader("🔍 Agent Trace")
            trace_col1, trace_col2, trace_col3 = st.columns(3)
            trace_col1.metric("Selected Agent", result.get('selected_agent', 'N/A'))
            trace_col2.metric("Confidence", f"{result.get('confidence', 0):.2f}")
            trace_col3.metric("Validation", "✅ Passed" if result.get('valid') else "❌ Failed")
            
            # Execution details
            st.subheader("⚙️ Execution Details")
            if result.get('error'):
                st.error(f"Error: {result['error']}")
            else:
                st.success("✅ Execution successful")
            
            # Code Viewer
            if result.get('code'):
                st.subheader("💻 Generated Code")
                code_type = result.get('code_type', 'unknown')
                st.code(result['code'], language=code_type)
            
            # Results
            if result.get('result') is not None:
                st.subheader("📊 Analysis Results")
                if isinstance(result['result'], pd.DataFrame):
                    st.dataframe(result['result'], use_container_width=True)
                else:
                    st.write(result['result'])
            
            # Visualization
            if result.get('charts'):
                st.subheader("📈 Visualization")
                # Note: Charts are stored as JSON, would need to render them
                st.info(f"Generated {len(result['charts'])} chart(s)")
            
            # Report
            if result.get('report'):
                st.subheader("📝 Report")
                st.markdown(result['report'])
                
                # Export buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📄 Export as Markdown"):
                        st.download_button(
                            "Download Report",
                            result['report'],
                            file_name="report.md",
                            mime="text/markdown"
                        )
                with col2:
                    if st.button("🌐 Export as HTML"):
                        html_report = f"""<html><body>{result['report'].replace('\n', '<br>')}</body></html>"""
                        st.download_button(
                            "Download HTML Report",
                            html_report,
                            file_name="report.html",
                            mime="text/html"
                        )

# Tab 3: Analysis History
with tab3:
    st.header("📊 Analysis History")
    
    if not st.session_state.question_history:
        st.info("No analysis history yet. Ask some questions in the Ask Questions tab!")
    else:
        for i, item in enumerate(reversed(st.session_state.question_history), 1):
            with st.expander(f"Q{i}: {item['question']}", expanded=False):
                result = item['result']
                st.write(f"**Agent:** {result.get('selected_agent', 'N/A')}")
                st.write(f"**Status:** {'✅ Success' if not result.get('error') else '❌ Failed'}")
                
                if result.get('result') is not None:
                    if isinstance(result['result'], pd.DataFrame):
                        st.dataframe(result['result'])
                    else:
                        st.write(result['result'])

# Footer
st.markdown("---")
st.markdown("""
**Multi-Agent Data Analyst** | Phase 6: Enhanced UI Complete  
Built with Jev, Ollama, LangGraph, DuckDB, Pandas, and Streamlit
""")
