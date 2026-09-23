"""
Shared state definition for LangGraph multi-agent system
"""
from typing import TypedDict, Any, Optional


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
    
    # Validation
    valid: bool
    validation_reason: str
    
    # Retry
    retry_count: int
    failed_agent: Optional[str]
    
    # Output
    charts: list[str]
    insights: list[str]
    report: str
