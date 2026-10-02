"""
Jev Validator Agent - Uses Jev decision engine to validate analysis results.

Phase 5 implementation: comprehensive result validation including
empty-result detection, NaN detection, outlier detection, type checking,
cross-validation orchestration, and self-healing retry integration.
"""
from typing import Dict, Any, List, Optional
from decision.jev_client import JevClient
from decision.validation_policies import (
    ValidationThresholds,
    RetryPolicy,
    ValidationResult,
    ValidationPolicyEngine,
)
import pandas as pd
import numpy as np
import config


class JevValidator:
    """Validates analysis results using Jev decision engine and structured policies."""
    
    def __init__(
        self,
        thresholds: ValidationThresholds = None,
        retry_policy: RetryPolicy = None,
    ):
        self.jev_client = JevClient()
        self.policy = ValidationPolicyEngine(thresholds, retry_policy)
        self.thresholds = self.policy.thresholds
    
    # ------------------------------------------------------------------
    #  Primary validation entry point
    # ------------------------------------------------------------------
    
    def validate_result(
        self,
        result: Any,
        error: str,
        question: str,
        plan: Dict[str, Any],
        retry_count: int = 0,
        code: str = "",
        code_type: str = "",
        failed_agent: str = None,
    ) -> Dict[str, Any]:
        """Validate the analysis result with comprehensive checks.
        
        Args:
            result: Analysis result (DataFrame, dict, list, scalar, etc.)
            error: Error message if execution failed
            question: Original user question
            plan: Analysis plan used
            retry_count: Current retry attempt
            code: The code that produced the result
            code_type: "sql" or "python"
            failed_agent: Which agent failed (for retry routing)
        
        Returns:
            Validation decision dict with: valid, should_retry, decision,
            confidence, reasoning, issues, warnings, quality_score,
            suggested_action, error_category
        """
        # ----------------------------------------------------------
        # 1. Handle execution errors
        # ----------------------------------------------------------
        if error is not None:
            return self._handle_error(
                error, retry_count, code, code_type, failed_agent
            )
        
        # ----------------------------------------------------------
        # 2. Run structural checks on the result
        # ----------------------------------------------------------
        quality = self.check_result_quality(result)
        
        # ----------------------------------------------------------
        # 3. Build Jev context and get decision
        # ----------------------------------------------------------
        context = {
            "error": error,
            "question": question,
            "method": plan.get("method", "unknown"),
            "confidence": plan.get("confidence", 0.5),
            "retry_count": retry_count,
            "result_type": type(result).__name__ if result is not None else "None",
            **self._analyze_result(result),
        }
        
        jev_decision = self.jev_client.make_decision(context, "validation")
        
        # ----------------------------------------------------------
        # 4. Merge Jev decision with quality checks
        # ----------------------------------------------------------
        return self._merge_validation(
            jev_decision, quality, result, retry_count
        )
    
    # ------------------------------------------------------------------
    #  Error handling
    # ------------------------------------------------------------------
    
    def _handle_error(
        self,
        error: str,
        retry_count: int,
        code: str,
        code_type: str,
        failed_agent: str,
    ) -> Dict[str, Any]:
        """Handle execution errors and determine retry strategy."""
        eligibility = self.policy.is_retry_eligible(error, retry_count, failed_agent)
        category = self.policy.classify_error(error)
        
        suggestions = self.suggest_fixes(error, code, code_type)
        
        result = ValidationResult(
            decision=eligibility["action"],
            valid=False,
            should_retry=eligibility["eligible"],
            confidence=0.2 if category == "fatal" else 0.5,
            reasoning=eligibility["reasoning"],
            issues=[f"Execution error: {error}"],
            warnings=[],
            quality_score=0.0,
            suggested_action=eligibility["action"],
            error_category=category,
        )
        
        d = result.to_dict()
        d["suggestions"] = suggestions
        return d
    
    # ------------------------------------------------------------------
    #  Result quality checks (comprehensive Phase 5)
    # ------------------------------------------------------------------
    
    def check_result_quality(self, result: Any) -> Dict[str, Any]:
        """Perform detailed quality checks on the result.
        
        Checks:
            - Empty result detection
            - NaN detection (per-column and overall)
            - Duplicate detection
            - Outlier detection (IQR-based)
            - Type consistency
            - Suspicious single-value results
        
        Returns:
            Quality assessment with issues, warnings, and score.
        """
        report: Dict[str, Any] = {
            "issues": [],
            "warnings": [],
            "score": 1.0,
            "checks": {},
        }
        
        if result is None:
            report["issues"].append("No result returned")
            report["score"] = 0.0
            report["checks"]["null_result"] = True
            return report
        
        if isinstance(result, pd.DataFrame):
            self._check_empty(result, report)
            self._check_nan(result, report)
            self._check_duplicates(result, report)
            self._check_outliers(result, report)
            self._check_single_value(result, report)
            self._check_type_consistency(result, report)
        elif isinstance(result, (dict, list)):
            if len(result) == 0:
                report["issues"].append("Empty structured result")
                report["score"] -= 0.4
                report["checks"]["empty"] = True
        elif isinstance(result, str):
            if not result.strip():
                report["issues"].append("Empty string result")
                report["score"] -= 0.4
                report["checks"]["empty_string"] = True
        
        report["score"] = max(0.0, report["score"])
        return report
    
    # ------ Individual checks ------
    
    def _check_empty(self, df: pd.DataFrame, report: Dict) -> None:
        """Detect empty result sets."""
        report["checks"]["empty"] = df.empty
        report["checks"]["row_count"] = len(df)
        report["checks"]["column_count"] = len(df.columns)
        
        if df.empty:
            report["issues"].append("Empty result set — query returned zero rows")
            report["score"] -= 0.5
        elif len(df) > self.thresholds.max_rows:
            report["warnings"].append(
                f"Very large result ({len(df)} rows) — may impact performance"
            )
            report["score"] -= 0.05
    
    def _check_nan(self, df: pd.DataFrame, report: Dict) -> None:
        """Detect NaN values at overall and per-column levels."""
        if df.empty:
            return
        
        total_cells = len(df) * len(df.columns)
        if total_cells == 0:
            return
        
        total_nans = int(df.isnull().sum().sum())
        nan_pct = (total_nans / total_cells) * 100
        report["checks"]["overall_nan_pct"] = round(nan_pct, 2)
        
        if nan_pct > self.thresholds.max_nan_percentage:
            report["issues"].append(
                f"High NaN percentage: {nan_pct:.1f}% of all cells are NaN"
            )
            report["score"] -= 0.3
        elif nan_pct > 20:
            report["warnings"].append(
                f"Moderate NaN percentage: {nan_pct:.1f}%"
            )
            report["score"] -= 0.1
        
        # Per-column NaN check
        all_nan_cols: List[str] = []
        high_nan_cols: List[str] = []
        
        for col in df.columns:
            col_nan_pct = (df[col].isnull().sum() / len(df)) * 100
            if col_nan_pct >= 100.0:
                all_nan_cols.append(col)
            elif col_nan_pct > self.thresholds.max_column_nan_percentage:
                high_nan_cols.append(f"{col} ({col_nan_pct:.1f}%)")
        
        report["checks"]["all_nan_columns"] = all_nan_cols
        report["checks"]["high_nan_columns"] = high_nan_cols
        
        if all_nan_cols:
            report["issues"].append(
                f"Columns entirely NaN: {', '.join(all_nan_cols)}"
            )
            report["score"] -= 0.2 * len(all_nan_cols)
        
        if high_nan_cols:
            report["warnings"].append(
                f"High NaN columns: {', '.join(high_nan_cols)}"
            )
            report["score"] -= 0.05 * len(high_nan_cols)
        
        # Check if all numeric columns are entirely NaN
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            all_numeric_nan = df[numeric_cols].isnull().all()
            if isinstance(all_numeric_nan, pd.Series):
                all_numeric_nan = all_numeric_nan.all()
            
            report["checks"]["all_numeric_nan"] = bool(all_numeric_nan)
            if all_numeric_nan:
                report["issues"].append(
                    "All numeric columns are entirely NaN — calculation likely failed"
                )
                report["score"] -= 0.4
    
    def _check_duplicates(self, df: pd.DataFrame, report: Dict) -> None:
        """Detect excessive duplicate rows."""
        if df.empty or len(df) < 2:
            return
        
        dup_count = int(df.duplicated().sum())
        dup_pct = (dup_count / len(df)) * 100
        report["checks"]["duplicate_count"] = dup_count
        report["checks"]["duplicate_pct"] = round(dup_pct, 2)
        
        if dup_pct > self.thresholds.max_duplicate_percentage:
            report["issues"].append(
                f"Excessive duplicates: {dup_count} rows ({dup_pct:.1f}%) are duplicates"
            )
            report["score"] -= 0.2
        elif dup_pct > 50:
            report["warnings"].append(
                f"High duplicate count: {dup_count} rows ({dup_pct:.1f}%)"
            )
            report["score"] -= 0.1
    
    def _check_outliers(self, df: pd.DataFrame, report: Dict) -> None:
        """IQR-based outlier detection on numeric columns."""
        if df.empty:
            return
        
        numeric_cols = df.select_dtypes(include=["number"]).columns
        outlier_info: Dict[str, Dict] = {}
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue
            
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            
            if iqr == 0:
                continue
            
            lower = q1 - self.thresholds.iqr_multiplier * iqr
            upper = q3 + self.thresholds.iqr_multiplier * iqr
            
            outlier_mask = (series < lower) | (series > upper)
            n_outliers = int(outlier_mask.sum())
            outlier_pct = (n_outliers / len(series)) * 100
            
            if outlier_pct > self.thresholds.max_outlier_percentage:
                outlier_info[col] = {
                    "count": n_outliers,
                    "percentage": round(outlier_pct, 2),
                    "lower_bound": round(lower, 4),
                    "upper_bound": round(upper, 4),
                }
        
        report["checks"]["outliers"] = outlier_info
        
        if outlier_info:
            col_summary = ", ".join(
                f"{c} ({v['percentage']:.1f}%)" for c, v in outlier_info.items()
            )
            report["warnings"].append(f"Columns with high outliers: {col_summary}")
            report["score"] -= 0.05 * len(outlier_info)
    
    def _check_single_value(self, df: pd.DataFrame, report: Dict) -> None:
        """Detect columns where every row has the same value (suspicious)."""
        if df.empty or len(df) < 2:
            return
        
        single_value_cols = [
            col for col in df.columns if df[col].nunique(dropna=True) <= 1
        ]
        
        report["checks"]["single_value_columns"] = single_value_cols
        
        if single_value_cols and len(single_value_cols) == len(df.columns):
            report["issues"].append(
                "All columns have a single unique value — result may be incorrect"
            )
            report["score"] -= 0.3
        elif single_value_cols:
            report["warnings"].append(
                f"Single-value columns: {', '.join(single_value_cols)}"
            )
    
    def _check_type_consistency(self, df: pd.DataFrame, report: Dict) -> None:
        """Check for mixed types within object columns."""
        if df.empty:
            return
        
        mixed_type_cols = []
        for col in df.select_dtypes(include=["object"]).columns:
            types = df[col].dropna().map(type).nunique()
            if types > 1:
                mixed_type_cols.append(col)
        
        report["checks"]["mixed_type_columns"] = mixed_type_cols
        
        if mixed_type_cols:
            report["warnings"].append(
                f"Mixed-type columns: {', '.join(mixed_type_cols)}"
            )
            report["score"] -= 0.05 * len(mixed_type_cols)
    
    # ------------------------------------------------------------------
    #  Merge Jev decision with quality checks
    # ------------------------------------------------------------------
    
    def _merge_validation(
        self,
        jev_decision: Dict[str, Any],
        quality: Dict[str, Any],
        result: Any,
        retry_count: int,
    ) -> Dict[str, Any]:
        """Combine Jev's decision with structural quality checks."""
        issues = quality.get("issues", [])
        warnings = quality.get("warnings", [])
        quality_score = quality.get("score", 1.0)
        
        # Start from Jev's decision
        decision = jev_decision.get("decision", "ACCEPT")
        confidence = jev_decision.get("confidence", 0.5)
        reasoning = jev_decision.get("reasoning", "")
        
        # Override if quality checks found critical issues
        has_critical = len(issues) > 0
        
        if has_critical and decision == "ACCEPT":
            if quality_score <= 0.3:
                decision = "RETRY"
                reasoning = f"Quality issues override acceptance: {'; '.join(issues)}"
                confidence = max(0.3, confidence - 0.3)
            elif quality_score <= 0.6:
                # Accept with warnings
                reasoning += f" | Quality warnings: {'; '.join(issues)}"
                confidence = max(0.4, confidence - 0.1)
        
        # Determine validity and retry
        if decision == "ACCEPT":
            valid = True
            should_retry = False
        elif decision == "RETRY" or decision == "RETRY_WITH_FIX":
            valid = False
            should_retry = retry_count < config.MAX_RETRIES
            if not should_retry:
                decision = "ACCEPT"  # Forced accept after max retries
                valid = True
                confidence = min(confidence, 0.3)
                reasoning = f"Max retries ({config.MAX_RETRIES}) reached — force-accepting"
        elif decision == "SWITCH_METHOD":
            valid = False
            should_retry = retry_count < config.MAX_RETRIES
        elif decision == "REJECT":
            valid = False
            should_retry = False
        else:
            valid = True
            should_retry = False
        
        return {
            "decision": decision,
            "valid": valid,
            "should_retry": should_retry,
            "confidence": confidence,
            "reasoning": reasoning,
            "issues": issues,
            "warnings": warnings,
            "quality_score": quality_score,
            "suggested_action": decision,
            "error_category": None,
            "checks": quality.get("checks", {}),
        }
    
    # ------------------------------------------------------------------
    #  Result analysis (context for Jev)
    # ------------------------------------------------------------------
    
    def _analyze_result(self, result: Any) -> Dict[str, Any]:
        """Analyze the result to provide context for Jev validation."""
        context: Dict[str, Any] = {}
        
        if isinstance(result, pd.DataFrame):
            context["result_rows"] = len(result)
            context["result_columns"] = len(result.columns)
            context["result_empty"] = result.empty
            
            has_nulls_series = result.isnull().any()
            context["has_nulls"] = bool(
                has_nulls_series.any()
                if isinstance(has_nulls_series, pd.Series)
                else has_nulls_series
            )
            
            numeric_cols = result.select_dtypes(include=["number"]).columns
            context["has_numeric"] = len(numeric_cols) > 0
            
            if context["has_numeric"]:
                all_nan_series = result[numeric_cols].isnull().all()
                context["all_nan"] = bool(
                    all_nan_series.all()
                    if isinstance(all_nan_series, pd.Series)
                    else all_nan_series
                )
        elif isinstance(result, (dict, list)):
            context["result_type"] = "structured"
            context["result_empty"] = len(result) == 0
        else:
            context["result_type"] = "scalar"
            context["result_empty"] = result is None or result == ""
        
        return context
    
    # ------------------------------------------------------------------
    #  Fix suggestions
    # ------------------------------------------------------------------
    
    def suggest_fixes(self, error: str, code: str, code_type: str) -> List[str]:
        """Suggest potential fixes for common errors."""
        suggestions: List[str] = []
        error_lower = error.lower()
        
        if code_type == "sql":
            if "column" in error_lower and "does not exist" in error_lower:
                suggestions.append("Check column names in the schema")
                suggestions.append("Verify table name is 'data'")
                suggestions.append("Column names may be case-sensitive")
            elif "syntax" in error_lower:
                suggestions.append("Check for missing commas or quotes")
                suggestions.append("Verify parentheses are balanced")
            elif "aggregate" in error_lower or "group by" in error_lower:
                suggestions.append("Ensure all non-aggregated columns are in GROUP BY")
            elif "table" in error_lower and "not found" in error_lower:
                suggestions.append("Ensure FROM clause references 'data'")
            elif "type" in error_lower:
                suggestions.append("Use CAST() for type conversion")
                suggestions.append("Check date/numeric column formats")
        
        elif code_type == "python":
            if "name" in error_lower and "not defined" in error_lower:
                suggestions.append("Ensure DataFrame is named 'df'")
                suggestions.append("Check variable names are spelled correctly")
            elif "key" in error_lower or "keyerror" in error_lower:
                suggestions.append("Verify column names match the schema")
                suggestions.append("Check for case sensitivity in column names")
            elif "syntax" in error_lower:
                suggestions.append("Check for missing colons or indentation")
            elif "type" in error_lower:
                suggestions.append("Use .astype() for type conversion")
                suggestions.append("Use pd.to_numeric() or pd.to_datetime()")
        
        if "timeout" in error_lower:
            suggestions.append("Add LIMIT clause or .head() to reduce result size")
            suggestions.append("Optimize with better filtering before aggregation")
        
        if "memory" in error_lower:
            suggestions.append("Reduce dataset size with filtering")
            suggestions.append("Use aggregations instead of raw data")
        
        return suggestions if suggestions else ["Review the error message and code logic"]
