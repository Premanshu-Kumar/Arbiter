"""
Data Profiler Agent - Analyzes dataset structure and statistics
"""
import pandas as pd
import duckdb
from typing import Dict, Any, Optional, List
import config


class DataProfiler:
    """Profiles CSV/Excel datasets to understand structure and statistics"""
    
    def __init__(self):
        self.conn = None
    
    def load_data(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """Load data from CSV or Excel file
        
        Args:
            file_path: Path to file
            sheet_name: Specific sheet name for Excel files (optional)
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            return df
        except Exception as e:
            raise Exception(f"Error loading file: {str(e)}")
    
    def get_excel_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file"""
        try:
            if file_path.endswith(('.xlsx', '.xls')):
                excel_file = pd.ExcelFile(file_path)
                return excel_file.sheet_names
            else:
                return []
        except Exception as e:
            raise Exception(f"Error reading Excel sheets: {str(e)}")
    
    def profile_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive data profile"""
        profile = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': [],
            'missing_values': {},
            'data_types': {},
            'schema': ''
        }
        
        # Analyze each column
        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': df[col].isnull().sum(),
                'null_percentage': (df[col].isnull().sum() / len(df)) * 100,
                'unique_count': df[col].nunique()
            }
            
            # Add numeric statistics if applicable
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info.update({
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'mean': df[col].mean(),
                    'median': df[col].median(),
                    'std': df[col].std()
                })
            
            # Add sample values
            col_info['sample_values'] = df[col].dropna().head(5).tolist()
            
            profile['columns'].append(col_info)
            profile['missing_values'][col] = col_info['null_percentage']
            profile['data_types'][col] = str(df[col].dtype)
        
        # Generate schema string
        profile['schema'] = self._generate_schema_string(df)
        
        return profile
    
    def _generate_schema_string(self, df: pd.DataFrame) -> str:
        """Generate a readable schema string with clear type indicators"""
        schema_lines = [f"Columns: {len(df.columns)}", f"Rows: {len(df)}", "\nColumn Details:"]
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            
            # Add type indicator for easier parsing
            type_indicator = "NUMERIC" if pd.api.types.is_numeric_dtype(df[col]) else "CATEGORICAL"
            schema_lines.append(f"  - {col} ({dtype}) [{type_indicator}] - {null_pct:.1f}% null")
        
        return "\n".join(schema_lines)
    
    def setup_duckdb(self, df: pd.DataFrame, table_name: str = "data") -> duckdb.DuckDBPyConnection:
        """Setup DuckDB connection and register the dataframe"""
        try:
            self.conn = duckdb.connect()
            self.conn.register(table_name, df)
            return self.conn
        except Exception as e:
            raise Exception(f"Error setting up DuckDB: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
