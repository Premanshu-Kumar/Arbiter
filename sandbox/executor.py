"""
Safe Executor - Executes SQL and Python code in a sandboxed environment
"""
import duckdb
import pandas as pd
import signal
import threading
import time
import re
from typing import Dict, Any, Optional
import config
from sandbox.safety import SQLSafetyValidator, PythonSafetyValidator


class SafeExecutor:
    """Executes code safely with validation and timeout protection"""
    
    def __init__(self):
        self.sql_validator = SQLSafetyValidator()
        self.python_validator = PythonSafetyValidator()
        self.conn = None
        self.table_name = "data"
    
    def setup_duckdb(self, df: pd.DataFrame, table_name: str = "data") -> bool:
        """Setup DuckDB connection and register DataFrame"""
        try:
            self.conn = duckdb.connect()
            self.conn.register(table_name, df)
            self.table_name = table_name
            return True
        except Exception as e:
            print(f"Error setting up DuckDB: {str(e)}")
            return False
    
    def execute_sql(
        self,
        sql: str,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Execute SQL query safely
        
        Args:
            sql: SQL query to execute
            timeout: Execution timeout in seconds
        
        Returns:
            Execution result with metadata
        """
        timeout = timeout or config.EXECUTION_TIMEOUT
        
        # Validate SQL first
        is_valid, error = self.sql_validator.validate(sql)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "result": None,
                "reasoning": f"SQL validation failed: {error}"
            }
        
        # Execute with timeout
        try:
            result = self._execute_with_timeout(
                self._execute_sql_internal,
                sql,
                timeout=timeout
            )
            
            return {
                "success": True,
                "result": result,
                "error": None,
                "reasoning": "SQL executed successfully"
            }
            
        except TimeoutError:
            return {
                "success": False,
                "error": "Query execution timeout",
                "result": None,
                "reasoning": f"SQL execution exceeded timeout of {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "reasoning": f"SQL execution failed: {str(e)}"
            }
    
    def _execute_sql_internal(self, sql: str) -> pd.DataFrame:
        """Internal SQL execution"""
        if not self.conn:
            raise Exception("DuckDB connection not established")
        
        # Replace table name if needed (case-insensitive)
        sql = re.sub(r'FROM\s+data', f'FROM {self.table_name}', sql, flags=re.IGNORECASE)
        sql = re.sub(r'from\s+data', f'from {self.table_name}', sql, flags=re.IGNORECASE)
        
        result = self.conn.execute(sql).fetchdf()
        return result
    
    def execute_python(
        self,
        code: str,
        df: pd.DataFrame,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Execute Python code safely
        
        Args:
            code: Python code to execute
            df: DataFrame to make available to the code
            timeout: Execution timeout in seconds
        
        Returns:
            Execution result with metadata
        """
        timeout = timeout or config.EXECUTION_TIMEOUT
        
        # Validate Python code first
        is_valid, error = self.python_validator.validate(code)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "result": None,
                "reasoning": f"Python validation failed: {error}"
            }
        
        # Execute with timeout
        try:
            result = self._execute_with_timeout(
                self._execute_python_internal,
                code,
                df,
                timeout=timeout
            )
            
            return {
                "success": True,
                "result": result,
                "error": None,
                "reasoning": "Python executed successfully"
            }
            
        except TimeoutError:
            return {
                "success": False,
                "error": "Code execution timeout",
                "result": None,
                "reasoning": f"Python execution exceeded timeout of {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "reasoning": f"Python execution failed: {str(e)}"
            }
    
    def _execute_python_internal(self, code: str, df: pd.DataFrame) -> Any:
        """Internal Python execution with restricted environment"""
        # Create restricted execution environment
        allowed_globals = {
            'pd': pd,
            'df': df,
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'enumerate': enumerate,
                'zip': zip,
                'filter': filter,
                'map': map,
                'sorted': sorted,
                'any': any,
                'all': all,
            }
        }
        
        # Capture output
        output_buffer = []
        
        def custom_print(*args, **kwargs):
            output_buffer.append(' '.join(str(arg) for arg in args))
        
        allowed_globals['print'] = custom_print
        
        # Execute code
        try:
            exec(code, allowed_globals, {})
            
            # Try to return the last meaningful result
            if output_buffer:
                return output_buffer
            else:
                return "Code executed successfully (no output)"
                
        except Exception as e:
            raise Exception(f"Execution error: {str(e)}")
    
    def _execute_with_timeout(self, func, *args, **kwargs):
        """Execute function with timeout protection"""
        timeout = kwargs.pop('timeout', 30)  # Default 30 seconds
        result = []
        exception = []
        
        def target():
            try:
                result.append(func(*args))
            except Exception as e:
                exception.append(e)
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            raise TimeoutError("Execution timeout")
        
        if exception:
            raise exception[0]
        
        return result[0] if result else None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


class DuckDBExecutor:
    """Specialized executor for DuckDB SQL operations"""
    
    def __init__(self):
        self.conn = None
        self.validator = SQLSafetyValidator()
    
    def connect(self, df: pd.DataFrame, table_name: str = "data") -> bool:
        """Connect to DuckDB with DataFrame"""
        try:
            self.conn = duckdb.connect()
            self.conn.register(table_name, df)
            return True
        except Exception as e:
            print(f"DuckDB connection error: {str(e)}")
            return False
    
    def execute_query(
        self,
        query: str,
        timeout: int = None
    ) -> Dict[str, Any]:
        """Execute SQL query with safety checks"""
        timeout = timeout or config.EXECUTION_TIMEOUT
        
        # Validate query
        is_valid, error = self.validator.validate(query)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "result": None
            }
        
        try:
            # Execute with timeout
            result = self._execute_with_timeout(query, timeout=timeout)
            
            return {
                "success": True,
                "result": result,
                "error": None,
                "row_count": len(result),
                "column_count": len(result.columns)
            }
            
        except TimeoutError:
            return {
                "success": False,
                "error": "Query timeout",
                "result": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def _execute_with_timeout(self, query: str, timeout: int) -> pd.DataFrame:
        """Execute query with timeout"""
        result = []
        exception = []
        
        def target():
            try:
                result.append(self.conn.execute(query).fetchdf())
            except Exception as e:
                exception.append(e)
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            raise TimeoutError("Query execution timeout")
        
        if exception:
            raise exception[0]
        
        return result[0] if result else pd.DataFrame()
    
    def get_table_info(self, table_name: str = "data") -> Dict[str, Any]:
        """Get information about the registered table"""
        try:
            # Get column info
            columns_info = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()
            
            # Get row count
            row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            return {
                "columns": columns_info.to_dict('records'),
                "row_count": row_count,
                "column_count": len(columns_info)
            }
        except Exception as e:
            return {
                "error": str(e),
                "columns": [],
                "row_count": 0,
                "column_count": 0
            }
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
            self.conn = None