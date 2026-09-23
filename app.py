"""
Streamlit UI for Multi-Agent Data Analyst
Phase 1: File upload and data profiling
"""
import streamlit as st
import pandas as pd
import os
from agents.profiler import DataProfiler
from agents.ollama_client import OllamaClient
from decision.jev_client import JevClient
import config

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

# Main content
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
        
        # Phase 1 completion notice
        st.info("""
        **Phase 1 Features Implemented:**
        ✅ CSV/Excel file upload
        ✅ Data profiling with statistics
        ✅ Schema extraction
        ✅ Missing value analysis
        ✅ Ollama integration (for future phases)
        ✅ Jev integration (with fallback logic)
        
        **Coming in Phase 2:** AI-powered question answering and analysis
        """)
        
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
    
    **Phase 1 Status:** File upload and data profiling ready
    """)

# Footer
st.markdown("---")
st.markdown("""
**Multi-Agent Data Analyst** | Phase 1: Foundation Complete  
Built with Jev, Ollama, LangGraph, DuckDB, Pandas, and Streamlit
""")
