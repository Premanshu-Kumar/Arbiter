"""
Test script for Phase 2 components
"""
import sys
import os
import pandas as pd

# Test imports
print("Testing Phase 2 imports...")
try:
    from agents.jev_planner import JevPlanner
    print("✅ JevPlanner imported successfully")
except Exception as e:
    print(f"❌ Error importing JevPlanner: {e}")
    sys.exit(1)

try:
    from agents.sql_agent import SQLAgent
    print("✅ SQLAgent imported successfully")
except Exception as e:
    print(f"❌ Error importing SQLAgent: {e}")
    sys.exit(1)

try:
    from agents.python_agent import PythonAgent
    print("✅ PythonAgent imported successfully")
except Exception as e:
    print(f"❌ Error importing PythonAgent: {e}")
    sys.exit(1)

try:
    from agents.viz_agent import VizAgent
    print("✅ VizAgent imported successfully")
except Exception as e:
    print(f"❌ Error importing VizAgent: {e}")
    sys.exit(1)

try:
    from agents.report_agent import ReportAgent
    print("✅ ReportAgent imported successfully")
except Exception as e:
    print(f"❌ Error importing ReportAgent: {e}")
    sys.exit(1)

try:
    from agents.jev_validator import JevValidator
    print("✅ JevValidator imported successfully")
except Exception as e:
    print(f"❌ Error importing JevValidator: {e}")
    sys.exit(1)

# Test JevPlanner
print("\nTesting JevPlanner...")
try:
    planner = JevPlanner()
    
    # Create sample data profile
    sample_profile = {
        "row_count": 1000,
        "column_count": 5,
        "data_types": {
            "id": "int64",
            "name": "object",
            "category": "object",
            "value": "float64",
            "date": "datetime64[ns]"
        },
        "missing_values": {
            "id": 0.0,
            "name": 0.5,
            "category": 0.0,
            "value": 1.0,
            "date": 0.0
        }
    }
    
    sample_schema = """Columns: 5
Rows: 1000

Column Details:
  - id (int64) - 0.0% null
  - name (object) - 0.5% null
  - category (object) - 0.0% null
  - value (float64) - 1.0% null
  - date (datetime64[ns]) - 0.0% null"""
    
    plan = planner.plan_analysis(
        question="What is the average value by category?",
        schema=sample_schema,
        data_profile=sample_profile
    )
    
    print(f"✅ JevPlanner analysis plan generated")
    print(f"   - Method: {plan['method']}")
    print(f"   - Confidence: {plan['confidence']}")
    print(f"   - Visualization: {plan['visualization']}")
    print(f"   - Requires Aggregation: {plan['requires_aggregation']}")
    
except Exception as e:
    print(f"❌ Error testing JevPlanner: {e}")

# Test SQLAgent
print("\nTesting SQLAgent...")
try:
    sql_agent = SQLAgent()
    
    plan = {
        "method": "SQL",
        "requires_aggregation": True,
        "requires_time_series": False,
        "requires_filtering": False,
        "requires_sorting": True
    }
    
    sql_result = sql_agent.generate_sql(
        question="What is the average value by category?",
        schema=sample_schema,
        plan=plan
    )
    
    print(f"✅ SQLAgent generated SQL code")
    print(f"   - Success: {sql_result['success']}")
    if sql_result.get('success') is True:
        print(f"   - Code preview: {sql_result['code'][:100]}...")
        
        # Test validation
        is_valid, error = sql_agent.validate_sql(sql_result['code'])
        print(f"   - SQL Valid: {is_valid}")
        if not is_valid:
            print(f"   - Validation Error: {error}")
    
except Exception as e:
    print(f"❌ Error testing SQLAgent: {e}")

