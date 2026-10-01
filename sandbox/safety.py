"""
Safety Validators - AST validation and SQL/Python safety checks
"""
import ast
import re
from typing import Tuple, List, Set


class SQLSafetyValidator:
    """Validates SQL queries for security and safety"""
    
    # Blocked SQL keywords and operations
    BLOCKED_KEYWORDS = {
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
        'TRUNCATE', 'GRANT', 'REVOKE', 'ATTACH', 'DETACH', 'EXECUTE',
        'CALL', 'COPY', 'EXPORT', 'IMPORT'
    }
    
    # Allowed SQL operations (whitelist approach for safety)
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING',
        'LIMIT', 'OFFSET', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'FULL', 'ON', 'AS', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
        'BETWEEN', 'LIKE', 'IS', 'NULL', 'DISTINCT', 'WITH', 'UNION',
        'ALL', 'INTERSECT', 'EXCEPT', 'CASE', 'WHEN', 'THEN', 'ELSE',
        'END', 'ASC', 'DESC', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
        'STDDEV', 'VARIANCE', 'ARRAY', 'ROW', 'STRUCT', 'MAP', 'LIST'
    }
    
    # Allowed functions for DuckDB
    ALLOWED_FUNCTIONS = {
        # Aggregate functions
        'count', 'sum', 'avg', 'mean', 'min', 'max', 'stddev', 'variance',
        'array_agg', 'string_agg', 'list', 'histogram',
        # Date/Time functions
        'date_trunc', 'extract', 'year', 'month', 'day', 'hour', 'minute', 'second',
        'current_date', 'current_time', 'current_timestamp',
        # String functions
        'lower', 'upper', 'trim', 'substring', 'replace', 'regexp_matches',
        'concat', 'length', 'strpos', 'split_part',
        # Mathematical functions
        'abs', 'round', 'floor', 'ceil', 'sqrt', 'power', 'log', 'exp',
        'sin', 'cos', 'tan', 'random',
        # Conditional functions
        'coalesce', 'nullif', 'ifnull', 'isnull',
        # Type conversion
        'cast', 'try_cast',
        # Window functions
        'row_number', 'rank', 'dense_rank', 'lag', 'lead', 'first_value', 'last_value'
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        r'--',  # SQL comments
        r';\s*\w',  # Multiple statements
        r'/\*',  # Multi-line comments
        r'\*/',  # Multi-line comments
        r'xp_',  # Extended stored procedures
        r'sp_',  # System stored procedures
        r'@@',  # Global variables
        r'\\x',  # Hex escape
        r'0x',  # Hex numbers (potentially dangerous)
    ]
    
    def __init__(self):
        self.blocked_keywords = self.BLOCKED_KEYWORDS
        self.allowed_keywords = self.ALLOWED_KEYWORDS
        self.allowed_functions = self.ALLOWED_FUNCTIONS
        self.suspicious_patterns = self.SUSPICIOUS_PATTERNS
    
    def validate(self, sql: str) -> Tuple[bool, str]:
        """
        Validate SQL query for safety
        
        Args:
            sql: SQL query to validate
        
        Returns:
            (is_valid, error_message)
        """
        sql_upper = sql.upper()
        
        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in sql_upper:
                return False, f"Blocked SQL keyword detected: {keyword}"
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"Suspicious pattern detected: {pattern}"
        
        # Must be a SELECT statement
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Query must start with SELECT"
        
        # Check for multiple statements
        if ';' in sql and not sql.rstrip().endswith(';'):
            return False, "Multiple SQL statements detected"
        
        # Check for shell command injection attempts
        shell_patterns = [r'\|\s*\w+', r'>&', r'<\s*\w+', r'\$\(']
        for pattern in shell_patterns:
            if re.search(pattern, sql):
                return False, f"Shell injection pattern detected: {pattern}"
        
        return True, ""
    
    def sanitize_query(self, sql: str) -> str:
        """Sanitize SQL query by removing dangerous elements"""
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Remove multiple statements (keep only first)
        statements = sql.split(';')
        sql = statements[0]
        
        return sql.strip()
    
    def check_query_complexity(self, sql: str) -> dict:
        """Analyze query complexity"""
        sql_upper = sql.upper()
        
        complexity = {
            "joins": sql_upper.count('JOIN'),
            "subqueries": sql_upper.count('SELECT') - 1,  # Subtract main SELECT
            "functions": sum(1 for func in self.allowed_functions if func in sql_upper),
            "where_clauses": sql_upper.count('WHERE'),
            "group_by": 1 if 'GROUP BY' in sql_upper else 0,
            "order_by": 1 if 'ORDER BY' in sql_upper else 0,
            "estimated_complexity": "simple"
        }
        
        # Estimate overall complexity
        complexity_score = (
            complexity["joins"] * 2 +
            complexity["subqueries"] * 3 +
            complexity["functions"] +
            complexity["where_clauses"] +
            complexity["group_by"] +
            complexity["order_by"]
        )
        
        if complexity_score <= 3:
            complexity["estimated_complexity"] = "simple"
        elif complexity_score <= 7:
            complexity["estimated_complexity"] = "moderate"
        else:
            complexity["estimated_complexity"] = "complex"
        
        return complexity


