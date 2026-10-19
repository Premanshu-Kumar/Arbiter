"""
SQL Agent - Generates SQL queries using local LLM
"""
from typing import Dict, Any
from agents.ollama_client import OllamaClient
import config


class SQLAgent:
    """Generates SQL queries for data analysis"""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def generate_sql(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate SQL query based on question and schema
        
        Args:
            question: User's natural language question
            schema: Data schema information
            plan: Analysis plan from Jev Planner
        
        Returns:
            Generated SQL query with metadata
        """
        # Build the prompt
        prompt = self._build_sql_prompt(question, schema, plan)
        
        # Generate SQL using coding model
        try:
            sql_code = self.ollama_client.generate_code(
                prompt=prompt,
                model=config.CODER_MODEL,
                language="sql"
            )
            
            # Clean and validate the generated SQL
            cleaned_sql = self._clean_sql(sql_code)
            
            # Additional validation for empty SQL
            if not cleaned_sql or not cleaned_sql.strip():
                return {
                    "code": "",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": False,
                    "error": "Generated SQL is empty",
                    "reasoning": "SQL generation returned empty code"
                }
            
            return {
                "code": cleaned_sql,
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": "SQL generated successfully"
            }
            
        except Exception as e:
            return {
                "code": "",
                "code_type": "sql",
                "method": "SQL",
                "success": False,
                "error": str(e),
                "reasoning": f"SQL generation failed: {str(e)}"
            }
    
    def generate_sql_mock(self, question: str, schema: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Mock SQL generation for testing without Ollama"""
        # Enhanced rule-based SQL generation
        question_lower = question.lower()
        
        # Extract column names and types from schema
        columns = []
        cat_cols = []
        num_cols = []
        
        for line in schema.split("\n"):
            # Try to match the schema line format: "  - column (dtype) [TYPE] - null%"
            # Handle both regular dash and en dash
            if "–" in line or "-" in line:
                # Replace en dash with regular dash
                line = line.replace("–", "-")
                # Remove multiple spaces
                line = " ".join(line.split())
                parts = line.split("-")
                if len(parts) >= 1:
                    col_name = parts[0].strip()
                    if col_name and not col_name.startswith("Column") and col_name != "Columns" and col_name != "Rows":
                        columns.append(col_name)
                        
                        # Check type indicator
                        if "[NUMERIC]" in line.upper():
                            num_cols.append(col_name)
                        elif "[CATEGORICAL]" in line.upper():
                            cat_cols.append(col_name)
        
        # Detect mentioned columns in question (smart word-level matching)
        mentioned_columns = []
        sql_keywords = {'average', 'mean', 'sum', 'count', 'max', 'min', 'total', 'top', 'bottom', 'by', 'per', 'each', 'group'}
        
        for col in columns:
            col_lower = col.lower()
            # Check if any word from the question matches the column name
            words = question_lower.split()
            # Filter out SQL keywords
            meaningful_words = [w for w in words if w not in sql_keywords and len(w) >= 3]
            
            for word in meaningful_words:
                # Check if word matches column name or is contained in it
                if word == col_lower or word in col_lower:
                    mentioned_columns.append(col)
                    break
        
        mentioned_cat = [col for col in mentioned_columns if col in cat_cols]
        mentioned_num = [col for col in mentioned_columns if col in num_cols]
        
        # Determine aggregation function
        agg_func = None
        if 'average' in question_lower or 'mean' in question_lower:
            agg_func = 'AVG'
        elif 'sum' in question_lower or 'total' in question_lower:
            agg_func = 'SUM'
        elif 'count' in question_lower:
            agg_func = 'COUNT'
        elif 'max' in question_lower or 'maximum' in question_lower:
            agg_func = 'MAX'
        elif 'min' in question_lower or 'minimum' in question_lower:
            agg_func = 'MIN'
        
        # Check if this is a grouping query (has grouping keyword OR has both cat and num columns mentioned)
        has_grouping_keyword = any(word in question_lower for word in ['by', 'per', 'for each', 'group'])
        has_grouping_pattern = len(mentioned_cat) >= 1 and len(mentioned_num) >= 1
        
        # Handle grouping/aggregation queries
        if has_grouping_keyword or has_grouping_pattern:
            # Use mentioned columns if available, otherwise use first of each type
            group_col = mentioned_cat[0] if mentioned_cat else (cat_cols[0] if cat_cols else None)
            agg_col = mentioned_num[0] if mentioned_num else (num_cols[0] if num_cols else None)
            
            if group_col and agg_col and agg_func:
                return {
                    "code": f"SELECT {group_col}, {agg_func}({agg_col}) as {agg_func.lower()}_{agg_col} FROM data GROUP BY {group_col}",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for {agg_func.lower()} {agg_col} by {group_col}"
                }
            elif group_col and agg_func == 'COUNT':
                return {
                    "code": f"SELECT {group_col}, COUNT(*) as count FROM data GROUP BY {group_col}",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for count by {group_col}"
                }
        
        # Handle single column aggregations
        if agg_func and mentioned_num:
            return {
                "code": f"SELECT {agg_func}({', '.join(mentioned_num)}) as {agg_func.lower()}_value FROM data",
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": f"Generated SQL for {agg_func.lower()} of {', '.join(mentioned_num)}"
            }
        elif agg_func and num_cols:
            return {
                "code": f"SELECT {agg_func}({num_cols[0]}) as {agg_func.lower()}_value FROM data",
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": f"Generated SQL for {agg_func.lower()} of {num_cols[0]}"
            }
        
        # Handle count of categorical
        if 'count' in question_lower and mentioned_cat:
            return {
                "code": f"SELECT {mentioned_cat[0]}, COUNT(*) as count FROM data GROUP BY {mentioned_cat[0]}",
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": f"Generated SQL for count by {mentioned_cat[0]}"
            }
        elif 'count' in question_lower and cat_cols:
            return {
                "code": f"SELECT {cat_cols[0]}, COUNT(*) as count FROM data GROUP BY {cat_cols[0]}",
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": f"Generated SQL for count by {cat_cols[0]}"
            }
        
        # Handle top/bottom queries
        if "top" in question_lower and num_cols:
            return {
                "code": f"SELECT * FROM data ORDER BY {num_cols[0]} DESC LIMIT 10",
                "code_type": "sql",
                "method": "SQL",
                "success": True,
                "reasoning": f"Generated SQL for top values by {num_cols[0]}"
            }
        
        # Default SELECT
        # Default SELECT - show all data
        return {
            "code": "SELECT * FROM data",
            "code_type": "sql",
            "method": "SQL",
            "success": True,
            "reasoning": "Generated default SELECT query"
        }
    
    def _build_sql_prompt(
        self,
        question: str,
        schema: str,
        plan: Dict[str, Any]
    ) -> str:
        """Build the prompt for SQL generation"""
        prompt = f"""Generate a DuckDB SQL query to answer this question:
Question: {question}

Database Schema:
{schema}

Analysis Requirements:
- Method: SQL
- Requires Aggregation: {plan.get('requires_aggregation', False)}
- Requires Time Series: {plan.get('requires_time_series', False)}
- Requires Filtering: {plan.get('requires_filtering', False)}
- Requires Sorting: {plan.get('requires_sorting', False)}

Important Rules:
1. Use DuckDB SQL syntax
2. Assume the table name is 'data'
3. Only use SELECT statements (no DROP, DELETE, UPDATE, INSERT, etc.)
4. Use appropriate aggregate functions (SUM, AVG, COUNT, etc.) when needed
5. Use GROUP BY for aggregations
6. Use ORDER BY for sorting
7. Use WHERE for filtering
8. Use DATE_TRUNC for time series analysis
9. Include column aliases for clarity
10. Return all rows (no LIMIT) unless specifically requested

Generate only the SQL query, no explanations.
"""
        return prompt
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and format the generated SQL"""
        # Remove markdown code blocks if present
        sql = sql.strip()
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        # Remove common prefixes
        sql = sql.strip()
        if sql.lower().startswith("select"):
            # Already clean
            pass
        elif sql.lower().startswith("here is") or sql.lower().startswith("the sql"):
            # Remove explanatory text
            lines = sql.split("\n")
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("select"):
                    sql = "\n".join(lines[i:])
                    break
        
        return sql.strip()
    
    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """
        Validate the generated SQL for safety
        
        Returns:
            (is_valid, error_message)
        """
        sql_upper = sql.upper()
        
        # Blocked operations
        blocked_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
            "TRUNCATE", "GRANT", "REVOKE", "ATTACH", "DETACH"
        ]
        
        for keyword in blocked_keywords:
            if keyword in sql_upper:
                return False, f"Blocked keyword detected: {keyword}"
        
        # Must be a SELECT statement
        if not sql_upper.strip().startswith("SELECT"):
            return False, "Query must start with SELECT"
        
        # Check for suspicious patterns
        suspicious_patterns = ["--", ";", "/*", "*/", "xp_", "sp_"]
        for pattern in suspicious_patterns:
            if pattern in sql:
                return False, f"Suspicious pattern detected: {pattern}"
        
        return True, ""
    
    def explain_sql(self, sql: str) -> str:
        """Generate a natural language explanation of the SQL query"""
        prompt = f"""Explain this SQL query in simple terms:
{sql}

Provide a brief explanation of what the query does.
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
    
    def suggest_columns(self, question: str, schema: str) -> list:
        """Suggest relevant columns based on the question"""
        # Extract column names from schema
        columns = []
        for line in schema.split("\n"):
            if "-" in line and "(" in line:
                col_name = line.split("-")[0].strip()
                if col_name is not None and col_name != "" and not col_name.startswith("Column"):
                    columns.append(col_name)
        
        # Simple keyword matching
        question_lower = question.lower()
        relevant_columns = []
        
        for col in columns:
            col_lower = col.lower()
            # Check if column name or part of it appears in question
            if any(word in question_lower for word in col_lower.split("_")):
                relevant_columns.append(col)
        
        return relevant_columns if relevant_columns else columns[:5]