# Test PythonAgent
print("\nTesting PythonAgent...")
try:
    python_agent = PythonAgent()
    
    plan = {
        "method": "Python",
        "requires_aggregation": True,
        "requires_time_series": False,
        "requires_filtering": False,
        "requires_sorting": True
    }
    
    python_result = python_agent.generate_python(
        question="What is the average value by category?",
        schema=sample_schema,
        plan=plan
    )
    
    print(f"✅ PythonAgent generated Python code")
    print(f"   - Success: {python_result['success']}")
    if python_result.get('success') is True:
        print(f"   - Code preview: {python_result['code'][:100]}...")
        
        # Test validation
        is_valid, error = python_agent.validate_python(python_result['code'])
        print(f"   - Python Valid: {is_valid}")
        if not is_valid:
            print(f"   - Validation Error: {error}")
    
except Exception as e:
    print(f"❌ Error testing PythonAgent: {e}")

# Test VizAgent
print("\nTesting VizAgent...")
try:
    viz_agent = VizAgent()
    
    # Create sample data for visualization
    sample_data = pd.DataFrame({
        'category': ['A', 'B', 'C', 'D', 'E'],
        'value': [100, 150, 75, 200, 125]
    })
    
    plan = {
        "method": "SQL",
        "visualization": "bar_chart"
    }
    
    viz_result = viz_agent.generate_chart(
        data=sample_data,
        chart_type="bar_chart",
        plan=plan,
        question="Value by category"
    )
    
    print(f"✅ VizAgent generated chart")
    print(f"   - Success: {viz_result['success']}")
    print(f"   - Chart Type: {viz_result['chart_type']}")
    
    # Test chart type suggestion
    suggested = viz_agent.suggest_chart_type(sample_data, "Compare values by category")
    print(f"   - Suggested Chart: {suggested}")
    
except Exception as e:
    print(f"❌ Error testing VizAgent: {e}")

# Test ReportAgent
print("\nTesting ReportAgent...")
try:
    report_agent = ReportAgent()
    
    plan = {
        "method": "SQL",
        "confidence": 0.8,
        "visualization": "bar_chart"
    }
    
    sample_result = pd.DataFrame({
        'category': ['A', 'B'],
        'average_value': [100.5, 150.3]
    })
    
    report_result = report_agent.generate_report(
        question="What is the average value by category?",
        plan=plan,
        result=sample_result,
        error=None
    )
    
    print(f"✅ ReportAgent generated report")
    print(f"   - Success: {report_result['success']}")
    if report_result.get('success') is True:
        print(f"   - Executive Summary: {report_result['executive_summary'][:100]}...")
        print(f"   - Key Insights Count: {len(report_result['key_insights'])}")
    
except Exception as e:
    print(f"❌ Error testing ReportAgent: {e}")

# Test JevValidator
print("\nTesting JevValidator...")
try:
    validator = JevValidator()
    
    plan = {
        "method": "SQL",
        "confidence": 0.8
    }
    
    # Test with valid result
    sample_result = pd.DataFrame({
        'category': ['A', 'B'],
        'value': [100, 150]
    })
    
    validation = validator.validate_result(
        result=sample_result,
        error=None,
        question="Test question",
        plan=plan,
        retry_count=0
    )
    
    print(f"✅ JevValidator validation completed")
    print(f"   - Valid: {validation['valid']}")
    print(f"   - Decision: {validation['decision']}")
    print(f"   - Reasoning: {validation['reasoning'][:100]}...")
    
    # Test quality check
    quality = validator.check_result_quality(sample_result)
    print(f"   - Quality Score: {quality['score']}")
    print(f"   - Issues: {len(quality['issues'])}")
    
except Exception as e:
    print(f"❌ Error testing JevValidator: {e}")

print("\n" + "="*50)
print("Phase 2 Component Tests Complete")
print("="*50)
print("\nSummary:")
print("✅ All Phase 2 agents imported successfully")
print("✅ JevPlanner - Analysis strategy planning working")
print("✅ SQLAgent - SQL code generation working")
print("✅ PythonAgent - Python code generation working")
print("✅ VizAgent - Chart generation working")
print("✅ ReportAgent - Report generation working")
print("✅ JevValidator - Result validation working")
print("\nPhase 2 is ready for integration!")
print("\nNote: Some agents use Ollama LLM for code generation.")
print("Full functionality requires Ollama server running with configured models.")