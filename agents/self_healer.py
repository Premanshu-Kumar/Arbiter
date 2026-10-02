"""
Self-Healer Agent - Attempts to fix broken code using LLM error analysis.

When generated SQL or Python fails execution, this agent:
1. Classifies the error
2. Builds a targeted correction prompt with the error, the original code,
   the schema, and fix suggestions from the validator
3. Asks the LLM to produce a corrected version
4. Validates the corrected code for safety before returning it
"""
from typing import Dict, Any, Optional, List
from agents.ollama_client import OllamaClient
from agents.sql_agent import SQLAgent
from agents.python_agent import PythonAgent
from sandbox.safety import SQLSafetyValidator, PythonSafetyValidator
import config


class SelfHealer:
    """Attempts to automatically fix code that failed execution."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.sql_validator = SQLSafetyValidator()
        self.python_validator = PythonSafetyValidator()
        self.sql_agent = SQLAgent()
        self.python_agent = PythonAgent()
    
    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    
    def heal(
        self,
        code: str,
        code_type: str,
        error: str,
        question: str,
        schema: str,
        plan: Dict[str, Any],
        attempt: int = 0,
        suggestions: List[str] = None,
    ) -> Dict[str, Any]:
        """Attempt to fix broken code.
        
        Args:
            code: The code that failed
            code_type: "sql" or "python"
            error: Error message from execution
            question: Original user question
            schema: Data schema string
            plan: Analysis plan dict
            attempt: Which fix attempt this is (0-indexed)
            suggestions: Optional list of fix suggestions
        
        Returns:
            dict with keys: success (bool), code (str), reasoning (str),
                            fix_type (str)
        """
        if code_type.lower() == "sql":
            return self._heal_sql(code, error, question, schema, plan, attempt, suggestions)
        else:
            return self._heal_python(code, error, question, schema, plan, attempt, suggestions)
    
    # ------------------------------------------------------------------
    #  SQL healing
    # ------------------------------------------------------------------
    
    def _heal_sql(
        self,
        code: str,
        error: str,
        question: str,
        schema: str,
        plan: Dict[str, Any],
        attempt: int,
        suggestions: List[str] = None,
    ) -> Dict[str, Any]:
        """Fix broken SQL code."""
        # First try rule-based fixes for common issues
        rule_fix = self._apply_sql_rules(code, error, schema)
        if rule_fix is not None:
            # Validate the rule-based fix
            is_valid, val_error = self.sql_validator.validate(rule_fix)
            if is_valid:
                return {
                    "success": True,
                    "code": rule_fix,
                    "reasoning": "Applied rule-based SQL fix",
                    "fix_type": "rule_based",
                }
        
        # Fall back to LLM-based fix
        prompt = self._build_sql_fix_prompt(code, error, question, schema, suggestions)
        
        try:
            fixed_code = self.ollama_client.generate_code(
                prompt=prompt,
                model=config.CODER_MODEL,
                language="sql",
            )
            fixed_code = self.sql_agent._clean_sql(fixed_code)
            
            if not fixed_code or not fixed_code.strip():
                return self._fallback_regenerate("sql", question, schema, plan)
            
            # Safety validate
            is_valid, val_error = self.sql_validator.validate(fixed_code)
            if not is_valid:
                return {
                    "success": False,
                    "code": code,
                    "reasoning": f"LLM fix failed safety check: {val_error}",
                    "fix_type": "failed",
                }
            
            return {
                "success": True,
                "code": fixed_code,
                "reasoning": "LLM-corrected SQL code",
                "fix_type": "llm_fix",
            }
        except Exception as e:
            # Last resort: regenerate from scratch using mock
            return self._fallback_regenerate("sql", question, schema, plan)
    
    # ------------------------------------------------------------------
    #  Python healing
    # ------------------------------------------------------------------
    
    def _heal_python(
        self,
        code: str,
        error: str,
        question: str,
        schema: str,
        plan: Dict[str, Any],
        attempt: int,
        suggestions: List[str] = None,
    ) -> Dict[str, Any]:
        """Fix broken Python code."""
        # Try rule-based fixes first
        rule_fix = self._apply_python_rules(code, error, schema)
        if rule_fix is not None:
            is_valid, val_error = self.python_validator.validate(rule_fix)
            if is_valid:
                return {
                    "success": True,
                    "code": rule_fix,
                    "reasoning": "Applied rule-based Python fix",
                    "fix_type": "rule_based",
                }
        
        # LLM-based fix
        prompt = self._build_python_fix_prompt(code, error, question, schema, suggestions)
        
        try:
            fixed_code = self.ollama_client.generate_code(
                prompt=prompt,
                model=config.CODER_MODEL,
                language="python",
            )
            fixed_code = self.python_agent._clean_python(fixed_code)
            
            if not fixed_code or not fixed_code.strip():
                return self._fallback_regenerate("python", question, schema, plan)
            
            is_valid, val_error = self.python_validator.validate(fixed_code)
            if not is_valid:
                return {
                    "success": False,
                    "code": code,
                    "reasoning": f"LLM fix failed safety check: {val_error}",
                    "fix_type": "failed",
                }
            
            return {
                "success": True,
                "code": fixed_code,
                "reasoning": "LLM-corrected Python code",
                "fix_type": "llm_fix",
            }
        except Exception:
            return self._fallback_regenerate("python", question, schema, plan)
    
    # ------------------------------------------------------------------
    #  Rule-based fixes
    # ------------------------------------------------------------------
    
    def _apply_sql_rules(self, code: str, error: str, schema: str) -> Optional[str]:
        """Apply common rule-based SQL fixes.
        
        Returns corrected SQL or None if no rule applies.
        """
        error_lower = error.lower()
        code_upper = code.upper()
        
        # Fix: missing GROUP BY for aggregate
        if "group by" in error_lower or "aggregate" in error_lower:
            if "GROUP BY" not in code_upper and any(
                fn in code_upper for fn in ["SUM(", "AVG(", "COUNT(", "MIN(", "MAX("]
            ):
                # Try to add GROUP BY with non-aggregate columns from SELECT
                return self._add_group_by(code)
        
        # Fix: table name wrong
        if "table" in error_lower and "not found" in error_lower:
            import re
            # Replace any FROM <name> with FROM data
            fixed = re.sub(
                r'FROM\s+\w+', 'FROM data', code, flags=re.IGNORECASE
            )
            if fixed != code:
                return fixed
        
        # Fix: column name with spaces / special chars (DuckDB needs quotes)
        if "column" in error_lower and "does not exist" in error_lower:
            # Extract the problematic column from the error
            import re
            match = re.search(r'column\s+"?([^"]+)"?\s+does not exist', error, re.IGNORECASE)
            if match:
                bad_col = match.group(1)
                # Try to find a close match in the schema
                schema_cols = self._extract_columns_from_schema(schema)
                for sc in schema_cols:
                    if sc.lower() == bad_col.lower() and sc != bad_col:
                        return code.replace(bad_col, sc)
        
        # Fix: missing LIMIT (timeout hint)
        if "timeout" in error_lower and "LIMIT" not in code_upper:
            return code.rstrip().rstrip(";") + " LIMIT 1000"
        
        return None
    
    def _apply_python_rules(self, code: str, error: str, schema: str) -> Optional[str]:
        """Apply common rule-based Python fixes.
        
        Returns corrected Python or None if no rule applies.
        """
        error_lower = error.lower()
        
        # Fix: KeyError for column name
        if "keyerror" in error_lower:
            import re
            match = re.search(r"keyerror:?\s*['\"]?([^'\"]+)['\"]?", error, re.IGNORECASE)
            if match:
                bad_col = match.group(1).strip()
                schema_cols = self._extract_columns_from_schema(schema)
                for sc in schema_cols:
                    if sc.lower() == bad_col.lower() and sc != bad_col:
                        return code.replace(f"'{bad_col}'", f"'{sc}'").replace(
                            f'"{bad_col}"', f'"{sc}"'
                        )
        
        # Fix: NameError for 'result' — add print
        if "nameerror" in error_lower and "result" in error_lower:
            if "print(" not in code:
                return code + "\nprint(result)"
        
        # Fix: df not defined (shouldn't happen but handle)
        if "nameerror" in error_lower and "'df'" in error_lower:
            # The DataFrame is already injected — this means the code
            # references df before it exists. Nothing rule-based can fix.
            return None
        
        return None
    
    def _add_group_by(self, sql: str) -> str:
        """Try to add a GROUP BY clause to SQL with aggregates."""
        import re
        # Extract SELECT columns
        select_match = re.search(
            r'SELECT\s+(.*?)\s+FROM',
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not select_match:
            return sql
        
        select_clause = select_match.group(1)
        
        # Find non-aggregate columns
        agg_patterns = re.compile(
            r'(SUM|AVG|COUNT|MIN|MAX|STDDEV|VARIANCE)\s*\(',
            re.IGNORECASE,
        )
        
        parts = [p.strip() for p in select_clause.split(",")]
        non_agg = []
        for part in parts:
            # Skip if contains aggregate function
            if agg_patterns.search(part):
                continue
            # Get the column reference (before AS alias)
            col_ref = part.split(" AS ")[0].split(" as ")[0].strip()
            if col_ref:
                non_agg.append(col_ref)
        
        if not non_agg:
            return sql
        
        group_by_clause = ", ".join(non_agg)
        
        # Insert GROUP BY before ORDER BY or at the end
        if re.search(r'ORDER\s+BY', sql, re.IGNORECASE):
            return re.sub(
                r'(ORDER\s+BY)',
                f'GROUP BY {group_by_clause}\n\\1',
                sql,
                flags=re.IGNORECASE,
            )
        
        return sql.rstrip().rstrip(";") + f"\nGROUP BY {group_by_clause}"
    
    # ------------------------------------------------------------------
    #  LLM fix prompts
    # ------------------------------------------------------------------
    
    def _build_sql_fix_prompt(
        self,
        code: str,
        error: str,
        question: str,
        schema: str,
        suggestions: List[str] = None,
    ) -> str:
        suggestion_text = ""
        if suggestions:
            suggestion_text = "\n\nSuggested fixes:\n" + "\n".join(
                f"- {s}" for s in suggestions
            )
        
        return f"""Fix this DuckDB SQL query that produced an error.

