"""
Validation Policies - Structured rules for Jev-powered result validation

Defines configurable policies that the JevValidator uses to decide whether
an analysis result should be ACCEPTED, RETRIED, or REJECTED.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import config


@dataclass
class ValidationThresholds:
    """Configurable thresholds for result validation"""
    
    # Empty-result detection
    min_rows: int = 0                      # 0 means empty results are flagged
    max_rows: int = 100_000                # Upper bound before warning
    
    # NaN detection
    max_nan_percentage: float = 50.0       # Entire result
    max_column_nan_percentage: float = 80.0  # Single column
    max_all_nan_columns: int = 0           # Columns that are entirely NaN
    
    # Duplicate detection
    max_duplicate_percentage: float = 90.0
    
    # Outlier detection (IQR-based)
    iqr_multiplier: float = 3.0
    max_outlier_percentage: float = 25.0
    
    # Cross-check tolerance
    cross_check_tolerance: float = 0.01    # 1% relative tolerance for numeric comparison
    cross_check_row_tolerance: int = 0     # Exact row count match by default
    
    # Confidence thresholds
    high_confidence: float = 0.8
    medium_confidence: float = 0.5
    low_confidence: float = 0.3


@dataclass
class RetryPolicy:
    """Policy governing self-healing retry behaviour"""
    
    max_retries: int = field(default_factory=lambda: config.MAX_RETRIES)
    
    # Whether to try method switching (SQL→Python or Python→SQL)
    allow_method_switch: bool = True
    
    # After how many same-method failures do we switch
    switch_after_failures: int = 2
    
    # Whether to attempt LLM-based code correction before full retry
    attempt_code_fix: bool = True
    
    # Maximum code-fix attempts per retry cycle
    max_fix_attempts: int = 2
    
    # Errors that should never be retried (fatal)
    fatal_error_patterns: List[str] = field(default_factory=lambda: [
        "blocked sql keyword",
        "blocked import",
        "blocked function call",
        "blocked attribute access",
        "file operation detected",
        "network operation detected",
        "process operation detected",
        "shell injection",
    ])
    
    # Errors that suggest switching method rather than retrying
    switch_method_patterns: List[str] = field(default_factory=lambda: [
        "not supported by duckdb",
        "cannot be cast",
        "type mismatch",
        "unable to parse",
        "unsupported function",
    ])


@dataclass
class ValidationResult:
    """Structured result of a validation check"""
    
    decision: str           # ACCEPT, RETRY, REJECT, SWITCH_METHOD
    valid: bool
    should_retry: bool
    confidence: float
    reasoning: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_score: float = 1.0
    suggested_action: Optional[str] = None
    error_category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "valid": self.valid,
            "should_retry": self.should_retry,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "issues": self.issues,
            "warnings": self.warnings,
            "quality_score": self.quality_score,
            "suggested_action": self.suggested_action,
            "error_category": self.error_category,
        }


class ValidationPolicyEngine:
    """Applies validation policies to determine result acceptance"""
    
    def __init__(
        self,
        thresholds: ValidationThresholds = None,
        retry_policy: RetryPolicy = None,
    ):
        self.thresholds = thresholds or ValidationThresholds()
        self.retry_policy = retry_policy or RetryPolicy()
    
    # ------------------------------------------------------------------
    #  Error classification
    # ------------------------------------------------------------------
    
    def classify_error(self, error: str) -> str:
        """Classify an error message into a category for routing decisions.
        
        Categories:
            fatal       — security violation, never retry
            switch      — error suggests the other method would work better
            syntax      — code syntax / generation error, retry with fix
            runtime     — runtime failure, retry or switch
            timeout     — execution took too long
            data        — data-related issue (missing column, type cast)
            unknown     — fallback
        """
        if not error:
            return "none"
        
        error_lower = error.lower()
        
        for pattern in self.retry_policy.fatal_error_patterns:
            if pattern in error_lower:
                return "fatal"
        
        for pattern in self.retry_policy.switch_method_patterns:
            if pattern in error_lower:
                return "switch"
        
        if any(kw in error_lower for kw in ["syntax error", "syntaxerror", "parse error"]):
            return "syntax"
        
        if any(kw in error_lower for kw in ["timeout", "timed out"]):
            return "timeout"
        
        if any(kw in error_lower for kw in [
            "column", "does not exist", "not found", "keyerror",
            "no such column", "invalid column"
        ]):
            return "data"
        
        if any(kw in error_lower for kw in [
            "execution error", "runtime", "exception", "error"
        ]):
            return "runtime"
        
        return "unknown"
    
    # ------------------------------------------------------------------
    #  Retry eligibility
    # ------------------------------------------------------------------
    
    def is_retry_eligible(
        self,
        error: str,
        retry_count: int,
        failed_agent: str = None,
    ) -> Dict[str, Any]:
        """Determine if a failed execution should be retried.
        
        Returns:
            dict with keys: eligible (bool), action (str), reasoning (str)
        """
        category = self.classify_error(error)
        
        # Fatal errors are never retried
        if category == "fatal":
            return {
                "eligible": False,
                "action": "REJECT",
                "reasoning": f"Fatal error — security violation: {error}",
            }
        
        # Exceeded max retries
        if retry_count >= self.retry_policy.max_retries:
            return {
                "eligible": False,
                "action": "ACCEPT_DEGRADED",
                "reasoning": f"Max retries ({self.retry_policy.max_retries}) exhausted",
            }
        
        # Suggest method switch if pattern matches or repeated failures
        if category == "switch" or (
            retry_count >= self.retry_policy.switch_after_failures
            and self.retry_policy.allow_method_switch
        ):
            target = "Python" if failed_agent == "SQL" else "SQL"
            return {
                "eligible": True,
                "action": "SWITCH_METHOD",
                "reasoning": f"Switching to {target} after {retry_count} failures",
            }
        
        # Code-fixable errors
        if category in ("syntax", "data", "runtime", "unknown"):
            return {
                "eligible": True,
                "action": "RETRY_WITH_FIX" if self.retry_policy.attempt_code_fix else "RETRY",
                "reasoning": f"Retryable {category} error (attempt {retry_count + 1})",
            }
        
        # Timeout — retry with a simpler approach
        if category == "timeout":
            return {
                "eligible": True,
                "action": "RETRY_SIMPLIFIED",
                "reasoning": "Execution timed out — will simplify the query",
            }
        
        return {
            "eligible": True,
            "action": "RETRY",
            "reasoning": "Default retry",
        }
    
    # ------------------------------------------------------------------
    #  Cross-check policy
    # ------------------------------------------------------------------
    
    def should_cross_check(self, plan: Dict[str, Any], confidence: float) -> bool:
        """Decide whether a cross-check (SQL↔Pandas) is warranted.
        
        Cross-checks are triggered when:
        - The plan explicitly asks for "BOTH"
        - Confidence is below medium threshold
        - The question involves aggregation (common source of mismatches)
        """
        if plan.get("method", "").upper() == "BOTH":
            return True
        
        if confidence < self.thresholds.medium_confidence:
            return True
        
        if plan.get("requires_aggregation", False) and confidence < self.thresholds.high_confidence:
            return True
        
        return False
