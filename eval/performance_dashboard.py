"""
Model Performance Dashboard — Phase 7

Tracks and persists per-question agent performance metrics so the UI can
display historical trends, success rates, latency distributions, and
agent-specific statistics.

Metrics are stored as JSONL in the eval/ directory.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import json
import os
import statistics
import time
from datetime import datetime


METRICS_FILE = os.path.join("eval", "performance_metrics.jsonl")


class QuestionMetric:
    """Performance record for a single question run"""

    def __init__(
        self,
        question: str,
        agent: str,
        code_type: str,
        success: bool,
        latency_ms: float,
        retry_count: int,
        heal_attempts: int,
        validation_passed: bool,
        quality_score: float,
        cross_check_performed: bool,
        cross_check_match: Optional[bool],
        confidence: float,
        error: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        self.question = question
        self.agent = agent
        self.code_type = code_type
        self.success = success
        self.latency_ms = latency_ms
        self.retry_count = retry_count
        self.heal_attempts = heal_attempts
        self.validation_passed = validation_passed
        self.quality_score = quality_score
        self.cross_check_performed = cross_check_performed
        self.cross_check_match = cross_check_match
        self.confidence = confidence
        self.error = error
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QuestionMetric":
        return cls(**d)


class ModelPerformanceDashboard:
    """
    Collects, persists, and analyses agent performance metrics.

    Metrics are appended to a JSONL file and can be queried at any time
    for dashboarding without requiring a database.
    """

    def __init__(self, metrics_file: str = METRICS_FILE):
        self.metrics_file = metrics_file
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)

    # ------------------------------------------------------------------
    #  Recording
    # ------------------------------------------------------------------

    def record(
        self,
        workflow_state: Dict[str, Any],
        latency_ms: float,
    ) -> QuestionMetric:
        """
        Extract performance metrics from a completed workflow state and persist them.

        Args:
            workflow_state: The final AnalystState dict from the workflow
            latency_ms: Total end-to-end latency in milliseconds

        Returns:
            The QuestionMetric that was recorded
        """
        metric = QuestionMetric(
            question=workflow_state.get("question", ""),
            agent=workflow_state.get("selected_agent", "unknown"),
            code_type=workflow_state.get("code_type", ""),
            success=workflow_state.get("error") is None,
            latency_ms=round(latency_ms, 1),
            retry_count=workflow_state.get("retry_count", 0),
            heal_attempts=workflow_state.get("heal_attempts", 0),
            validation_passed=workflow_state.get("valid", False),
            quality_score=workflow_state.get("quality_score", 0.0),
            cross_check_performed=workflow_state.get("cross_check_performed", False),
            cross_check_match=workflow_state.get("cross_check_match"),
            confidence=workflow_state.get("confidence", 0.0),
            error=workflow_state.get("error"),
        )

        self._append(metric)
        return metric

    def _append(self, metric: QuestionMetric) -> None:
        """Append a single metric to the JSONL file"""
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(metric.to_dict()) + "\n")

    # ------------------------------------------------------------------
    #  Loading
    # ------------------------------------------------------------------

    def load_all(self) -> List[QuestionMetric]:
        """Load all recorded metrics from disk"""
        metrics = []
        if not os.path.exists(self.metrics_file):
            return metrics
        with open(self.metrics_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        metrics.append(QuestionMetric.from_dict(json.loads(line)))
                    except Exception:
                        pass
        return metrics

    def load_recent(self, n: int = 50) -> List[QuestionMetric]:
        """Load the most recent n metrics"""
        return self.load_all()[-n:]

    # ------------------------------------------------------------------
    #  Aggregated statistics
    # ------------------------------------------------------------------

    def summary_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all recorded runs"""
        metrics = self.load_all()
        if not metrics:
            return {"total_runs": 0}

        successes = [m for m in metrics if m.success]
        failures = [m for m in metrics if not m.success]
        latencies = [m.latency_ms for m in metrics]
        retries = [m.retry_count for m in metrics]
        quality_scores = [m.quality_score for m in metrics if m.validation_passed]

        # Per-agent breakdown
        agents = set(m.agent for m in metrics)
        agent_stats = {}
        for agent in agents:
            agent_metrics = [m for m in metrics if m.agent == agent]
            agent_successes = [m for m in agent_metrics if m.success]
            agent_stats[agent] = {
                "total": len(agent_metrics),
                "successes": len(agent_successes),
                "success_rate": round(len(agent_successes) / len(agent_metrics), 3),
                "mean_latency_ms": round(statistics.mean([m.latency_ms for m in agent_metrics]), 1),
                "mean_retries": round(statistics.mean([m.retry_count for m in agent_metrics]), 2),
            }

        # Cross-check stats
        cc_performed = [m for m in metrics if m.cross_check_performed]
        cc_passed = [m for m in cc_performed if m.cross_check_match is True]

        return {
            "total_runs": len(metrics),
            "success_count": len(successes),
            "failure_count": len(failures),
            "success_rate": round(len(successes) / len(metrics), 3),
            "success_rate_pct": round(len(successes) / len(metrics) * 100, 1),
            "mean_latency_ms": round(statistics.mean(latencies), 1),
            "median_latency_ms": round(statistics.median(latencies), 1),
            "p95_latency_ms": round(
                sorted(latencies)[int(len(latencies) * 0.95)], 1
            ) if len(latencies) >= 20 else round(max(latencies), 1),
            "mean_retries": round(statistics.mean(retries), 2),
            "zero_retry_runs": sum(1 for r in retries if r == 0),
            "mean_quality_score": round(statistics.mean(quality_scores), 3) if quality_scores else 0.0,
            "cross_check_rate": round(len(cc_performed) / len(metrics), 3) if metrics else 0,
            "cross_check_pass_rate": round(len(cc_passed) / len(cc_performed), 3) if cc_performed else 0,
            "agent_stats": agent_stats,
            "first_run": metrics[0].timestamp if metrics else None,
            "last_run": metrics[-1].timestamp if metrics else None,
        }

    def recent_trends(self, window: int = 20) -> Dict[str, Any]:
        """Compute rolling window statistics for trend analysis"""
        metrics = self.load_recent(window)
        if not metrics:
            return {}

        return {
            "window": window,
            "runs_in_window": len(metrics),
            "success_rate_recent": round(
                sum(1 for m in metrics if m.success) / len(metrics), 3
            ),
            "mean_latency_recent": round(
                statistics.mean([m.latency_ms for m in metrics]), 1
            ),
            "mean_quality_recent": round(
                statistics.mean([m.quality_score for m in metrics if m.validation_passed] or [0]),
                3
            ),
        }

    def agent_comparison(self) -> List[Dict[str, Any]]:
        """Return per-agent performance comparison table"""
        stats = self.summary_stats()
        rows = []
        for agent, s in stats.get("agent_stats", {}).items():
            rows.append({
                "agent": agent,
                "total_runs": s["total"],
                "success_rate_pct": round(s["success_rate"] * 100, 1),
                "mean_latency_ms": s["mean_latency_ms"],
                "mean_retries": s["mean_retries"],
            })
        rows.sort(key=lambda x: x["success_rate_pct"], reverse=True)
        return rows

    def latency_buckets(self) -> Dict[str, int]:
        """Return latency distribution in buckets"""
        metrics = self.load_all()
        buckets = {
            "0-500ms": 0,
            "500ms-1s": 0,
            "1s-5s": 0,
            "5s-30s": 0,
            "30s+": 0,
        }
        for m in metrics:
            if m.latency_ms < 500:
                buckets["0-500ms"] += 1
            elif m.latency_ms < 1000:
                buckets["500ms-1s"] += 1
            elif m.latency_ms < 5000:
                buckets["1s-5s"] += 1
            elif m.latency_ms < 30000:
                buckets["5s-30s"] += 1
            else:
                buckets["30s+"] += 1
        return buckets

    def retry_distribution(self) -> Dict[str, int]:
        """Return distribution of retry counts"""
        metrics = self.load_all()
        dist: Dict[str, int] = {}
        for m in metrics:
            key = str(m.retry_count)
            dist[key] = dist.get(key, 0) + 1
        return dict(sorted(dist.items()))

    def error_breakdown(self) -> List[Dict[str, Any]]:
        """Return most common error patterns"""
        metrics = self.load_all()
        error_counts: Dict[str, int] = {}
        for m in metrics:
            if m.error:
                # Extract error category from message
                category = self._categorise_error(m.error)
                error_counts[category] = error_counts.get(category, 0) + 1

        return [
            {"error_category": k, "count": v}
            for k, v in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    def _categorise_error(self, error: str) -> str:
        """Categorise an error string into a bucket"""
        e = error.lower()
        if "timeout" in e:
            return "timeout"
        if "syntax" in e or "parse" in e:
            return "syntax_error"
        if "column" in e or "not found" in e or "keyerror" in e:
            return "missing_column"
        if "blocked" in e or "security" in e:
            return "security_violation"
        if "connection" in e or "ollama" in e:
            return "llm_connection"
        return "other"

    # ------------------------------------------------------------------
    #  Export
    # ------------------------------------------------------------------

    def export_to_dataframe(self):
        """Export all metrics to a pandas DataFrame"""
        import pandas as pd
        metrics = self.load_all()
        if not metrics:
            return pd.DataFrame()
        return pd.DataFrame([m.to_dict() for m in metrics])

    def clear(self) -> None:
        """Clear all stored metrics (use with care)"""
        if os.path.exists(self.metrics_file):
            os.remove(self.metrics_file)
            print("Performance metrics cleared.")


# ------------------------------------------------------------------
#  Convenience timer context manager
# ------------------------------------------------------------------

class PerformanceTimer:
    """Context manager for measuring elapsed time"""

    def __init__(self):
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "PerformanceTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
