"""
Phase 7 Integration Tests — Advanced Features

Tests for:
  1. Multi-file joins (MultiFileJoiner)
  2. Automatic EDA (AutoEDAAgent)
  3. Dataset versioning (DatasetVersionManager)
  4. Jev vs LLM benchmark (JevVsLLMBenchmark)
  5. Model performance dashboard (ModelPerformanceDashboard)
  6. Docker sandbox status (DockerSandbox)
"""
import pytest
import pandas as pd
import numpy as np
import os
import shutil
import tempfile
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def sales_df():
    """Sample sales DataFrame"""
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "order_id": range(1, n + 1),
        "customer_id": np.random.randint(1, 51, n),
        "product_id": np.random.randint(1, 21, n),
        "order_date": pd.date_range("2023-01-01", periods=n, freq="D"),
        "category": np.random.choice(["Electronics", "Clothing", "Books", "Food"], n),
        "quantity": np.random.randint(1, 10, n),
        "unit_price": np.round(np.random.uniform(10, 500, n), 2),
        "revenue": np.round(np.random.uniform(20, 3000, n), 2),
        "region": np.random.choice(["North", "South", "East", "West"], n),
    })


@pytest.fixture
def customers_df():
    """Sample customers DataFrame (joinable with sales_df)"""
    return pd.DataFrame({
        "customer_id": range(1, 51),
        "customer_name": [f"Customer {i}" for i in range(1, 51)],
        "city": np.random.choice(["Mumbai", "Delhi", "Chennai", "Bangalore"], 50),
        "segment": np.random.choice(["Retail", "Wholesale", "Online"], 50),
        "signup_date": pd.date_range("2022-01-01", periods=50, freq="7D"),
    })


@pytest.fixture
def products_df():
    """Sample products DataFrame (joinable with sales_df)"""
    return pd.DataFrame({
        "product_id": range(1, 21),
        "product_name": [f"Product {i}" for i in range(1, 21)],
        "brand": np.random.choice(["BrandA", "BrandB", "BrandC"], 20),
        "cost_price": np.round(np.random.uniform(5, 200, 20), 2),
    })


