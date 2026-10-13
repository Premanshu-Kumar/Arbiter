"""
Excel Multi-Sheet Handler - Phase 8

Handles multi-sheet Excel workbook operations including:
- Sheet selection and analysis
- Multi-sheet data loading
- Sheet-wise analysis
- Result export to Excel sheets
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
import os
import config


class ExcelMultiSheetHandler:
    """
    Handler for multi-sheet Excel workbook operations.
    
    Supports:
    - Loading multi-sheet workbooks
    - Sheet selection
    - Multi-sheet analysis
    - Result export to Excel
    - Summary and insights sheets
    """
    
    def __init__(self):
        self.workbook_path: Optional[str] = None
        self.workbook: Optional[Workbook] = None
        self.sheets: Dict[str, pd.DataFrame] = {}
        self.sheet_names: List[str] = []
    
    def load_workbook(self, file_path: str) -> Dict[str, Any]:
        """
        Load an Excel workbook with all sheets.
        
        Args:
            file_path: Path to Excel file (.xlsx, .xls)
        
        Returns:
            Dictionary with sheet information
        """
        if not file_path.endswith(('.xlsx', '.xls')):
            raise ValueError(f"Unsupported file format: {file_path}")
        
        self.workbook_path = file_path
        
        try:
            # Load all sheets
            excel_file = pd.ExcelFile(file_path)
            self.sheet_names = excel_file.sheet_names
            
            # Load each sheet as DataFrame
            self.sheets = {}
            for sheet_name in self.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                self.sheets[sheet_name] = df
            
            return {
                "success": True,
                "sheet_count": len(self.sheet_names),
                "sheet_names": self.sheet_names,
                "sheets": {name: {"rows": len(df), "columns": len(df.columns)} 
                          for name, df in self.sheets.items()},
                "message": f"Loaded {len(self.sheet_names)} sheets"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to load workbook: {str(e)}"
            }
    
    def get_sheet(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """
        Get a specific sheet as DataFrame.
        
        Args:
            sheet_name: Name of the sheet
        
        Returns:
            DataFrame or None if sheet not found
        """
        return self.sheets.get(sheet_name)
    
    def get_sheet_info(self, sheet_name: str) -> Dict[str, Any]:
        """
        Get information about a specific sheet.
        
        Args:
            sheet_name: Name of the sheet
        
        Returns:
            Sheet information dictionary
        """
        df = self.sheets.get(sheet_name)
        if df is None:
            return {
                "success": False,
                "error": f"Sheet '{sheet_name}' not found"
            }
        
        return {
            "success": True,
            "sheet_name": sheet_name,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": df.isnull().sum().to_dict(),
            "memory_usage": df.memory_usage(deep=True).sum()
        }
    
    def analyze_sheet(self, sheet_name: str) -> Dict[str, Any]:
        """
        Perform basic analysis on a sheet.
        
        Args:
            sheet_name: Name of the sheet to analyze
        
        Returns:
            Analysis results
        """
        df = self.sheets.get(sheet_name)
        if df is None:
            return {
                "success": False,
                "error": f"Sheet '{sheet_name}' not found"
            }
        
        # Basic statistics
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        analysis = {
            "success": True,
            "sheet_name": sheet_name,
            "shape": df.shape,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "numeric_stats": {},
            "categorical_stats": {}
        }
        
        # Numeric statistics
        if numeric_cols:
            analysis["numeric_stats"] = df[numeric_cols].describe().to_dict()
        
        # Categorical statistics
        if categorical_cols:
            for col in categorical_cols:
                analysis["categorical_stats"][col] = {
                    "unique_count": df[col].nunique(),
                    "top_values": df[col].value_counts().head(5).to_dict()
                }
        
        return analysis
    
    def export_results_to_excel(
        self,
        results: Dict[str, Any],
        output_path: str,
        create_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Export analysis results to a new Excel workbook.
        
        Args:
            results: Analysis results dictionary
            output_path: Path for output Excel file
            create_summary: Whether to create a summary sheet
        
        Returns:
            Export status
        """
        try:
            # Create new workbook
            wb = Workbook()
            wb.remove(wb.active)  # Remove default sheet
            
            # Add results sheet
            if results.get('result') is not None:
                if isinstance(results['result'], pd.DataFrame):
                    ws = wb.create_sheet("Analysis Results")
                    # Write DataFrame to sheet
                    for r_idx, row in enumerate(results['result'].values, 1):
                        for c_idx, value in enumerate(row, 1):
                            ws.cell(row=r_idx, column=c_idx, value=value)
                    
                    # Add headers
                    for c_idx, col_name in enumerate(results['result'].columns, 1):
                        ws.cell(row=1, column=c_idx, value=col_name)
                        ws.cell(row=1, column=c_idx).font = Font(bold=True)
            
            # Add code sheet
            if results.get('code'):
                ws = wb.create_sheet("Generated Code")
                ws.cell(row=1, column=1, value="Code Type")
                ws.cell(row=1, column=2, value="Generated Code")
                ws.cell(row=1, column=1).font = Font(bold=True)
                ws.cell(row=1, column=2).font = Font(bold=True)
                
                ws.cell(row=2, column=1, value=results.get('code_type', 'unknown'))
                ws.cell(row=2, column=2, value=results['code'])
            
            # Add insights sheet
            if results.get('insights'):
                ws = wb.create_sheet("Insights")
                ws.cell(row=1, column=1, value="Insights")
                ws.cell(row=1, column=1).font = Font(bold=True)
                
                for i, insight in enumerate(results['insights'], 2):
                    ws.cell(row=i, column=1, value=insight)
            
            # Add summary sheet
            if create_summary:
                ws = wb.create_sheet("Summary")
                ws.cell(row=1, column=1, value="Analysis Summary")
                ws.cell(row=1, column=1).font = Font(bold=True)
                ws.cell(row=1, column=1).font = Font(size=14)
                
                row = 3
                ws.cell(row=row, column=1, value="Question:")
                ws.cell(row=row, column=2, value=results.get('question', 'N/A'))
                row += 2
                
                ws.cell(row=row, column=1, value="Selected Agent:")
                ws.cell(row=row, column=2, value=results.get('selected_agent', 'N/A'))
                row += 2
                
                ws.cell(row=row, column=1, value="Validation Status:")
                status = "✅ Passed" if results.get('valid') else "❌ Failed"
                ws.cell(row=row, column=2, value=status)
                row += 2
                
                if results.get('error'):
                    ws.cell(row=row, column=1, value="Error:")
                    ws.cell(row=row, column=2, value=results['error'])
                    row += 2
                
                ws.cell(row=row, column=1, value="Charts Generated:")
                ws.cell(row=row, column=2, value=len(results.get('charts', [])))
            
            # Save workbook
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            wb.save(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
                "message": f"Results exported to {output_path}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to export results: {str(e)}"
            }
    
    def create_multi_sheet_analysis(
        self,
        analysis_type: str = "aggregation"
    ) -> Dict[str, Any]:
        """
        Perform analysis across multiple sheets.
        
        Args:
            analysis_type: Type of analysis (aggregation, comparison, summary)
        
        Returns:
            Multi-sheet analysis results
        """
        results = {
            "success": True,
            "analysis_type": analysis_type,
            "sheets_analyzed": [],
            "combined_results": {}
        }
        
        for sheet_name in self.sheet_names:
            df = self.sheets.get(sheet_name)
            if df is None:
                continue
            
            sheet_result = {
                "sheet_name": sheet_name,
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": df.select_dtypes(include=['number']).columns.tolist()
            }
            
            results["sheets_analyzed"].append(sheet_result)
            
            if analysis_type == "aggregation":
                # Sum numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    results["combined_results"][sheet_name] = df[numeric_cols].sum().to_dict()
            
            elif analysis_type == "summary":
                results["combined_results"][sheet_name] = {
                    "shape": df.shape,
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "null_counts": df.isnull().sum().to_dict()
                }
        
        return results
    
    def close(self):
        """Close workbook and cleanup"""
        self.workbook = None
        self.sheets = {}
        self.sheet_names = []