class PythonSafetyValidator:
    """Validates Python code using AST analysis for security"""
    
    # Blocked imports
    BLOCKED_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
        'http', 'ftplib', 'smtplib', 'telnetlib', 'pickle', 'shelve',
        'marshal', 'importlib', 'imp', 'ctypes', 'multiprocessing',
        'threading', 'signal', 'pty', 'fcntl', 'termios'
    }
    
    # Blocked built-in functions
    BLOCKED_BUILTINS = {
        'eval', 'exec', 'compile', '__import__', 'open', 'file',
        'input', 'raw_input', 'reload', 'exit', 'quit'
    }
    
    # Blocked attributes
    BLOCKED_ATTRIBUTES = {
        '__globals__', '__code__', '__closure__', '__dict__',
        '__class__', '__bases__', '__subclasses__', '__mro__',
        '__init__', '__getattribute__', '__setattr__'
    }
    
    # Allowed modules for data analysis
    ALLOWED_MODULES = {
        'pandas', 'numpy', 'math', 'datetime', 'collections',
        'itertools', 'random', 'statistics', 'fractions', 'decimal'
    }
    
    def __init__(self):
        self.blocked_imports = self.BLOCKED_IMPORTS
        self.blocked_builtins = self.BLOCKED_BUILTINS
        self.blocked_attributes = self.BLOCKED_ATTRIBUTES
        self.allowed_modules = self.ALLOWED_MODULES
    
    def validate(self, code: str) -> Tuple[bool, str]:
        """
        Validate Python code using AST analysis
        
        Args:
            code: Python code to validate
        
        Returns:
            (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        
        # Check for dangerous patterns
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if not self._check_import(node):
                    return False, f"Blocked import detected: {self._get_import_name(node)}"
            
            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.blocked_builtins:
                        return False, f"Blocked function call: {node.func.id}"
            
            # Check attribute access
            elif isinstance(node, ast.Attribute):
                if node.attr in self.blocked_attributes:
                    return False, f"Blocked attribute access: {node.attr}"
            
            # Check for dangerous operations
            # Note: ast.Exec was removed in Python 3, eval is checked via function calls
        
        # Additional text-based checks
        text_checks = self._text_based_checks(code)
        if not text_checks[0]:
            return text_checks
        
        return True, ""
    
    def _check_import(self, node) -> bool:
        """Check if import is allowed"""
        import_name = self._get_import_name(node)
        
        if not import_name:
            return True
        
        # Check base module
        base_module = import_name.split('.')[0]
        
        # Block if in blocked list
        if base_module in self.blocked_imports:
            return False
        
        # Allow if in allowed list
        if base_module in self.allowed_modules:
            return True
        
        # Block by default (whitelist approach)
        return False
    
    def _get_import_name(self, node) -> str:
        """Extract import name from AST node"""
        if isinstance(node, ast.Import):
            if node.names:
                return node.names[0].name
        elif isinstance(node, ast.ImportFrom):
            return node.module or ""
        return ""
    
    def _text_based_checks(self, code: str) -> Tuple[bool, str]:
        """Additional text-based safety checks"""
        code_lower = code.lower()
        
        # Check for file operations
        file_patterns = ['open(', 'file(', '.write(', '.read(']
        for pattern in file_patterns:
            if pattern in code_lower:
                return False, f"File operation detected: {pattern}"
        
        # Check for network operations
        network_patterns = ['socket.', 'requests.', 'urllib.', 'http.']
        for pattern in network_patterns:
            if pattern in code_lower:
                return False, f"Network operation detected: {pattern}"
        
        # Check for process operations
        process_patterns = ['subprocess.', 'os.system', 'os.popen', 'os.spawn']
        for pattern in process_patterns:
            if pattern in code_lower:
                return False, f"Process operation detected: {pattern}"
        
        # Check for shell commands
        shell_patterns = ['! ', '$(', '`', '&&', '||']
        for pattern in shell_patterns:
            if pattern in code:
                return False, f"Shell command pattern detected: {pattern}"
        
        return True, ""
    
    def sanitize_code(self, code: str) -> str:
        """Remove dangerous elements from code (basic sanitization)"""
        # This is a basic sanitization - AST validation is still required
        lines = code.split('\n')
        safe_lines = []
        
        for line in lines:
            # Skip lines with dangerous patterns
            if any(pattern in line.lower() for pattern in ['import os', 'import sys', 'import subprocess']):
                continue
            if any(pattern in line.lower() for pattern in ['eval(', 'exec(', 'compile(']):
                continue
            safe_lines.append(line)
        
        return '\n'.join(safe_lines)
    
    def check_code_complexity(self, code: str) -> dict:
        """Analyze code complexity"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"error": "Invalid syntax"}
        
        complexity = {
            "functions": len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]),
            "classes": len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]),
            "loops": len([node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]),
            "imports": len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]),
            "calls": len([node for node in ast.walk(tree) if isinstance(node, ast.Call)]),
            "estimated_complexity": "simple"
        }
        
        # Estimate overall complexity
        complexity_score = (
            complexity["functions"] * 2 +
            complexity["classes"] * 3 +
            complexity["loops"] * 2 +
            complexity["imports"] +
            complexity["calls"] // 5
        )
        
        if complexity_score <= 5:
            complexity["estimated_complexity"] = "simple"
        elif complexity_score <= 15:
            complexity["estimated_complexity"] = "moderate"
        else:
            complexity["estimated_complexity"] = "complex"
        
        return complexity


class TimeoutHandler:
    """Handles execution timeouts"""
    
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self.timed_out = False
    
    def __enter__(self):
        # Set up signal handler for Unix systems
        try:
            import signal
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.timeout_seconds)
        except (ImportError, AttributeError):
            # Windows doesn't have SIGALRM, will use threading approach
            pass
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cancel alarm
        try:
            import signal
            signal.alarm(0)
        except (ImportError, AttributeError):
            pass
        return False
    
    def _timeout_handler(self, signum, frame):
        self.timed_out = True
        raise TimeoutError(f"Execution timed out after {self.timeout_seconds} seconds")
    
    def check_timeout(self):
        """Check if timeout occurred"""
        return self.timed_out