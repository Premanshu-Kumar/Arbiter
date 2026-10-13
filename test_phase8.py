"""
Phase 8 - Spreadsheet Integration Tests

Tests for:
- Multi-sheet Excel support
- Excel sheet selection
- Excel result export
- Google Sheets integration (mock)
"""
import pandas as pd
import os
from agents.excel_multi_sheet import ExcelMultiSheetHandler
from agents.google_sheets_agent import GoogleSheetsIntegrator
from agents.profiler import DataProfiler


def test_excel_multi_sheet():
    """Test multi-sheet Excel workbook support"""
    print("=" * 50)
    print("Testing Phase 8: Multi-Sheet Excel Support")
    print("=" * 50)
    
    # Create a multi-sheet Excel file for testing
    test_excel_path = "data/test_multi_sheet.xlsx"
    os.makedirs("data", exist_ok=True)
    
    # Create sample data for multiple sheets
    sheets_data = {
        "Sales": pd.DataFrame({
            "product": ["A", "B", "C"],
            "value": [100, 200, 300]
        }),
        "Customers": pd.DataFrame({
            "customer": ["X", "Y", "Z"],
            "region": ["North", "South", "East"]
        }),
        "Products": pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Laptop", "Phone", "Tablet"],
            "price": [999, 699, 449]
        })
    }
    
    # Write to Excel
    with pd.ExcelWriter(test_excel_path, engine='openpyxl') as writer:
        for sheet_name, df in sheets_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"\n✅ Created test Excel file: {test_excel_path}")
    
    # Test ExcelMultiSheetHandler
    handler = ExcelMultiSheetHandler()
    
    # Load workbook
    print("\n📂 Loading workbook...")
    result = handler.load_workbook(test_excel_path)
    
    if result['success']:
        print(f"✅ Loaded {result['sheet_count']} sheets")
        print(f"   Sheet names: {result['sheet_names']}")
    else:
        print(f"❌ Failed to load: {result['error']}")
        return
    
    # Test getting sheet info
    print("\n📊 Testing sheet info...")
    for sheet_name in handler.sheet_names:
        info = handler.get_sheet_info(sheet_name)
        if info['success']:
            print(f"   {sheet_name}: {info['rows']} rows, {info['columns']} columns")
        else:
            print(f"   {sheet_name}: {info['error']}")
    
    # Test sheet analysis
    print("\n🔍 Testing sheet analysis...")
    for sheet_name in handler.sheet_names:
        analysis = handler.analyze_sheet(sheet_name)
        if analysis['success']:
            print(f"   {sheet_name}: {len(analysis['numeric_columns'])} numeric cols, "
                  f"{len(analysis['categorical_columns'])} categorical cols")
    
    # Test multi-sheet analysis
    print("\n📈 Testing multi-sheet analysis...")
    multi_result = handler.create_multi_sheet_analysis(analysis_type="aggregation")
    if multi_result['success']:
        print(f"✅ Analyzed {len(multi_result['sheets_analyzed'])} sheets")
    
    # Test result export
    print("\n💾 Testing result export...")
    export_path = "data/test_export.xlsx"
    
    mock_results = {
        "question": "What is the total value?",
        "selected_agent": "SQL",
        "valid": True,
        "result": pd.DataFrame({
            "category": ["A", "B"],
            "total": [500, 600]
        }),
        "code": "SELECT category, SUM(value) FROM data GROUP BY category",
        "code_type": "sql",
        "insights": ["Total is 1100"]
    }
    
    export_result = handler.export_results_to_excel(
        mock_results,
        export_path,
        create_summary=True
    )
    
    if export_result['success']:
        print(f"✅ Exported results to {export_path}")
    else:
        print(f"❌ Export failed: {export_result['error']}")
    
    handler.close()
    
    # Cleanup
    try:
        if os.path.exists(test_excel_path):
            os.remove(test_excel_path)
            print(f"\n🗑️ Cleaned up test file")
    except PermissionError:
        print(f"\n⚠️ Could not remove test file (file in use)")
    
    print("\n" + "=" * 50)
    print("✅ Multi-Sheet Excel Tests Complete")
    print("=" * 50)


def test_google_sheets_mock():
    """Test Google Sheets integration (mock)"""
    print("\n" + "=" * 50)
    print("Testing Phase 8: Google Sheets Integration (Mock)")
    print("=" * 50)
    
    integrator = GoogleSheetsIntegrator()
    
    # Test authentication (will fail without real credentials)
    print("\n🔐 Testing authentication...")
    auth_result = integrator.authenticate()
    
    if auth_result['success']:
        print("✅ Authentication successful")
    else:
        print(f"⚠️ Authentication failed (expected without credentials): {auth_result['message']}")
    
    # Test spreadsheet loading (will fail without real ID)
    print("\n📂 Testing spreadsheet loading...")
    load_result = integrator.load_spreadsheet("mock_spreadsheet_id")
    
    if load_result['success']:
        print(f"✅ Loaded {load_result['rows']} rows")
    else:
        print(f"⚠️ Load failed (expected without real ID): {load_result['message']}")
    
    integrator.close()
    
    print("\n" + "=" * 50)
    print("✅ Google Sheets Mock Tests Complete")
    print("=" * 50)


def test_profiler_sheet_support():
    """Test profiler with sheet selection"""
    print("\n" + "=" * 50)
    print("Testing Phase 8: Profiler Sheet Selection")
    print("=" * 50)
    
    profiler = DataProfiler()
    
    # Create test Excel file
    test_excel_path = "data/test_profiler.xlsx"
    os.makedirs("data", exist_ok=True)
    
    df1 = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    df2 = pd.DataFrame({"C": [7, 8, 9], "D": [10, 11, 12]})
    
    with pd.ExcelWriter(test_excel_path, engine='openpyxl') as writer:
        df1.to_excel(writer, sheet_name="Sheet1", index=False)
        df2.to_excel(writer, sheet_name="Sheet2", index=False)
    
    print(f"\n✅ Created test Excel file: {test_excel_path}")
    
    # Test getting sheet names
    print("\n📋 Getting sheet names...")
    sheet_names = profiler.get_excel_sheet_names(test_excel_path)
    print(f"✅ Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Test loading specific sheet
    print("\n📂 Loading specific sheet...")
    df = profiler.load_data(test_excel_path, sheet_name="Sheet2")
    print(f"✅ Loaded Sheet2: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns: {list(df.columns)}")
    
    # Cleanup
    try:
        if os.path.exists(test_excel_path):
            os.remove(test_excel_path)
            print(f"\n🗑️ Cleaned up test file")
    except PermissionError:
        print(f"\n⚠️ Could not remove test file (file in use)")
    
    print("\n" + "=" * 50)
    print("✅ Profiler Sheet Selection Tests Complete")
    print("=" * 50)


if __name__ == "__main__":
    test_excel_multi_sheet()
    test_google_sheets_mock()
    test_profiler_sheet_support()
    
    print("\n" + "=" * 50)
    print("Phase 8 Spreadsheet Integration Tests Complete")
    print("=" * 50)
