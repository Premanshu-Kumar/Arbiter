"""
Python Agent - Generates Python code using local LLM
"""
from typing import Dict, Any
from agents.ollama_client import OllamaClient
import config


class PythonAgent:
    """Generates Python code for data analysis"""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def generate_python(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Python code based on question and schema
        
        Args:
            question: User's natural language question
            schema: Data schema information
            plan: Analysis plan from Jev Planner
        
        Returns:
            Generated Python code with metadata
        """
        # Build the prompt
        prompt = self._build_python_prompt(question, schema, plan)
        
        # Generate Python using coding model
        try:
            python_code = self.ollama_client.generate_code(
                prompt=prompt,
                model=config.CODER_MODEL,
                language="python"
            )
            
            # Clean and validate the generated Python
            cleaned_python = self._clean_python(python_code)
            
            return {
                "code": cleaned_python,
                "code_type": "python",
                "method": "Python",
                "success": True,
                "reasoning": "Python code generated successfully"
            }
            
        except Exception as e:
            return {
                "code": "",
                "code_type": "python",
                "method": "Python",
                "success": False,
                "error": str(e),
                "reasoning": f"Python generation failed: {str(e)}"
            }
    
    def generate_python_mock(self, question: str, schema: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Python generation for testing without Ollama"""
        # Enhanced rule-based Python generation with real column names
        question_lower = question.lower()
        
        # Extract row count from schema
        row_count = 0
        for line in schema.split("\n"):
            if "Rows:" in line:
                try:
                    row_count = int(line.split("Rows:")[1].strip())
                except:
                    pass
        
        # Extract column names and types from schema
        columns = []
        cat_cols = []
        num_cols = []
        
        for line in schema.split("\n"):
            if "–" in line or "-" in line:
                line = line.replace("–", "-")
                parts = line.split("-")
                if len(parts) >= 1:
                    col_name = parts[0].strip()
                    if col_name and not col_name.startswith("Column") and col_name != "Columns" and col_name != "Rows":
                        columns.append(col_name)
                        
                        if "[NUMERIC]" in line.upper():
                            num_cols.append(col_name)
                        elif "[CATEGORICAL]" in line.upper():
                            cat_cols.append(col_name)
        
        # Detect mentioned columns
        sql_keywords = {'average', 'mean', 'sum', 'count', 'max', 'min', 'total', 'top', 'bottom', 'by', 'per', 'each', 'group'}
        mentioned_columns = []
        for col in columns:
            col_lower = col.lower()
            words = question_lower.split()
            meaningful_words = [w for w in words if w not in sql_keywords and len(w) >= 3]
            
            for word in meaningful_words:
                if word == col_lower or word in col_lower:
                    mentioned_columns.append(col)
                    break
        
        mentioned_cat = [col for col in mentioned_columns if col in cat_cols]
        mentioned_num = [col for col in mentioned_columns if col in num_cols]
        
        # Check for grouping pattern
        has_grouping_keyword = any(word in question_lower for word in ['by', 'per', 'for each', 'group'])
        has_grouping_pattern = len(mentioned_cat) >= 1 and len(mentioned_num) >= 1
        
        # Generate code based on query type
        if "average" in question_lower or "mean" in question_lower:
            if has_grouping_keyword or has_grouping_pattern:
                group_col = mentioned_cat[0] if mentioned_cat else (cat_cols[0] if cat_cols else 'category')
                agg_col = mentioned_num[0] if mentioned_num else (num_cols[0] if num_cols else 'value')
                return {
                    "code": f"result = df.groupby('{group_col}')['{agg_col}'].mean()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": f"Generated Python for average {agg_col} by {group_col}"
                }
            elif num_cols:
                return {
                    "code": f"result = df['{num_cols[0]}'].mean()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": f"Generated Python for average of {num_cols[0]}"
                }
            else:
                return {
                    "code": "result = df.groupby('category')['value'].mean()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": "Generated Python for average calculation"
                }
        elif "sum" in question_lower or "total" in question_lower:
            if has_grouping_keyword or has_grouping_pattern:
                group_col = mentioned_cat[0] if mentioned_cat else (cat_cols[0] if cat_cols else 'category')
                agg_col = mentioned_num[0] if mentioned_num else (num_cols[0] if num_cols else 'value')
                return {
                    "code": f"result = df.groupby('{group_col}')['{agg_col}'].sum()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": f"Generated Python for sum {agg_col} by {group_col}"
                }
            elif num_cols:
                return {
                    "code": f"result = df['{num_cols[0]}'].sum()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": f"Generated Python for sum of {num_cols[0]}"
                }
            else:
                return {
                    "code": "result = df.groupby('category')['value'].sum()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": "Generated Python for sum calculation"
                }
        elif "count" in question_lower:
            if cat_cols:
                return {
                    "code": f"result = df.groupby('{cat_cols[0]}').size()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": f"Generated Python for count by {cat_cols[0]}"
                }
            else:
                return {
                    "code": "result = df.groupby('category').size()\nprint(result)",
                    "code_type": "python",
                    "method": "Python",
                    "success": True,
                    "reasoning": "Generated Python for count calculation"
                }
        else:
            # Default operation - show all data for small datasets
            limit_clause = ""
            if row_count > 1000:
                limit_clause = ".head(1000)"
            
            return {
                "code": f"result = df{limit_clause}\nprint(result)",
                "code_type": "python",
                "method": "Python",
                "success": True,
                "reasoning": f"Generated default Python code (dataset has {row_count} rows)"
            }
    
    def _build_python_prompt(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any]
    ) -> str:
        """Build the prompt for Python generation"""
        prompt = f"""Generate Python code using pandas to answer this question:
Question: {question}

Data Schema:
{schema}

Analysis Requirements:
- Method: Python
- Requires Aggregation: {plan.get('requires_aggregation', False)}
- Requires Time Series: {plan.get('requires_time_series', False)}
- Requires Filtering: {plan.get('requires_filtering', False)}
- Requires Sorting: {plan.get('requires_sorting', False)}

Important Rules:
1. Assume the data is in a pandas DataFrame called 'df'
2. Use pandas operations for filtering, grouping, and aggregation
3. Use df.groupby() for aggregations
4. Use df.sort_values() for sorting
5. Use df[df['column'].condition] for filtering
6. Use pd.to_datetime() for date operations
7. Use .resample() for time series analysis
8. Print the final result using print()
9. Keep the code simple and readable
10. Don't use any external libraries besides pandas and numpy

Generate only the Python code, no explanations.
"""
        return prompt
    
    def _clean_python(self, python: str) -> str:
        """Clean and format the generated Python"""
        # Remove markdown code blocks if present
        python = python.strip()
        if python.startswith("```"):
            python = python.split("```")[1]
            if python.startswith("python"):
                python = python[6:]
        if python.endswith("```"):
            python = python[:-3]
        
        # Remove common prefixes
        python = python.strip()
        if python.startswith("import") or python.startswith("df"):
            # Already clean
            pass
        elif python.lower().startswith("here is") or python.lower().startswith("the python"):
            # Remove explanatory text
            lines = python.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("import") or line.strip().startswith("df"):
                    python = "\n".join(lines[i:])
                    break
        
        return python.strip()
    
    def validate_python(self, python: str) -> tuple[bool, str]:
        """
        Validate the generated Python for safety
        
        Returns:
            (is_valid, error_message)
        """
        # Blocked imports
        blocked_imports = [
            "os", "subprocess", "sys", "socket", "requests", "urllib",
            "http", "ftplib", "smtplib", "telnetlib", "pickle", "shelve",
            "eval", "exec", "compile", "__import__"
        ]
        
        python_lower = python.lower()
        
        for blocked in blocked_imports:
            if f"import {blocked}" in python_lower or f"from {blocked}" in python_lower:
                return False, f"Blocked import detected: {blocked}"
        
        # Check for dangerous functions
        dangerous_functions = ["eval(", "exec(", "compile(", "__import__("]
        for func in dangerous_functions:
            if func in python_lower:
                return False, f"Dangerous function detected: {func}"
        
        # Check for file operations
        file_operations = ["open(", "file(", "write(", "read("]
        for op in file_operations:
            if op in python_lower:
                return False, f"File operation detected: {op}"
        
        # Check for network operations
        network_operations = ["socket.", "requests.", "urllib.", "http."]
        for op in network_operations:
            if op in python_lower:
                return False, f"Network operation detected: {op}"
        
        return True, ""
    
    def explain_python(self, python: str) -> str:
        """Generate a natural language explanation of the Python code"""
        prompt = f"""Explain this Python code in simple terms:
{python}

Provide a brief explanation of what the code does.
"""
        
        try:
            explanation = self.ollama_client.generate(
                prompt=prompt,
                model=config.REASONING_MODEL,
                max_tokens=300
            )
            return explanation
        except Exception as e:
            return f"Could not generate explanation: {str(e)}"
    
    def fix_python(self, python: str, error: str) -> str:
        """Fix Python code based on error message"""
        prompt = f"""Fix this Python code that has an error:
Code:
{python}

Error:
{error}

Provide the corrected code only, no explanations.
"""
        
        try:
            fixed_code = self.ollama_client.generate_code(
                prompt=prompt,
                model=config.CODER_MODEL,
                language="python"
            )
            return self._clean_python(fixed_code)
        except Exception as e:
            return python  # Return original if fix fails
    
    def suggest_libraries(self, question: str) -> list:
        """Suggest relevant pandas libraries/functions based on the question"""
        question_lower = question.lower()
        
        suggestions = {
            "aggregation": ["groupby", "agg", "sum", "mean", "count", "std"],
            "filtering": ["query", "loc", "isin", "between"],
            "time_series": ["to_datetime", "resample", "dt", "rolling"],
            "sorting": ["sort_values", "sort_index"],
            "merging": ["merge", "join", "concat"],
            "pivoting": ["pivot", "pivot_table", "melt"],
            "statistics": ["describe", "corr", "cov", "value_counts"]
        }
        
        relevant = []
        for category, functions in suggestions.items():
            if any(keyword in question_lower for keyword in 
                  ["group", "aggregate", "sum", "average"] if category == "aggregation" or
                  ["filter", "where", "only"] if category == "filtering" or
                  ["time", "date", "trend"] if category == "time_series" or
                  ["sort", "top", "bottom"] if category == "sorting" or
                  ["join", "merge", "combine"] if category == "merging" or
                  ["pivot", "reshape"] if category == "pivoting" or
                  ["statistic", "correlation", "describe"] if category == "statistics"):
                relevant.extend(functions)
        
        return relevant if relevant else ["head", "describe", "info"]
