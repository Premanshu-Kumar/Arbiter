"""
Jev Validator Agent - Uses Jev decision engine to validate analysis results
"""
from typing import Dict, Any
from decision.jev_client import JevClient
import pandas as pd
import config


class JevValidator:
    """Validates analysis results using Jev decision engine"""
    
    def __init__(self):
        self.jev_client = JevClient()
    
    def validate_result(
        self,
        result: Any,
        error: str,
        question: str,
        plan: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Validate the analysis result
        
        Args:
            result: Analysis result (DataFrame, dict, etc.)
            error: Error message if execution failed
            question: Original user question
            plan: Analysis plan used
            retry_count: Current retry attempt
        
        Returns:
            Validation decision with reasoning
        """
        context = {
            "error": error,
            "question": question,
            "method": plan.get("method", "unknown"),
            "confidence": plan.get("confidence", 0.5),
            "retry_count": retry_count,
            "result_type": type(result).__name__ if result is not None else "None"
        }
        
        # Add result-specific context
        if result is not None and not error:
            context.update(self._analyze_result(result))
        
        # Use Jev to make validation decision
        decision_result = self.jev_client.make_decision(context, "validation")
        
        # Enhance with additional validation checks
        enhanced_validation = self._enhance_validation(
            decision_result,
            result,
            error,
            retry_count
        )
        
        return enhanced_validation
    
    def _analyze_result(self, result: Any) -> Dict[str, Any]:
        """Analyze the result to provide context for validation"""
        context = {}
        
        if isinstance(result, pd.DataFrame):
            context["result_rows"] = len(result)
            context["result_columns"] = len(result.columns)
            context["result_empty"] = len(result) == 0
            context["has_nulls"] = result.isnull().any().any()
            
            # Check for numeric columns
            numeric_cols = result.select_dtypes(include=['number']).columns
            context["has_numeric"] = len(numeric_cols) > 0
            
            # Check for all NaN values
            if context["has_numeric"]:
                context["all_nan"] = result[numeric_cols].isnull().all().all()
            
        elif isinstance(result, (dict, list)):
            context["result_type"] = "structured"
            context["result_empty"] = len(result) == 0 if isinstance(result, (dict, list)) else False
        else:
            context["result_type"] = "scalar"
            context["result_empty"] = result is None or result == ""
        
        return context
    
    def _enhance_validation(
        self,
        decision_result: Dict[str, Any],
        result: Any,
        error: str,
        retry_count: int
    ) -> Dict[str, Any]:
        """Enhance Jev decision with additional validation checks"""
        validation = {
            "decision": decision_result.get("decision", "ACCEPT"),
            "confidence": decision_result.get("confidence", 0.5),
            "reasoning": decision_result.get("reasoning", ""),
            "valid": True,
            "should_retry": False
        }
        
        # Check for execution errors
        if error:
            validation["valid"] = False
            validation["should_retry"] = retry_count < config.MAX_RETRIES
            validation["decision"] = "RETRY" if validation["should_retry"] else "REJECT"
            validation["reasoning"] = f"Execution error: {error}"
            return validation
        
        # Check for empty results
        if isinstance(result, pd.DataFrame) and len(result) == 0:
            validation["valid"] = False
            validation["should_retry"] = retry_count < config.MAX_RETRIES
            validation["decision"] = "RETRY" if validation["should_retry"] else "ACCEPT"
            validation["reasoning"] = "Empty result set - may indicate query issue"
            return validation
        
        # Check for all NaN results
        if isinstance(result, pd.DataFrame):
            numeric_cols = result.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and result[numeric_cols].isnull().all().all():
                validation["valid"] = False
                validation["should_retry"] = retry_count < config.MAX_RETRIES
                validation["decision"] = "RETRY" if validation["should_retry"] else "ACCEPT"
                validation["reasoning"] = "All numeric values are NaN - calculation may have failed"
                return validation
        
        # Check retry limits
        if retry_count >= config.MAX_RETRIES:
            validation["valid"] = True  # Accept after max retries to prevent infinite loops
            validation["should_retry"] = False
            validation["decision"] = "ACCEPT"
            validation["reasoning"] = f"Max retries ({config.MAX_RETRIES}) reached, accepting result"
            validation["confidence"] = 0.3  # Lower confidence for forced acceptance
            return validation
        
        # Map Jev decision to validation fields
        decision = validation["decision"]
        if decision == "ACCEPT":
            validation["valid"] = True
            validation["should_retry"] = False
        elif decision == "RETRY":
            validation["valid"] = False
            validation["should_retry"] = True
        elif decision == "REJECT":
            validation["valid"] = False
            validation["should_retry"] = False
        elif decision == "SWITCH_METHOD":
            validation["valid"] = False
            validation["should_retry"] = True
            validation["reasoning"] += " - Consider switching analysis method"
        
        return validation
    
    def check_result_quality(self, result: Any) -> Dict[str, Any]:
        """
        Perform detailed quality checks on the result
        
        Returns:
            Quality assessment with specific issues found
        """
        quality_report = {
            "issues": [],
            "warnings": [],
            "score": 1.0
        }
        
        if isinstance(result, pd.DataFrame):
            # Check for empty results
            if len(result) == 0:
                quality_report["issues"].append("Empty result set")
                quality_report["score"] -= 0.5
            
            # Check for excessive nulls
            null_percentage = (result.isnull().sum().sum() / (len(result) * len(result.columns))) * 100
            if null_percentage > 50:
                quality_report["issues"].append(f"High null percentage: {null_percentage:.1f}%")
                quality_report["score"] -= 0.3
            elif null_percentage > 20:
                quality_report["warnings"].append(f"Moderate null percentage: {null_percentage:.1f}%")
                quality_report["score"] -= 0.1
            
            # Check for duplicate rows
            duplicate_count = result.duplicated().sum()
            if duplicate_count > len(result) * 0.5:
                quality_report["warnings"].append(f"High duplicate count: {duplicate_count}")
                quality_report["score"] -= 0.1
            
            # Check for reasonable row count
            if len(result) > 10000:
                quality_report["warnings"].append("Large result set may affect performance")
                quality_report["score"] -= 0.05
        
        elif result is None:
            quality_report["issues"].append("No result returned")
            quality_report["score"] = 0.0
        
        # Ensure score doesn't go below 0
        quality_report["score"] = max(0.0, quality_report["score"])
        
        return quality_report
    
    def suggest_fixes(self, error: str, code: str, code_type: str) -> list:
        """Suggest potential fixes for common errors"""
        suggestions = []
        
        error_lower = error.lower()
        
        # SQL-specific fixes
        if code_type == "sql":
            if "column" in error_lower and "does not exist" in error_lower:
                suggestions.append("Check column names in the schema")
                suggestions.append("Verify table name is 'data'")
            elif "syntax" in error_lower:
                suggestions.append("Check for missing commas or quotes")
                suggestions.append("Verify parentheses are balanced")
            elif "aggregate" in error_lower:
                suggestions.append("Ensure all non-aggregated columns are in GROUP BY")
        
        # Python-specific fixes
        elif code_type == "python":
            if "name" in error_lower and "not defined" in error_lower:
                suggestions.append("Ensure DataFrame is named 'df'")
                suggestions.append("Check variable names are spelled correctly")
            elif "key" in error_lower and "not found" in error_lower:
                suggestions.append("Verify column names match the schema")
                suggestions.append("Check for case sensitivity in column names")
            elif "syntax" in error_lower:
                suggestions.append("Check for missing colons or indentation")
        
        # General fixes
        if "timeout" in error_lower:
            suggestions.append("Consider adding LIMIT clause to reduce result size")
            suggestions.append("Optimize query with better filtering")
        
        if "memory" in error_lower:
            suggestions.append("Reduce dataset size with filtering")
            suggestions.append("Use aggregations instead of raw data")
        
        return suggestions if suggestions else ["Review the error message and code logic"]
