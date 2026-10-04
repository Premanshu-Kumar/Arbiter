"""
Multi-File Joiner Agent — Phase 7

Allows users to upload multiple datasets and join them for cross-dataset analysis.
Uses DuckDB to register and join multiple DataFrames using auto-detected or
user-specified join keys.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import duckdb
import re


class JoinConfig:
    """Configuration for a dataset join operation"""

    def __init__(
        self,
        left_table: str,
        right_table: str,
        left_key: str,
        right_key: str,
        join_type: str = "INNER",
        alias: Optional[str] = None,
    ):
        self.left_table = left_table
        self.right_table = right_table
        self.left_key = left_key
        self.right_key = right_key
        self.join_type = join_type.upper()  # INNER, LEFT, RIGHT, FULL
        self.alias = alias or f"{left_table}_{right_table}"

    def to_sql(self) -> str:
        """Generate a SQL JOIN clause"""
        return (
            f"{self.left_table} "
            f"{self.join_type} JOIN {self.right_table} "
            f"ON {self.left_table}.{self.left_key} = {self.right_table}.{self.right_key}"
        )


class MultiFileJoiner:
    """
    Manages multiple uploaded datasets and provides join capabilities.

    Workflow:
        1. Register each dataset with a name  (register_dataset)
        2. Auto-detect or manually specify join keys  (detect_join_keys / configure_join)
        3. Execute the join and get back a merged DataFrame  (join_datasets)
        4. The merged DataFrame is available in DuckDB as a view
    """

    def __init__(self):
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.dataset_profiles: Dict[str, Dict[str, Any]] = {}
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._init_connection()

    # ------------------------------------------------------------------
    #  Connection management
    # ------------------------------------------------------------------

    def _init_connection(self) -> None:
        """Initialize in-memory DuckDB connection"""
        self.conn = duckdb.connect(":memory:")

    # ------------------------------------------------------------------
    #  Dataset registration
    # ------------------------------------------------------------------

    def register_dataset(self, name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Register a DataFrame under a table name.

        Args:
            name: Logical table name (alphanumeric + underscore)
            df: The DataFrame to register

        Returns:
            Profile dict for this dataset
        """
        # Sanitise the name
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_") or "dataset"
        self.datasets[safe_name] = df

        # Build a lightweight profile
        profile = self._profile_dataset(df, safe_name)
        self.dataset_profiles[safe_name] = profile

        # Register with DuckDB
        self.conn.register(safe_name, df)

        print(f"📂 Registered dataset '{safe_name}': {len(df):,} rows x {len(df.columns)} cols")
        return profile

    def _profile_dataset(self, df: pd.DataFrame, name: str) -> Dict[str, Any]:
        """Generate a lightweight profile for a dataset"""
        columns = {}
        for col in df.columns:
            columns[col] = {
                "dtype": str(df[col].dtype),
                "unique_count": int(df[col].nunique()),
                "null_pct": float(df[col].isnull().mean() * 100),
                "sample": df[col].dropna().head(3).tolist(),
            }
        return {
            "name": name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns,
        }

    def list_datasets(self) -> List[str]:
        """Return the list of registered dataset names"""
        return list(self.datasets.keys())

    def get_schemas(self) -> str:
        """Return a combined schema string for all registered datasets"""
        parts = []
        for name, profile in self.dataset_profiles.items():
            parts.append(f"Table: {name} ({profile['row_count']:,} rows)")
            for col, info in profile["columns"].items():
                parts.append(
                    f"  - {col} ({info['dtype']}) "
                    f"[{info['unique_count']} unique, {info['null_pct']:.1f}% null]"
                )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    #  Auto join-key detection
    # ------------------------------------------------------------------

    def detect_join_keys(
        self, left_name: str, right_name: str
    ) -> List[Dict[str, Any]]:
        """
        Heuristically detect candidate join key pairs between two datasets.

        Scoring rules:
        - Same column name in both tables -> high score
        - One name is a suffix/prefix of the other + compatible types -> medium score
        - High cardinality numeric column with same unique counts -> low-medium score

        Returns:
            List of candidates sorted by confidence (descending)
        """
        if left_name not in self.datasets or right_name not in self.datasets:
            return []

        left_profile = self.dataset_profiles[left_name]
        right_profile = self.dataset_profiles[right_name]

        left_cols = left_profile["columns"]
        right_cols = right_profile["columns"]

        candidates = []

        for l_col, l_info in left_cols.items():
            for r_col, r_info in right_cols.items():
                score = 0.0
                reason = []

                l_lower = l_col.lower()
                r_lower = r_col.lower()

                # Exact match
                if l_lower == r_lower:
                    score += 0.9
                    reason.append("exact name match")
                # One is suffix of the other (e.g., customer_id vs id)
                elif l_lower.endswith(r_lower) or r_lower.endswith(l_lower):
                    score += 0.6
                    reason.append("name suffix match")
                elif l_lower in r_lower or r_lower in l_lower:
                    score += 0.4
                    reason.append("name substring match")

                # Penalise free-text columns
                if any(kw in l_lower for kw in ["name", "description", "notes", "comment"]):
                    score -= 0.3

                # Reward ID-like column names
                if any(kw in l_lower for kw in ["id", "key", "code", "num", "no"]):
                    score += 0.2
                    reason.append("ID-like name")

                # Reward matching unique counts (potential FK->PK)
                if l_info["unique_count"] > 1 and r_info["unique_count"] > 1:
                    ratio = min(l_info["unique_count"], r_info["unique_count"]) / max(
                        l_info["unique_count"], r_info["unique_count"]
                    )
                    if ratio > 0.8:
                        score += 0.1
                        reason.append("similar cardinality")

                if score > 0.3:
                    candidates.append(
                        {
                            "left_key": l_col,
                            "right_key": r_col,
                            "confidence": min(score, 1.0),
                            "reason": ", ".join(reason),
                        }
                    )

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates[:5]  # Return top 5

    # ------------------------------------------------------------------
    #  Join execution
    # ------------------------------------------------------------------

    def join_datasets(
        self,
        join_configs: List[JoinConfig],
        select_columns: Optional[List[str]] = None,
        result_name: str = "joined_data",
    ) -> Dict[str, Any]:
        """
        Execute one or more joins and return the merged DataFrame.

        Args:
            join_configs: List of JoinConfig objects (supports chained joins)
            select_columns: Specific columns to include in the result (None = all)
            result_name: Name to register the result under in DuckDB

        Returns:
            dict with keys: success, result (DataFrame), sql, error, row_count
        """
        if not join_configs:
            return {"success": False, "error": "No join configurations provided"}

        try:
            # Build the FROM clause from the first join
            sql = self._build_join_sql(join_configs, select_columns)

            print(f"Executing join SQL:\n{sql}")
            result_df = self.conn.execute(sql).df()

            # Register the joined result
            self.conn.register(result_name, result_df)
            self.datasets[result_name] = result_df

            print(f"Join successful: {len(result_df):,} rows x {len(result_df.columns)} cols")

            return {
                "success": True,
                "result": result_df,
                "sql": sql,
                "row_count": len(result_df),
                "column_count": len(result_df.columns),
                "result_name": result_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "sql": ""}

    def _build_join_sql(
        self,
        join_configs: List[JoinConfig],
        select_columns: Optional[List[str]],
    ) -> str:
        """Build the complete JOIN SQL statement"""
        # Start from the first left table
        from_clause = join_configs[0].left_table

        join_clauses = []
        for cfg in join_configs:
            join_clauses.append(
                f"{cfg.join_type} JOIN {cfg.right_table} "
                f"ON {cfg.left_table}.{cfg.left_key} = {cfg.right_table}.{cfg.right_key}"
            )

        if select_columns:
            select_clause = ", ".join(select_columns)
        else:
            select_clause = "*"

        sql = f"SELECT {select_clause}\nFROM {from_clause}\n" + "\n".join(join_clauses)
        return sql

    def quick_join(
        self,
        left_name: str,
        right_name: str,
        join_type: str = "INNER",
        result_name: str = "joined_data",
    ) -> Dict[str, Any]:
        """
        Auto-detect join keys and perform a quick join.

        Returns:
            dict with success, result, sql, candidates (detected keys), error
        """
        candidates = self.detect_join_keys(left_name, right_name)

        if not candidates:
            return {
                "success": False,
                "error": "Could not auto-detect join keys. Please specify them manually.",
                "candidates": [],
            }

        best = candidates[0]
        join_cfg = JoinConfig(
            left_table=left_name,
            right_table=right_name,
            left_key=best["left_key"],
            right_key=best["right_key"],
            join_type=join_type,
        )

        result = self.join_datasets([join_cfg], result_name=result_name)
        result["candidates"] = candidates
        result["used_key"] = best
        return result

    def get_join_summary(
        self, left_name: str, right_name: str
    ) -> Dict[str, Any]:
        """Return a human-readable summary of two datasets and join candidates"""
        candidates = self.detect_join_keys(left_name, right_name)
        left_p = self.dataset_profiles.get(left_name, {})
        right_p = self.dataset_profiles.get(right_name, {})

        return {
            "left_dataset": {
                "name": left_name,
                "rows": left_p.get("row_count", 0),
                "columns": list(left_p.get("columns", {}).keys()),
            },
            "right_dataset": {
                "name": right_name,
                "rows": right_p.get("row_count", 0),
                "columns": list(right_p.get("columns", {}).keys()),
            },
            "join_candidates": candidates,
            "recommended_join": candidates[0] if candidates else None,
        }

    # ------------------------------------------------------------------
    #  SQL execution on registered tables
    # ------------------------------------------------------------------

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Execute arbitrary SQL against registered datasets"""
        try:
            result = self.conn.execute(sql).df()
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the DuckDB connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