@pytest.fixture
def temp_dir():
    """Temporary directory for versioning tests"""
    d = tempfile.mkdtemp(prefix="phase7_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────
#  1. Multi-File Joiner Tests
# ──────────────────────────────────────────────────────────────────────

class TestMultiFileJoiner:
    def setup_method(self):
        from agents.multi_file_joiner import MultiFileJoiner
        self.joiner = MultiFileJoiner()

    def teardown_method(self):
        self.joiner.close()

    def test_register_single_dataset(self, sales_df):
        profile = self.joiner.register_dataset("sales", sales_df)
        assert profile["name"] == "sales"
        assert profile["row_count"] == len(sales_df)
        assert "order_id" in profile["columns"]

    def test_list_datasets(self, sales_df, customers_df):
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        datasets = self.joiner.list_datasets()
        assert "sales" in datasets
        assert "customers" in datasets

    def test_detect_join_keys_exact_match(self, sales_df, customers_df):
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        candidates = self.joiner.detect_join_keys("sales", "customers")
        assert len(candidates) > 0
        # customer_id should be top candidate
        top = candidates[0]
        assert top["left_key"] == "customer_id"
        assert top["right_key"] == "customer_id"
        assert top["confidence"] >= 0.8

    def test_inner_join(self, sales_df, customers_df):
        from agents.multi_file_joiner import JoinConfig
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        cfg = JoinConfig("sales", "customers", "customer_id", "customer_id", "INNER")
        result = self.joiner.join_datasets([cfg], result_name="test_join")
        assert result["success"] is True
        assert isinstance(result["result"], pd.DataFrame)
        assert result["row_count"] > 0
        assert "customer_name" in result["result"].columns
        assert "revenue" in result["result"].columns

    def test_left_join(self, sales_df, customers_df):
        from agents.multi_file_joiner import JoinConfig
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        cfg = JoinConfig("sales", "customers", "customer_id", "customer_id", "LEFT")
        result = self.joiner.join_datasets([cfg], result_name="left_join")
        assert result["success"] is True
        # LEFT join should have at least as many rows as sales_df
        assert result["row_count"] >= len(sales_df)

    def test_quick_join(self, sales_df, customers_df):
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        result = self.joiner.quick_join("sales", "customers")
        assert result["success"] is True
        assert "candidates" in result
        assert "used_key" in result

    def test_get_schemas(self, sales_df, customers_df):
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        schemas = self.joiner.get_schemas()
        assert "sales" in schemas
        assert "customers" in schemas

    def test_execute_sql(self, sales_df):
        self.joiner.register_dataset("sales", sales_df)
        result = self.joiner.execute_sql("SELECT COUNT(*) as cnt FROM sales")
        assert result["success"] is True
        assert result["result"]["cnt"].iloc[0] == len(sales_df)

    def test_join_summary(self, sales_df, customers_df):
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        summary = self.joiner.get_join_summary("sales", "customers")
        assert summary["left_dataset"]["name"] == "sales"
        assert summary["right_dataset"]["name"] == "customers"
        assert "join_candidates" in summary

    def test_no_datasets_join_fails(self):
        from agents.multi_file_joiner import JoinConfig
        cfg = JoinConfig("a", "b", "x", "y")
        result = self.joiner.join_datasets([cfg])
        # Should fail gracefully
        assert result["success"] is False

    def test_three_table_join(self, sales_df, customers_df, products_df):
        from agents.multi_file_joiner import JoinConfig
        self.joiner.register_dataset("sales", sales_df)
        self.joiner.register_dataset("customers", customers_df)
        self.joiner.register_dataset("products", products_df)
        cfgs = [
            JoinConfig("sales", "customers", "customer_id", "customer_id", "INNER"),
            JoinConfig("sales", "products", "product_id", "product_id", "INNER"),
        ]
        result = self.joiner.join_datasets(cfgs, result_name="triple_join")
        assert result["success"] is True
        assert "product_name" in result["result"].columns
        assert "customer_name" in result["result"].columns


# ──────────────────────────────────────────────────────────────────────
#  2. Auto EDA Tests
# ──────────────────────────────────────────────────────────────────────

class TestAutoEDAAgent:
    def setup_method(self):
        from agents.auto_eda_agent import AutoEDAAgent
        self.eda = AutoEDAAgent()

    def test_run_eda_returns_report(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales_test")
        assert "overview" in report
        assert "missing_values" in report
        assert "numeric_analysis" in report
        assert "categorical_analysis" in report
        assert "correlation_analysis" in report
        assert "temporal_analysis" in report
        assert "duplicate_analysis" in report
        assert "insights" in report
        assert "recommendations" in report

    def test_overview_correct(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        ov = report["overview"]
        assert ov["rows"] == len(sales_df)
        assert ov["columns"] == len(sales_df.columns)
        assert ov["memory_mb"] > 0

    def test_numeric_analysis(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        numeric_cols = {c["column"] for c in report["numeric_analysis"]}
        assert "revenue" in numeric_cols
        assert "quantity" in numeric_cols
        # Check structure
        first = report["numeric_analysis"][0]
        assert "mean" in first
        assert "std" in first
        assert "outlier_pct" in first
        assert "skewness" in first

    def test_categorical_analysis(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        cat_cols = {c["column"] for c in report["categorical_analysis"]}
        assert "category" in cat_cols
        assert "region" in cat_cols

    def test_correlation_analysis(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        corr = report["correlation_analysis"]
        assert corr["available"] is True
        assert "matrix" in corr

    def test_missing_values_zero(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        mv = report["missing_values"]
        assert mv["total_missing"] == 0

    def test_missing_values_detected(self, sales_df):
        df_with_missing = sales_df.copy()
        df_with_missing.loc[0:10, "revenue"] = np.nan
        report = self.eda.run_eda(df_with_missing, "sales")
        mv = report["missing_values"]
        assert mv["total_missing"] > 0
        assert any(c["column"] == "revenue" for c in mv["columns_with_missing"])

    def test_duplicate_detection(self, sales_df):
        df_with_dupes = pd.concat([sales_df, sales_df.head(10)], ignore_index=True)
        report = self.eda.run_eda(df_with_dupes, "sales")
        dupes = report["duplicate_analysis"]
        assert dupes["total_duplicates"] == 10

    def test_insights_non_empty(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        assert len(report["insights"]) > 0

    def test_recommendations_non_empty(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        assert len(report["recommendations"]) > 0

    def test_to_markdown(self, sales_df):
        self.eda.run_eda(sales_df, "sales")
        md = self.eda.to_markdown()
        assert "# Automatic EDA Report" in md
        assert "## Key Insights" in md
        assert "## Recommendations" in md

    def test_temporal_detection(self, sales_df):
        report = self.eda.run_eda(sales_df, "sales")
        temporal = report["temporal_analysis"]
        assert temporal["available"] is True  # order_date is a datetime col

    def test_single_column_df(self):
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})
        report = self.eda.run_eda(df, "single_col")
        assert report["overview"]["columns"] == 1


# ──────────────────────────────────────────────────────────────────────
#  3. Dataset Versioning Tests
# ──────────────────────────────────────────────────────────────────────

class TestDatasetVersionManager:
    def setup_method(self, temp_dir=None):
        from agents.dataset_versioning import DatasetVersionManager
        self.temp_dir = tempfile.mkdtemp(prefix="ver_test_")
        self.vm = DatasetVersionManager(versions_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_version(self, sales_df):
        version = self.vm.save_version("sales", sales_df, description="Test v1")
        assert version.version_id == "v0001"
        loaded = self.vm.load_version("sales", "v0001")
        assert loaded is not None
        assert len(loaded) == len(sales_df)
        assert list(loaded.columns) == list(sales_df.columns)

    def test_version_increments(self, sales_df):
        v1 = self.vm.save_version("sales", sales_df)
        v2 = self.vm.save_version("sales", sales_df.head(100))
        assert v1.version_id == "v0001"
        assert v2.version_id == "v0002"

    def test_list_versions(self, sales_df):
        self.vm.save_version("sales", sales_df)
        self.vm.save_version("sales", sales_df.head(100))
        versions = self.vm.list_versions("sales")
        assert len(versions) == 2
        assert versions[0].version_id == "v0001"
        assert versions[1].version_id == "v0002"

    def test_list_all_datasets(self, sales_df, customers_df):
        self.vm.save_version("sales", sales_df)
        self.vm.save_version("customers", customers_df)
        all_ds = self.vm.list_all_datasets()
        assert "sales" in all_ds
        assert "customers" in all_ds

    def test_load_latest(self, sales_df):
        self.vm.save_version("sales", sales_df)
        self.vm.save_version("sales", sales_df.head(100))
        latest = self.vm.load_latest_version("sales")
        assert latest is not None
        assert len(latest) == 100

    def test_compare_versions(self, sales_df):
        self.vm.save_version("sales", sales_df)
        reduced = sales_df.head(100)
        self.vm.save_version("sales", reduced)
        diff = self.vm.compare_versions("sales", "v0001", "v0002")
        assert "error" not in diff
        assert diff["row_count_change"] == -100
        assert diff["schema_changed"] is False

    def test_compare_schema_changed(self, sales_df):
        self.vm.save_version("sales", sales_df)
        extra_col = sales_df.copy()
        extra_col["new_col"] = 99
        self.vm.save_version("sales", extra_col)
        diff = self.vm.compare_versions("sales", "v0001", "v0002")
        assert diff["schema_changed"] is True
        assert "new_col" in diff["added_columns"]

    def test_delete_version(self, sales_df):
        self.vm.save_version("sales", sales_df)
        assert len(self.vm.list_versions("sales")) == 1
        self.vm.delete_version("sales", "v0001")
        assert len(self.vm.list_versions("sales")) == 0

    def test_to_dataframe(self, sales_df):
        self.vm.save_version("sales", sales_df)
        self.vm.save_version("sales", sales_df.head(50))
        df = self.vm.to_dataframe("sales")
        assert len(df) == 2
        assert "version_id" in df.columns

    def test_metadata_persisted(self, sales_df):
        self.vm.save_version("sales", sales_df, source_file="test.csv", description="My description")
        meta = self.vm.get_version_metadata("sales", "v0001")
        assert meta is not None
        assert meta.description == "My description"
        assert meta.source_file == "test.csv"
        assert meta.row_count == len(sales_df)

    def test_checksums_differ_for_different_data(self, sales_df):
        v1 = self.vm.save_version("sales", sales_df)
        v2 = self.vm.save_version("sales", sales_df.head(100))
        assert v1.checksum != v2.checksum

    def test_checksums_same_for_same_data(self, sales_df):
        v1 = self.vm.save_version("sales", sales_df)
        v2 = self.vm.save_version("sales", sales_df.copy())
        assert v1.checksum == v2.checksum


# ──────────────────────────────────────────────────────────────────────
#  4. Jev vs LLM Benchmark Tests
# ──────────────────────────────────────────────────────────────────────

class TestJevVsLLMBenchmark:
    def setup_method(self):
        from eval.jev_vs_llm_benchmark import JevVsLLMBenchmark
        self.temp_dir = tempfile.mkdtemp(prefix="bench_test_")
        self.benchmark = JevVsLLMBenchmark(benchmark_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _mock_sql_decider(self, question: str, schema: str) -> dict:
        """Always returns SQL"""
        return {"method": "SQL", "confidence": 0.9, "reasoning": "Mock SQL"}

    def _mock_python_decider(self, question: str, schema: str) -> dict:
        """Always returns Python"""
        return {"method": "PYTHON", "confidence": 0.8, "reasoning": "Mock Python"}

    def test_default_test_suite(self):
        cases = self.benchmark.default_test_suite()
        assert len(cases) == 15
        assert all(hasattr(c, "case_id") for c in cases)
        assert all(hasattr(c, "expected_method") for c in cases)

    def test_run_benchmark_jev_only(self):
        cases = self.benchmark.default_test_suite()[:5]
        run = self.benchmark.run(cases, self._mock_sql_decider, run_id="test_run")
        assert len(run.results) == 5
        assert all(r.engine == "jev" for r in run.results)

    def test_run_benchmark_both_engines(self):
        cases = self.benchmark.default_test_suite()[:3]
        run = self.benchmark.run(
            cases, self._mock_sql_decider,
            llm_decider=self._mock_python_decider,
            run_id="test_both"
        )
        assert len(run.results) == 6  # 3 cases x 2 engines
        engines = set(r.engine for r in run.results)
        assert "jev" in engines
        assert "llm" in engines

    def test_compute_metrics(self):
        cases = self.benchmark.default_test_suite()[:5]
        run = self.benchmark.run(cases, self._mock_sql_decider, run_id="metric_test")
        metrics = run.compute_metrics("jev")
        assert metrics["total_cases"] == 5
        assert 0 <= metrics["accuracy"] <= 1
        assert metrics["mean_latency_ms"] >= 0

    def test_compare_engines(self):
        cases = self.benchmark.default_test_suite()[:5]
        run = self.benchmark.run(
            cases, self._mock_sql_decider,
            llm_decider=self._mock_python_decider,
            run_id="compare_test"
        )
        comparison = self.benchmark.compare_engines(run)
        assert "engines" in comparison
        assert "winner" in comparison
        assert "jev" in comparison["engines"]
        assert "llm" in comparison["engines"]

    def test_save_and_load_run(self):
        cases = self.benchmark.default_test_suite()[:3]
        run = self.benchmark.run(cases, self._mock_sql_decider, run_id="save_test")
        self.benchmark.save_run(run)
        loaded = self.benchmark.load_run("save_test")
        assert loaded is not None
        assert loaded.run_id == "save_test"
        assert len(loaded.results) == 3

    def test_list_runs(self):
        cases = self.benchmark.default_test_suite()[:2]
        self.benchmark.run(cases, self._mock_sql_decider, run_id="run_a")
        self.benchmark.save_run(self.benchmark.run(cases, self._mock_sql_decider, run_id="run_b"))
        self.benchmark.save_run(self.benchmark.run(cases, self._mock_sql_decider, run_id="run_c"))
        runs = self.benchmark.list_runs()
        run_ids = [r["run_id"] for r in runs]
        assert "run_b" in run_ids
        assert "run_c" in run_ids

    def test_historical_accuracy(self):
        for i in range(3):
            cases = self.benchmark.default_test_suite()[:3]
            run = self.benchmark.run(cases, self._mock_sql_decider, run_id=f"hist_{i}")
            self.benchmark.save_run(run)
        history = self.benchmark.historical_accuracy("jev")
        assert len(history) == 3
        assert all("accuracy_pct" in h for h in history)

    def test_perfect_accuracy_decider(self):
        """A decider that always returns the correct expected method should get 100%"""
        cases = self.benchmark.default_test_suite()
        # Build a look-up for expected methods
        expected = {c.case_id: c.expected_method for c in cases}

        def perfect_decider(question, schema):
            # This is a cheat decider for testing
            for c in cases:
                if c.question == question:
                    return {"method": c.expected_method, "confidence": 1.0, "reasoning": "perfect"}
            return {"method": "SQL", "confidence": 1.0}

        run = self.benchmark.run(cases[:5], perfect_decider, run_id="perfect")
        metrics = run.compute_metrics("jev")
        assert metrics["accuracy"] == 1.0


# ──────────────────────────────────────────────────────────────────────
#  5. Performance Dashboard Tests
# ──────────────────────────────────────────────────────────────────────

class TestModelPerformanceDashboard:
    def setup_method(self):
        from eval.performance_dashboard import ModelPerformanceDashboard
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, prefix="perf_test_"
        ).name
        self.dashboard = ModelPerformanceDashboard(metrics_file=self.temp_file)

    def teardown_method(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def _make_state(self, **kwargs):
        """Create a minimal workflow state dict"""
        defaults = {
            "question": "Test question?",
            "selected_agent": "SQL",
            "code_type": "sql",
            "error": None,
            "retry_count": 0,
            "heal_attempts": 0,
            "valid": True,
            "quality_score": 0.9,
            "cross_check_performed": False,
            "cross_check_match": None,
            "confidence": 0.75,
        }
        defaults.update(kwargs)
        return defaults

    def test_record_and_load(self):
        state = self._make_state()
        self.dashboard.record(state, latency_ms=1234.5)
        metrics = self.dashboard.load_all()
        assert len(metrics) == 1
        assert metrics[0].agent == "SQL"
        assert metrics[0].latency_ms == 1234.5

    def test_multiple_records(self):
        for i in range(5):
            self.dashboard.record(self._make_state(selected_agent="SQL"), latency_ms=i * 100.0)
        for i in range(3):
            self.dashboard.record(self._make_state(selected_agent="Python", error="fail"), latency_ms=200.0)
        metrics = self.dashboard.load_all()
        assert len(metrics) == 8

    def test_summary_stats(self):
        for i in range(10):
            self.dashboard.record(self._make_state(), latency_ms=500.0)
        stats = self.dashboard.summary_stats()
        assert stats["total_runs"] == 10
        assert stats["success_count"] == 10
        assert stats["success_rate"] == 1.0
        assert stats["mean_latency_ms"] == 500.0

    def test_success_rate_with_failures(self):
        for _ in range(7):
            self.dashboard.record(self._make_state(), latency_ms=100.0)
        for _ in range(3):
            self.dashboard.record(self._make_state(error="Some error"), latency_ms=100.0)
        stats = self.dashboard.summary_stats()
        assert stats["success_rate"] == pytest.approx(0.7)
        assert stats["failure_count"] == 3

    def test_agent_stats_breakdown(self):
        for _ in range(5):
            self.dashboard.record(self._make_state(selected_agent="SQL"), latency_ms=100.0)
        for _ in range(5):
            self.dashboard.record(self._make_state(selected_agent="Python"), latency_ms=200.0)
        stats = self.dashboard.summary_stats()
        agent_stats = stats["agent_stats"]
        assert "SQL" in agent_stats
        assert "Python" in agent_stats
        assert agent_stats["SQL"]["total"] == 5
        assert agent_stats["Python"]["total"] == 5

    def test_latency_buckets(self):
        buckets_input = [100, 600, 2000, 10000, 60000]
        for lat in buckets_input:
            self.dashboard.record(self._make_state(), latency_ms=float(lat))
        buckets = self.dashboard.latency_buckets()
        assert buckets["0-500ms"] == 1
        assert buckets["500ms-1s"] == 1
        assert buckets["1s-5s"] == 1
        assert buckets["5s-30s"] == 1
        assert buckets["30s+"] == 1

    def test_retry_distribution(self):
        for retries in [0, 0, 0, 1, 1, 2]:
            self.dashboard.record(self._make_state(retry_count=retries), latency_ms=100.0)
        dist = self.dashboard.retry_distribution()
        assert dist["0"] == 3
        assert dist["1"] == 2
        assert dist["2"] == 1

    def test_error_breakdown(self):
        self.dashboard.record(self._make_state(error="Timeout error"), latency_ms=30001.0)
        self.dashboard.record(self._make_state(error="Syntax error in SQL"), latency_ms=100.0)
        self.dashboard.record(self._make_state(error="Column not found"), latency_ms=100.0)
        errors = self.dashboard.error_breakdown()
        categories = [e["error_category"] for e in errors]
        assert "timeout" in categories or "syntax_error" in categories

    def test_export_to_dataframe(self):
        for _ in range(5):
            self.dashboard.record(self._make_state(), latency_ms=100.0)
        df = self.dashboard.export_to_dataframe()
        assert len(df) == 5
        assert "agent" in df.columns
        assert "latency_ms" in df.columns

    def test_load_recent(self):
        for i in range(20):
            self.dashboard.record(self._make_state(question=f"Q{i}"), latency_ms=100.0)
        recent = self.dashboard.load_recent(5)
        assert len(recent) == 5

    def test_clear(self):
        self.dashboard.record(self._make_state(), latency_ms=100.0)
        self.dashboard.clear()
        assert self.dashboard.load_all() == []

    def test_empty_stats(self):
        stats = self.dashboard.summary_stats()
        assert stats["total_runs"] == 0


# ──────────────────────────────────────────────────────────────────────
#  6. Docker Sandbox Tests
# ──────────────────────────────────────────────────────────────────────

class TestDockerSandbox:
    def setup_method(self):
        from sandbox.docker_sandbox import DockerSandbox
        self.sandbox = DockerSandbox()

    def test_status_returns_dict(self):
        status = self.sandbox.status()
        assert "docker_available" in status
        assert "image" in status
        assert "memory_limit" in status
        assert "timeout_seconds" in status

    def test_is_available_is_bool(self):
        assert isinstance(self.sandbox.is_available, bool)

    def test_unavailable_returns_error_not_exception(self):
        """If Docker is not available, execute should return error dict, not raise"""
        if not self.sandbox.is_available:
            result = self.sandbox.execute_python("result = 1 + 1")
            assert result["success"] is False
            assert "docker_available" in result
            assert result["docker_available"] is False
        else:
            pytest.skip("Docker is available on this machine — unavailable path not testable")

    def test_image_exists_returns_bool(self):
        result = self.sandbox.image_exists()
        assert isinstance(result, bool)


# ──────────────────────────────────────────────────────────────────────
#  7. Performance Timer Tests
# ──────────────────────────────────────────────────────────────────────

class TestPerformanceTimer:
    def test_timer_records_elapsed(self):
        import time
        from eval.performance_dashboard import PerformanceTimer
        with PerformanceTimer() as t:
            time.sleep(0.05)
        assert t.elapsed_ms >= 40  # at least 40ms

    def test_timer_zero_before_use(self):
        from eval.performance_dashboard import PerformanceTimer
        t = PerformanceTimer()
        assert t.elapsed_ms == 0.0


# ──────────────────────────────────────────────────────────────────────
#  8. JoinConfig Tests
# ──────────────────────────────────────────────────────────────────────

class TestJoinConfig:
    def test_to_sql(self):
        from agents.multi_file_joiner import JoinConfig
        cfg = JoinConfig("sales", "customers", "customer_id", "customer_id", "INNER")
        sql = cfg.to_sql()
        assert "INNER JOIN customers" in sql
        assert "sales.customer_id = customers.customer_id" in sql

    def test_left_join_sql(self):
        from agents.multi_file_joiner import JoinConfig
        cfg = JoinConfig("orders", "products", "product_id", "id", "LEFT")
        sql = cfg.to_sql()
        assert "LEFT JOIN products" in sql

    def test_alias_defaults(self):
        from agents.multi_file_joiner import JoinConfig
        cfg = JoinConfig("a", "b", "x", "y")
        assert cfg.alias == "a_b"

    def test_custom_alias(self):
        from agents.multi_file_joiner import JoinConfig
        cfg = JoinConfig("a", "b", "x", "y", alias="my_join")
        assert cfg.alias == "my_join"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