Original question: {question}

Database schema:
{schema}

Broken SQL:
{code}

Error message:
{error}
{suggestion_text}

Rules:
1. Use DuckDB SQL syntax
2. The table name is 'data'
3. Only SELECT statements allowed
4. Fix the specific error while preserving the intent
5. If the column name is wrong, check the schema for the correct name
6. Ensure GROUP BY includes all non-aggregated columns

Return ONLY the corrected SQL query, no explanations."""
    
    def _build_python_fix_prompt(
        self,
        code: str,
        error: str,
        question: str,
        schema: str,
        suggestions: List[str] = None,
    ) -> str:
        suggestion_text = ""
        if suggestions:
            suggestion_text = "\n\nSuggested fixes:\n" + "\n".join(
                f"- {s}" for s in suggestions
            )
        
        return f"""Fix this Python code that produced an error.

Original question: {question}

Data schema:
{schema}

Broken code:
{code}

Error message:
{error}
{suggestion_text}

Rules:
1. The DataFrame is named 'df'
2. Use only pandas operations
3. Fix the specific error while preserving the intent
4. Print the final result
5. Check column names against the schema

Return ONLY the corrected Python code, no explanations."""
    
    # ------------------------------------------------------------------
    #  Fallback regeneration
    # ------------------------------------------------------------------
    
    def _fallback_regenerate(
        self,
        code_type: str,
        question: str,
        schema: str,
        plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Last resort: regenerate code from scratch using mock generators."""
        try:
            if code_type == "sql":
                result = self.sql_agent.generate_sql_mock(question, schema, plan)
            else:
                result = self.python_agent.generate_python_mock(question, schema, plan)
            
            if result.get("success") and result.get("code"):
                return {
                    "success": True,
                    "code": result["code"],
                    "reasoning": f"Regenerated {code_type} from scratch (mock fallback)",
                    "fix_type": "regenerated",
                }
        except Exception:
            pass
        
        return {
            "success": False,
            "code": "",
            "reasoning": "All fix attempts failed",
            "fix_type": "failed",
        }
    
    # ------------------------------------------------------------------
    #  Utilities
    # ------------------------------------------------------------------
    
    @staticmethod
    def _extract_columns_from_schema(schema: str) -> List[str]:
        """Extract column names from a schema string."""
        columns = []
        for line in schema.split("\n"):
            line = line.strip()
            if line.startswith("- ") and "(" in line:
                col_name = line[2:].split("(")[0].strip()
                if col_name:
                    columns.append(col_name)
        return columns
