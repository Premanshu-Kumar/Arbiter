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
        schema_str = str(schema).lower() if schema is not None else ""
        
        # Extract column names from schema
        columns = []
        for line in schema.split("\n"):
            if "-" in line and "(" in line:
                col_name = line.split("-")[0].strip()
                if col_name is not None and col_name != "" and not col_name.startswith("Column"):
                    columns.append(col_name)
        
        # Detect mentioned columns in question
        mentioned_columns = [col for col in columns if col.lower() in question_lower]
        
        # Separate categorical and numeric columns based on schema
        cat_cols = []
        num_cols = []
        for col in columns:
            if col.lower() in schema_str:
                col_line = [line for line in schema.split("\n") if col in line][0]
                if any(dtype in col_line.lower() for dtype in ['int', 'float', 'double', 'numeric']):
                    num_cols.append(col)
                else:
                    cat_cols.append(col)
        
        # Handle grouping/aggregation queries
        if any(word in question_lower for word in ['by', 'per', 'for each', 'group']):
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                group_col = cat_cols[0]
                agg_col = num_cols[0]
                
                if 'average' in question_lower or 'mean' in question_lower:
                    return {
                        "code": f"SELECT {group_col}, AVG({agg_col}) as avg_{agg_col} FROM data GROUP BY {group_col}",
                        "code_type": "sql",
                        "method": "SQL",
                        "success": True,
                        "reasoning": f"Generated SQL for average {agg_col} by {group_col}"
                    }
                elif 'sum' in question_lower or 'total' in question_lower:
                    return {
                        "code": f"SELECT {group_col}, SUM({agg_col}) as total_{agg_col} FROM data GROUP BY {group_col}",
                        "code_type": "sql",
                        "method": "SQL",
                        "success": True,
                        "reasoning": f"Generated SQL for sum {agg_col} by {group_col}"
                    }
                elif 'count' in question_lower:
                    return {
                        "code": f"SELECT {group_col}, COUNT(*) as count FROM data GROUP BY {group_col}",
                        "code_type": "sql",
                        "method": "SQL",
                        "success": True,
                        "reasoning": f"Generated SQL for count by {group_col}"
                    }
            elif len(cat_cols) >= 1:
                group_col = cat_cols[0]
                return {
                    "code": f"SELECT {group_col}, COUNT(*) as count FROM data GROUP BY {group_col}",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for count by {group_col}"
                }
        
        # Handle specific column-based queries
        if "average" in question_lower or "mean" in question_lower:
            if mentioned_columns:
                numeric_mentioned = [col for col in mentioned_columns if col in num_cols]
                if numeric_mentioned:
                    if len(numeric_mentioned) >= 2 and len(cat_cols) >= 1:
                        # Try to detect grouping pattern
                        for col in mentioned_columns:
                            if col in cat_cols:
                                group_col = col
                                agg_col = [c for c in numeric_mentioned if c != group_col][0]
                                return {
                                    "code": f"SELECT {group_col}, AVG({agg_col}) as avg_{agg_col} FROM data GROUP BY {group_col}",
                                    "code_type": "sql",
                                    "method": "SQL",
                                    "success": True,
                                    "reasoning": f"Generated SQL for average {agg_col} by {group_col}"
                                }
                    return {
                        "code": f"SELECT AVG({', '.join(numeric_mentioned)}) as avg_value FROM data",
                        "code_type": "sql",
                        "method": "SQL",
                        "success": True,
                        "reasoning": f"Generated SQL for average of {', '.join(numeric_mentioned)}"
                    }
            if num_cols:
                return {
                    "code": f"SELECT AVG({num_cols[0]}) as avg_value FROM data",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for average of {num_cols[0]}"
                }
        elif "sum" in question_lower or "total" in question_lower:
            if mentioned_columns:
                numeric_mentioned = [col for col in mentioned_columns if col in num_cols]
                if numeric_mentioned:
                    if len(numeric_mentioned) >= 2 and len(cat_cols) >= 1:
                        for col in mentioned_columns:
                            if col in cat_cols:
                                group_col = col
                                agg_col = [c for c in numeric_mentioned if c != group_col][0]
                                return {
                                    "code": f"SELECT {group_col}, SUM({agg_col}) as total_{agg_col} FROM data GROUP BY {group_col}",
                                    "code_type": "sql",
                                    "method": "SQL",
                                    "success": True,
                                    "reasoning": f"Generated SQL for sum {agg_col} by {group_col}"
                                }
                    return {
                        "code": f"SELECT SUM({', '.join(numeric_mentioned)}) as total_value FROM data",
                        "code_type": "sql",
                        "method": "SQL",
                        "success": True,
                        "reasoning": f"Generated SQL for sum of {', '.join(numeric_mentioned)}"
                    }
            if num_cols:
                return {
                    "code": f"SELECT SUM({num_cols[0]}) as total_value FROM data",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for sum of {num_cols[0]}"
                }
        elif "count" in question_lower:
            if mentioned_columns:
                if len(mentioned_columns) >= 2:
                    # Try to detect grouping pattern
                    for col in mentioned_columns:
                        if col in cat_cols:
                            group_col = col
                            other_col = [c for c in mentioned_columns if c != group_col][0]
                            return {
                                "code": f"SELECT {group_col}, COUNT({other_col}) as count FROM data GROUP BY {group_col}",
                                "code_type": "sql",
                                "method": "SQL",
                                "success": True,
                                "reasoning": f"Generated SQL for count {other_col} by {group_col}"
                            }
                return {
                    "code": f"SELECT {mentioned_columns[0]}, COUNT(*) as count FROM data GROUP BY {mentioned_columns[0]}",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for count by {mentioned_columns[0]}"
                }
            if cat_cols:
                return {
                    "code": f"SELECT {cat_cols[0]}, COUNT(*) as count FROM data GROUP BY {cat_cols[0]}",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for count by {cat_cols[0]}"
                }
        elif "top" in question_lower:
            if num_cols:
                return {
                    "code": f"SELECT * FROM data ORDER BY {num_cols[0]} DESC LIMIT 10",
                    "code_type": "sql",
                    "method": "SQL",
                    "success": True,
                    "reasoning": f"Generated SQL for top values by {num_cols[0]}"
                }
        else:
            # Default SELECT
            return {
                "code": "SELECT * FROM data LIMIT 10",
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
10. Limit results to 1000 rows for performance

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
