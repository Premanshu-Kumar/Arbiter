"""
Shared state definition for LangGraph multi-agent system
"""
from typing import TypedDict, Any, Optional
import pandas as pd


class AnalystState(TypedDict):
    """Shared state for the multi-agent data analyst workflow"""
    
    # Input
    question: str
    file_path: str
    
    # Data profiling
    schema: str
    row_count: int
    column_count: int
    missing_values: dict
    data_types: dict
    
    # DataFrame for execution
    df: Optional[pd.DataFrame]
    
    # Jev decisions
    decision: dict
    confidence: float
    
    # Agent execution
    selected_agent: str
    code: str
    code_type: str
    
    # Results
    result: Any
    error: Optional[str]
    
    # Validation (Phase 5 — enhanced)
    valid: bool
    validation_reason: str
    validation_issues: list          # Critical issues found during validation
    validation_warnings: list        # Non-critical warnings
    quality_score: float             # 0.0–1.0 result quality score
    validation_checks: dict          # Detailed check results (NaN %, outliers, etc.)
    
    # Cross-validation (Phase 5)
    cross_check_performed: bool
    cross_check_match: Optional[bool]
    cross_check_confidence: float
    cross_check_discrepancies: list
    
    # Retry / Self-healing (Phase 5 — enhanced)
    retry_count: int
    failed_agent: Optional[str]
    heal_attempts: int               # Number of code-fix attempts in current cycle
    last_error_category: Optional[str]  # fatal / syntax / data / runtime / timeout / switch
    suggested_fixes: list            # Fix suggestions from the validator
    
    # Output
    charts: list[str]
    insights: list[str]
    report: str

    # Phase 7 — Advanced
    # Multi-file joins
    datasets: dict                   # name -> registered dataset names
    joined_schema: Optional[str]     # Schema of the joined result (if any)

    # Automatic EDA
    eda_report: Optional[dict]       # Full EDA report dict

    # Dataset versioning
    dataset_version_id: Optional[str]  # Version ID of the active dataset

    # Performance tracking
    latency_ms: float                # End-to-end latency for this run
