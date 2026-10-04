"""
Jev vs LLM Benchmarking — Phase 7

Runs structured benchmarks comparing Jev-powered rule-based decisions against
LLM-powered decisions across routing accuracy, latency, and consistency.

Saves benchmark runs as JSONL files in the eval/ directory.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Callable
import time
import json
import os
import statistics
from datetime import datetime


BENCHMARK_DIR = os.path.join("eval", "benchmarks")


class BenchmarkCase:
    """A single benchmark test case"""

    def __init__(
        self,
        case_id: str,
        question: str,
        schema: str,
        expected_method: str,
        expected_visualization: str = "",
        description: str = "",
    ):
        self.case_id = case_id
        self.question = question
        self.schema = schema
        self.expected_method = expected_method.upper()
        self.expected_visualization = expected_visualization
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class BenchmarkResult:
    """Result from running a single benchmark case"""

    def __init__(
        self,
        case_id: str,
        engine: str,
        decision: str,
        confidence: float,
        reasoning: str,
        latency_ms: float,
        correct: bool,
        visualization_correct: Optional[bool],
        error: Optional[str] = None,
    ):
        self.case_id = case_id
        self.engine = engine
        self.decision = decision
        self.confidence = confidence
        self.reasoning = reasoning
        self.latency_ms = latency_ms
        self.correct = correct
        self.visualization_correct = visualization_correct
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class BenchmarkRun:
    """A complete benchmark run comparing Jev vs LLM decisions"""

    def __init__(self, run_id: str, description: str = ""):
        self.run_id = run_id
        self.description = description
        self.timestamp = datetime.utcnow().isoformat()
        self.results: List[BenchmarkResult] = []
        self.metadata: Dict[str, Any] = {}

    def add_result(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    def compute_metrics(self, engine: str) -> Dict[str, Any]:
        """Compute aggregate metrics for a specific engine"""
        engine_results = [r for r in self.results if r.engine == engine]
        if not engine_results:
            return {}

        correct = [r for r in engine_results if r.correct]
        latencies = [r.latency_ms for r in engine_results]
        confidences = [r.confidence for r in engine_results]

        return {
            "engine": engine,
            "total_cases": len(engine_results),
            "correct": len(correct),
            "accuracy": len(correct) / len(engine_results),
            "accuracy_pct": round(len(correct) / len(engine_results) * 100, 1),
            "mean_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(
                sorted(latencies)[int(len(latencies) * 0.95)], 2
            ) if len(latencies) >= 20 else round(max(latencies), 2),
            "mean_confidence": round(statistics.mean(confidences), 3),
            "errors": sum(1 for r in engine_results if r.error),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "description": self.description,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "results": [r.to_dict() for r in self.results],
        }


class JevVsLLMBenchmark:
    """
    Compares Jev (rule-based) decisions against LLM decisions for routing tasks.

    For each test case it:
        1. Runs the Jev decision engine and records the result + latency
        2. Optionally runs the LLM decision engine (if Ollama is available)
        3. Compares accuracy against the expected ground-truth answer
        4. Saves the run to disk as a JSONL file

    Usage:
        benchmark = JevVsLLMBenchmark()
        run = benchmark.run(cases, jev_decider, llm_decider)
        benchmark.save_run(run)
        summary = benchmark.compare_engines(run)
    """

    def __init__(self, benchmark_dir: str = BENCHMARK_DIR):
        self.benchmark_dir = benchmark_dir
        os.makedirs(benchmark_dir, exist_ok=True)

    # ------------------------------------------------------------------
    #  Default test suite
    # ------------------------------------------------------------------

    def default_test_suite(self) -> List[BenchmarkCase]:
        """Return a default set of benchmark cases"""
        schema = (
            "Columns: order_id (int64), customer_id (int64), "
            "order_date (object), category (object), product (object), "
            "quantity (int64), unit_price (float64), revenue (float64), region (object)"
        )

        cases = [
            BenchmarkCase("R001", "What is the total revenue by category?", schema, "SQL", "bar_chart", "Aggregation → SQL"),
            BenchmarkCase("R002", "Show the monthly revenue trend for 2023", schema, "SQL", "line_chart", "Time series → SQL"),
            BenchmarkCase("R003", "Find all orders where revenue is greater than 5000", schema, "SQL", "table", "Filter → SQL"),
            BenchmarkCase("R004", "Which are the top 10 products by quantity sold?", schema, "SQL", "bar_chart", "Ranking → SQL"),
            BenchmarkCase("R005", "What is the correlation between quantity and revenue?", schema, "Python", "scatter_plot", "Correlation → Python"),
            BenchmarkCase("R006", "Plot the distribution of revenue", schema, "Python", "histogram", "Distribution → Python"),
            BenchmarkCase("R007", "Are there any outliers in the revenue column?", schema, "Python", "box_plot", "Outlier detection → Python"),
            BenchmarkCase("R008", "Group orders by region and show monthly trends", schema, "SQL", "line_chart", "Multi-group time series → SQL"),
            BenchmarkCase("R009", "What percentage of revenue comes from each category?", schema, "SQL", "pie_chart", "Part-to-whole → SQL"),
            BenchmarkCase("R010", "Identify customers who placed more than 5 orders", schema, "SQL", "table", "Filter + count → SQL"),
            BenchmarkCase("R011", "Calculate rolling 7-day average of revenue", schema, "Python", "line_chart", "Rolling window → Python"),
            BenchmarkCase("R012", "Show the heatmap of sales by region and category", schema, "Python", "heatmap", "2D heatmap → Python"),
            BenchmarkCase("R013", "Detect seasonal patterns in the sales data", schema, "Python", "line_chart", "Seasonality → Python"),
            BenchmarkCase("R014", "Count distinct customers per month", schema, "SQL", "bar_chart", "Count distinct → SQL"),
            BenchmarkCase("R015", "What is the median order value?", schema, "SQL", "table", "Median → SQL"),
        ]
        return cases

    # ------------------------------------------------------------------
    #  Run benchmark
    # ------------------------------------------------------------------

    def run(
        self,
        cases: List[BenchmarkCase],
        jev_decider: Callable,
        llm_decider: Optional[Callable] = None,
        run_id: Optional[str] = None,
        description: str = "",
    ) -> BenchmarkRun:
        """
        Run benchmarks against all provided cases.

        Args:
            cases: List of BenchmarkCase objects
            jev_decider: Callable(question, schema) -> dict{method, visualization, confidence, reasoning}
            llm_decider: Optional callable with same signature
            run_id: Unique run identifier (auto-generated if None)
            description: Human-readable run description

        Returns:
            BenchmarkRun with all results
        """
        if run_id is None:
            run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        benchmark_run = BenchmarkRun(run_id=run_id, description=description)
        benchmark_run.metadata = {
            "total_cases": len(cases),
            "engines": ["jev"] + (["llm"] if llm_decider else []),
        }

        print(f"\n{'='*60}")
        print(f"Benchmark Run: {run_id}")
        print(f"Cases: {len(cases)}")
        print(f"{'='*60}")

        for case in cases:
            print(f"\n  [{case.case_id}] {case.question[:60]}...")

            # Run Jev
            jev_result = self._run_single(case, jev_decider, "jev")
            benchmark_run.add_result(jev_result)
            print(f"    Jev:  {jev_result.decision:8s} | correct={jev_result.correct} | {jev_result.latency_ms:.1f}ms")

            # Run LLM if provided
            if llm_decider:
                llm_result = self._run_single(case, llm_decider, "llm")
                benchmark_run.add_result(llm_result)
                print(f"    LLM:  {llm_result.decision:8s} | correct={llm_result.correct} | {llm_result.latency_ms:.1f}ms")

        print(f"\n{'='*60}")
        return benchmark_run

    def _run_single(
        self,
        case: BenchmarkCase,
        decider: Callable,
        engine_name: str,
    ) -> BenchmarkResult:
        """Run a single benchmark case with a given decision engine"""
        start = time.perf_counter()
        error = None
        decision = ""
        confidence = 0.0
        reasoning = ""
        viz = ""

        try:
            result = decider(case.question, case.schema)
            decision = result.get("method", result.get("decision", "")).upper()
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            viz = result.get("visualization", "")
        except Exception as e:
            error = str(e)
            decision = "ERROR"

        latency_ms = (time.perf_counter() - start) * 1000

        correct = decision == case.expected_method
        viz_correct = (
            (viz.lower() == case.expected_visualization.lower())
            if case.expected_visualization and viz
            else None
        )

        return BenchmarkResult(
            case_id=case.case_id,
            engine=engine_name,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            latency_ms=round(latency_ms, 3),
            correct=correct,
            visualization_correct=viz_correct,
            error=error,
        )

    # ------------------------------------------------------------------
    #  Analysis
    # ------------------------------------------------------------------

    def compare_engines(self, run: BenchmarkRun) -> Dict[str, Any]:
        """Compare metrics across all engines in a run"""
        engines = set(r.engine for r in run.results)
        metrics = {engine: run.compute_metrics(engine) for engine in engines}

        comparison = {
            "run_id": run.run_id,
            "timestamp": run.timestamp,
            "engines": metrics,
            "winner": None,
            "summary": [],
        }

        if "jev" in metrics and "llm" in metrics:
            j = metrics["jev"]
            l = metrics["llm"]

            if j["accuracy"] > l["accuracy"]:
                comparison["winner"] = "jev"
            elif l["accuracy"] > j["accuracy"]:
                comparison["winner"] = "llm"
            else:
                # Tie — pick faster one
                comparison["winner"] = "jev" if j["mean_latency_ms"] < l["mean_latency_ms"] else "llm"

            comparison["summary"] = [
                f"Jev accuracy: {j['accuracy_pct']:.1f}%  |  LLM accuracy: {l['accuracy_pct']:.1f}%",
                f"Jev mean latency: {j['mean_latency_ms']:.1f}ms  |  LLM mean latency: {l['mean_latency_ms']:.1f}ms",
                f"Jev mean confidence: {j['mean_confidence']:.3f}  |  LLM mean confidence: {l['mean_confidence']:.3f}",
                f"Winner: {comparison['winner'].upper()}",
            ]
        elif "jev" in metrics:
            j = metrics["jev"]
            comparison["summary"] = [
                f"Jev accuracy: {j['accuracy_pct']:.1f}%",
                f"Jev mean latency: {j['mean_latency_ms']:.1f}ms",
            ]

        return comparison

    def print_summary(self, comparison: Dict[str, Any]) -> None:
        """Print a formatted benchmark summary"""
        print(f"\n{'='*60}")
        print(f"Benchmark Summary: {comparison['run_id']}")
        print(f"{'='*60}")
        for line in comparison.get("summary", []):
            print(f"  {line}")
        print()

        for engine, metrics in comparison.get("engines", {}).items():
            print(f"  [{engine.upper()}]")
            print(f"    Accuracy: {metrics['correct']}/{metrics['total_cases']} ({metrics['accuracy_pct']:.1f}%)")
            print(f"    Latency (mean/median): {metrics['mean_latency_ms']:.1f}ms / {metrics['median_latency_ms']:.1f}ms")
            print(f"    Confidence (mean): {metrics['mean_confidence']:.3f}")
            if metrics["errors"]:
                print(f"    Errors: {metrics['errors']}")
            print()

    # ------------------------------------------------------------------
    #  Persistence
    # ------------------------------------------------------------------

    def save_run(self, run: BenchmarkRun) -> str:
        """Save a benchmark run to a JSONL file"""
        path = os.path.join(self.benchmark_dir, f"{run.run_id}.json")
        with open(path, "w") as f:
            json.dump(run.to_dict(), f, indent=2)
        print(f"Benchmark saved: {path}")
        return path

    def load_run(self, run_id: str) -> Optional[BenchmarkRun]:
        """Load a saved benchmark run"""
        path = os.path.join(self.benchmark_dir, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)

        run = BenchmarkRun(
            run_id=data["run_id"],
            description=data.get("description", ""),
        )
        run.timestamp = data["timestamp"]
        run.metadata = data.get("metadata", {})
        for r_data in data.get("results", []):
            run.add_result(BenchmarkResult(**r_data))
        return run

    def list_runs(self) -> List[Dict[str, str]]:
        """List all saved benchmark runs"""
        runs = []
        if not os.path.exists(self.benchmark_dir):
            return runs
        for fname in sorted(os.listdir(self.benchmark_dir)):
            if fname.endswith(".json"):
                path = os.path.join(self.benchmark_dir, fname)
                try:
                    with open(path) as f:
                        data = json.load(f)
                    runs.append({
                        "run_id": data["run_id"],
                        "timestamp": data["timestamp"],
                        "description": data.get("description", ""),
                        "total_cases": data.get("metadata", {}).get("total_cases", 0),
                    })
                except Exception:
                    pass
        return runs

    def historical_accuracy(self, engine: str = "jev") -> List[Dict[str, Any]]:
        """Return accuracy trend across all saved runs for an engine"""
        history = []
        for run_info in self.list_runs():
            run = self.load_run(run_info["run_id"])
            if run:
                metrics = run.compute_metrics(engine)
                if metrics:
                    history.append({
                        "run_id": run_info["run_id"],
                        "timestamp": run.timestamp,
                        "accuracy_pct": metrics["accuracy_pct"],
                        "mean_latency_ms": metrics["mean_latency_ms"],
                    })
        return history
