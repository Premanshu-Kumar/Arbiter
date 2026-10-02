"""
Cross Validator Agent - Runs the same question through both SQL and Python
and compares results to catch logic errors.
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from sandbox.executor import SafeExecutor
from agents.sql_agent import SQLAgent
from agents.python_agent import PythonAgent


class CrossValidator:
    """Executes the same analysis via SQL and Python, then cross-checks results.
    
    This agent is triggered when the validation policy decides that a
    cross-check is warranted (e.g. low confidence, aggregation, or explicit
    "BOTH" method selection).
    """
    
    def __init__(self):
        self.sql_agent = SQLAgent()
        self.python_agent = PythonAgent()
        self.executor = SafeExecutor()
    
    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    
    def cross_check(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any],
        df: pd.DataFrame,
        primary_result: Any = None,
        primary_method: str = "SQL",
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """Run the alternate method and compare results.
        
        Args:
            question: User's question
            schema: Schema string
            plan: Analysis plan dict
            df: Source DataFrame
            primary_result: The result already obtained by the primary method
            primary_method: "SQL" or "Python" — whichever ran first
            tolerance: Relative tolerance for numeric comparison (0.01 = 1%)
        
        Returns:
            dict with keys:
                match (bool), confidence (float), reasoning (str),
                primary_result, secondary_result, discrepancies (list)
        """
        # Generate and execute the alternate method
        secondary_method = "Python" if primary_method.upper() == "SQL" else "SQL"
        secondary_result = self._run_secondary(
            question, schema, plan, df, secondary_method
        )
        
        if secondary_result is None:
            return {
                "match": None,
                "confidence": 0.4,
                "reasoning": f"Cross-check inconclusive — {secondary_method} execution failed",
                "primary_result": primary_result,
                "secondary_result": None,
                "discrepancies": ["secondary method failed to produce a result"],
            }
        
        # Compare
        comparison = self._compare_results(
            primary_result, secondary_result, tolerance
        )
        
        return {
            "match": comparison["match"],
            "confidence": comparison["confidence"],
            "reasoning": comparison["reasoning"],
            "primary_result": primary_result,
            "secondary_result": secondary_result,
            "discrepancies": comparison["discrepancies"],
        }
    
    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------
    
    def _run_secondary(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any],
        df: pd.DataFrame,
        method: str,
    ) -> Optional[pd.DataFrame]:
        """Generate and execute code with the secondary method."""
        try:
            if method.upper() == "SQL":
                # Try Ollama first, fall back to mock
                try:
                    gen = self.sql_agent.generate_sql(question, schema, plan)
                    if not gen.get("success"):
                        gen = self.sql_agent.generate_sql_mock(question, schema, plan)
                except Exception:
                    gen = self.sql_agent.generate_sql_mock(question, schema, plan)
                
                if not gen.get("success") or not gen.get("code"):
                    return None
                
                self.executor.setup_duckdb(df, "data")
                exec_result = self.executor.execute_sql(gen["code"])
            else:
                try:
                    gen = self.python_agent.generate_python(question, schema, plan)
                    if not gen.get("success"):
                        gen = self.python_agent.generate_python_mock(question, schema, plan)
                except Exception:
                    gen = self.python_agent.generate_python_mock(question, schema, plan)
                
                if not gen.get("success") or not gen.get("code"):
                    return None
                
                exec_result = self.executor.execute_python(gen["code"], df)
            
            if exec_result.get("success"):
                return exec_result.get("result")
            return None
        except Exception:
            return None
    
    def _compare_results(
        self,
        primary: Any,
        secondary: Any,
        tolerance: float,
    ) -> Dict[str, Any]:
        """Compare two results and produce a structured comparison."""
        discrepancies: List[str] = []
        
        # Both are DataFrames
        if isinstance(primary, pd.DataFrame) and isinstance(secondary, pd.DataFrame):
            return self._compare_dataframes(primary, secondary, tolerance)
        
        # Both are lists (print output)
        if isinstance(primary, list) and isinstance(secondary, list):
            return self._compare_lists(primary, secondary)
        
        # Mixed types — structural mismatch
        if type(primary) != type(secondary):
            discrepancies.append(
                f"Type mismatch: primary={type(primary).__name__}, "
                f"secondary={type(secondary).__name__}"
            )
            return {
                "match": False,
                "confidence": 0.3,
                "reasoning": "Results have different types — possible logic divergence",
                "discrepancies": discrepancies,
            }
        
        # Scalar / string comparison
        if primary == secondary:
            return {
                "match": True,
                "confidence": 0.95,
                "reasoning": "Scalar results match exactly",
                "discrepancies": [],
            }
        
        return {
            "match": False,
            "confidence": 0.4,
            "reasoning": f"Scalar results differ: {primary!r} vs {secondary!r}",
            "discrepancies": [f"Value mismatch: {primary!r} ≠ {secondary!r}"],
        }
    
    def _compare_dataframes(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        tolerance: float,
    ) -> Dict[str, Any]:
        """Compare two DataFrames with tolerance for numeric columns."""
        discrepancies: List[str] = []
        confidence = 1.0
        
        # Row count comparison
        if len(df1) != len(df2):
            discrepancies.append(
                f"Row count mismatch: {len(df1)} vs {len(df2)}"
            )
            confidence -= 0.3
        
        # Column count comparison
        if len(df1.columns) != len(df2.columns):
            discrepancies.append(
                f"Column count mismatch: {len(df1.columns)} vs {len(df2.columns)}"
            )
            confidence -= 0.2
        
        # Compare common columns
        common_cols = set(df1.columns) & set(df2.columns)
        if not common_cols:
            # Try case-insensitive match
            df1_lower = {c.lower(): c for c in df1.columns}
            df2_lower = {c.lower(): c for c in df2.columns}
            common_lower = set(df1_lower) & set(df2_lower)
            if common_lower:
                discrepancies.append("Column names differ in case only")
                confidence -= 0.05
            else:
                discrepancies.append("No common columns between results")
                return {
                    "match": False,
                    "confidence": 0.2,
                    "reasoning": "Results have completely different column structures",
                    "discrepancies": discrepancies,
                }
        
        # Value-level comparison for common columns (use smaller row count)
        min_rows = min(len(df1), len(df2))
        if min_rows > 0 and common_cols:
            for col in common_cols:
                try:
                    s1 = df1[col].iloc[:min_rows].reset_index(drop=True)
                    s2 = df2[col].iloc[:min_rows].reset_index(drop=True)
                    
                    if pd.api.types.is_numeric_dtype(s1) and pd.api.types.is_numeric_dtype(s2):
                        # Numeric comparison with tolerance
                        if not np.allclose(
                            s1.fillna(0).values,
                            s2.fillna(0).values,
                            rtol=tolerance,
                            atol=1e-10,
                            equal_nan=True,
                        ):
                            max_diff = float(np.max(np.abs(s1.fillna(0).values - s2.fillna(0).values)))
                            discrepancies.append(
                                f"Numeric mismatch in '{col}' (max diff: {max_diff:.6f})"
                            )
                            confidence -= 0.15
                    else:
                        # Categorical comparison
                        mismatches = (s1.astype(str) != s2.astype(str)).sum()
                        if mismatches > 0:
                            discrepancies.append(
                                f"Value mismatch in '{col}': {mismatches}/{min_rows} rows differ"
                            )
                            confidence -= 0.1
                except Exception:
                    pass  # Skip columns that can't be compared
        
        confidence = max(0.0, confidence)
        match = len(discrepancies) == 0
        
        if match:
            reasoning = "Cross-check passed — SQL and Python results match"
        elif confidence >= 0.7:
            reasoning = "Results are close but have minor discrepancies"
        else:
            reasoning = "Significant discrepancies detected between SQL and Python results"
        
        return {
            "match": match,
            "confidence": confidence,
            "reasoning": reasoning,
            "discrepancies": discrepancies,
        }
    
    def _compare_lists(
        self,
        list1: list,
        list2: list,
    ) -> Dict[str, Any]:
        """Compare two list outputs (from print statements)."""
        discrepancies = []
        
        if len(list1) != len(list2):
            discrepancies.append(f"Output line count differs: {len(list1)} vs {len(list2)}")
        
        min_len = min(len(list1), len(list2))
        mismatches = 0
        for i in range(min_len):
            if str(list1[i]).strip() != str(list2[i]).strip():
                mismatches += 1
        
        if mismatches > 0:
            discrepancies.append(f"{mismatches}/{min_len} output lines differ")
        
        match = len(discrepancies) == 0
        confidence = 1.0 - (mismatches / max(min_len, 1)) * 0.5
        
        return {
            "match": match,
            "confidence": max(0.0, confidence),
            "reasoning": "Output comparison " + ("passed" if match else "found discrepancies"),
            "discrepancies": discrepancies,
        }
    
    def close(self):
        """Release resources."""
        self.executor.close()
