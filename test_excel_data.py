"""
Test Phase 4 with real Excel file
"""
import pandas as pd
from graph import AnalystWorkflow
from agents.profiler import DataProfiler

def test_with_real_excel():
    """Test workflow with real Excel file"""
    print("=" * 50)
    print("Testing Phase 4 with Real Excel Data")
    print("=" * 50)
    
    # Load and profile the data
    excel_path = "data/sample_data.xlsx"
    profiler = DataProfiler()
    
    print(f"\n📂 Loading data from: {excel_path}")
    df = profiler.load_data(excel_path)
    
    # Profile the data
    profile = profiler.profile_data(df)
    schema = profile['schema']
    row_count = profile['row_count']
    column_count = profile['column_count']
    missing_values = profile['missing_values']
    
    # Register with DuckDB for SQL execution
    import duckdb
    conn = duckdb.connect()
    conn.register('data', df)
    conn.close()
    
    print(f"✅ Data loaded successfully")
    print(f"   - Rows: {row_count}")
    print(f"   - Columns: {column_count}")
    print(f"   - Missing values: {missing_values}")
    print(f"\n📊 Schema:\n{schema}")
    print(f"\n📋 Data preview:\n{df.head()}")
    
    # Create workflow
    print("\n🔧 Creating LangGraph workflow...")
    workflow_instance = AnalystWorkflow()
    workflow_instance.executor.setup_duckdb(df, table_name="data")
    print("✅ Workflow created successfully")
    
    # Test different questions
    questions = [
        "What is the average value by category?",
        "Show me the total value for each category"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'=' * 50}")
        print(f"Test {i}: {question}")
        print('=' * 50)
        
        # Execute workflow using the run method
        try:
            final_state = workflow_instance.run(
                question=question,
                df=df,
                schema=schema,
                data_profile=profile
            )
            
            print(f"\n✅ Workflow execution completed")
            print(f"   - Selected agent: {final_state.get('selected_agent')}")
            print(f"   - Execution success: {final_state.get('error') is None}")
            print(f"   - Validation passed: {final_state.get('valid')}")
            print(f"   - Charts generated: {len(final_state.get('charts', []))}")
            print(f"   - Insights generated: {len(final_state.get('insights', []))}")
            print(f"   - Report generated: {final_state.get('report') is not None}")
            
            if final_state.get('result') is not None:
                print(f"\n📊 Result:")
                if isinstance(final_state['result'], pd.DataFrame):
                    print(final_state['result'])
                else:
                    print(final_state['result'])
            
            if final_state.get('error'):
                print(f"\n❌ Error: {final_state['error']}")
                
        except Exception as e:
            print(f"\n❌ Workflow execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ Excel Data Testing Complete")
    print("=" * 50)
    
    # Clean up
    workflow_instance.close()

if __name__ == "__main__":
    test_with_real_excel()
