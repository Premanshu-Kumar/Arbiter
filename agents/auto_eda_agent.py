"""
Automatic EDA Agent — Phase 7

Runs a comprehensive Exploratory Data Analysis on any uploaded dataset without
the user needing to ask specific questions. Produces a structured EDA report
covering distribution, correlations, outliers, missing data patterns, and
auto-generated insights.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import json


class AutoEDAAgent:
    """
    Automatically generates a full Exploratory Data Analysis for a dataset.

    The EDA covers:
        - Dataset overview (shape, dtypes, memory)
        - Missing value analysis
        - Numeric column statistics (mean, std, skewness, kurtosis, outliers)
        - Categorical column analysis (cardinality, top values, entropy)
        - Correlation matrix & highly correlated pairs
        - Temporal column detection & trend hints
        - Automated text insights and recommendations
    """

    def __init__(self):
        self.results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    #  Main entry point
    # ------------------------------------------------------------------

    def run_eda(self, df: pd.DataFrame, dataset_name: str = "dataset") -> Dict[str, Any]:
        """
        Run the full EDA pipeline.

        Args:
            df: Input DataFrame
            dataset_name: Label to use in the report

        Returns:
            Comprehensive EDA report as a dict
        """
        print(f"🔍 Auto EDA: Analysing '{dataset_name}' ({len(df):,} rows x {len(df.columns)} cols)...")

        report = {
            "dataset_name": dataset_name,
            "overview": self._overview(df),
            "missing_values": self._missing_values(df),
            "numeric_analysis": self._numeric_analysis(df),
            "categorical_analysis": self._categorical_analysis(df),
            "correlation_analysis": self._correlation_analysis(df),
            "temporal_analysis": self._temporal_analysis(df),
            "duplicate_analysis": self._duplicate_analysis(df),
            "insights": [],
            "recommendations": [],
        }

        # Generate insights and recommendations from the analysis
        report["insights"] = self._generate_insights(report, df)
        report["recommendations"] = self._generate_recommendations(report, df)

        self.results = report
        print(f"   EDA complete — {len(report['insights'])} insights found")
        return report

    # ------------------------------------------------------------------
    #  Individual analysis sections
    # ------------------------------------------------------------------

    def _overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Basic dataset overview"""
        dtypes = df.dtypes.value_counts().to_dict()
        dtype_summary = {str(k): int(v) for k, v in dtypes.items()}

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "dtype_summary": dtype_summary,
            "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
            "categorical_columns": df.select_dtypes(include=["object", "category"]).columns.tolist(),
            "datetime_columns": df.select_dtypes(include=["datetime"]).columns.tolist(),
            "bool_columns": df.select_dtypes(include=["bool"]).columns.tolist(),
            "column_names": df.columns.tolist(),
        }

    def _missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Missing value analysis"""
        missing_count = df.isnull().sum()
        missing_pct = (missing_count / len(df) * 100).round(2)

        columns_with_missing = [
            {
                "column": col,
                "missing_count": int(missing_count[col]),
                "missing_pct": float(missing_pct[col]),
            }
            for col in df.columns
            if missing_count[col] > 0
        ]
        columns_with_missing.sort(key=lambda x: x["missing_pct"], reverse=True)

        total_cells = len(df) * len(df.columns)
        total_missing = int(missing_count.sum())

        return {
            "total_missing": total_missing,
            "total_missing_pct": round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0,
            "columns_with_missing": columns_with_missing,
            "complete_columns": int((missing_count == 0).sum()),
            "complete_rows": int(df.dropna().shape[0]),
            "complete_rows_pct": round(df.dropna().shape[0] / len(df) * 100, 2) if len(df) > 0 else 0,
        }

    def _numeric_analysis(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Per-column numeric statistics"""
        numeric_cols = df.select_dtypes(include="number").columns
        results = []

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outliers = series[(series < lower_fence) | (series > upper_fence)]

            try:
                skewness = float(series.skew())
                kurtosis = float(series.kurtosis())
            except Exception:
                skewness = 0.0
                kurtosis = 0.0

            results.append(
                {
                    "column": col,
                    "count": int(series.count()),
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "q1": q1,
                    "median": float(series.median()),
                    "q3": q3,
                    "max": float(series.max()),
                    "iqr": float(iqr),
                    "skewness": skewness,
                    "kurtosis": kurtosis,
                    "outlier_count": int(len(outliers)),
                    "outlier_pct": round(len(outliers) / len(series) * 100, 2),
                    "zero_count": int((series == 0).sum()),
                    "negative_count": int((series < 0).sum()),
                    "unique_count": int(series.nunique()),
                }
            )

        return results

    def _categorical_analysis(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Per-column categorical statistics"""
        cat_cols = df.select_dtypes(include=["object", "category"]).columns
        results = []

        for col in cat_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            vc = series.value_counts()
            top_values = [
                {"value": str(k), "count": int(v), "pct": round(v / len(series) * 100, 2)}
                for k, v in vc.head(10).items()
            ]

            # Shannon entropy as a measure of diversity
            probs = vc / len(series)
            entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

            results.append(
                {
                    "column": col,
                    "unique_count": int(series.nunique()),
                    "unique_pct": round(series.nunique() / len(series) * 100, 2),
                    "top_values": top_values,
                    "most_frequent": str(vc.index[0]) if len(vc) > 0 else None,
                    "most_frequent_pct": round(vc.iloc[0] / len(series) * 100, 2) if len(vc) > 0 else 0,
                    "entropy": round(entropy, 3),
                    "is_likely_id": series.nunique() == len(series),
                    "is_binary": series.nunique() == 2,
                    "is_low_cardinality": series.nunique() <= 10,
                }
            )

        return results

    def _correlation_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Correlation matrix and high-correlation pairs"""
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.shape[1] < 2:
            return {"available": False, "reason": "Less than 2 numeric columns"}

        corr_matrix = numeric_df.corr()

        # Find highly correlated pairs
        high_corr = []
        cols = corr_matrix.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) >= 0.7 and not pd.isna(corr_val):
                    high_corr.append(
                        {
                            "col_a": cols[i],
                            "col_b": cols[j],
                            "correlation": round(float(corr_val), 4),
                            "strength": "strong" if abs(corr_val) >= 0.9 else "moderate",
                        }
                    )

        high_corr.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        # Convert matrix to JSON-safe format
        corr_dict = {}
        for col in cols:
            corr_dict[col] = {
                other: round(float(corr_matrix.loc[col, other]), 4)
                for other in cols
                if not pd.isna(corr_matrix.loc[col, other])
            }

        return {
            "available": True,
            "matrix": corr_dict,
            "high_correlation_pairs": high_corr[:10],
            "total_high_corr_pairs": len(high_corr),
        }

    def _temporal_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect and analyse datetime columns"""
        dt_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        # Also try to parse object columns that look like dates
        for col in df.select_dtypes(include="object").columns:
            sample = df[col].dropna().head(20)
            try:
                parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="raise")
                if len(parsed) > 5:
                    dt_cols.append(col)
            except Exception:
                pass

        if not dt_cols:
            return {"available": False, "datetime_columns": []}

        analyses = []
        for col in dt_cols:
            try:
                series = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(series) == 0:
                    continue
                analyses.append(
                    {
                        "column": col,
                        "min_date": str(series.min()),
                        "max_date": str(series.max()),
                        "date_range_days": int((series.max() - series.min()).days),
                        "unique_dates": int(series.nunique()),
                        "has_gaps": self._check_date_gaps(series),
                    }
                )
            except Exception:
                pass

        return {
            "available": bool(analyses),
            "datetime_columns": [a["column"] for a in analyses],
            "analyses": analyses,
        }

    def _check_date_gaps(self, series: pd.Series) -> bool:
        """Check if a datetime series has unexpected gaps"""
        try:
            sorted_dates = series.sort_values().dt.normalize().unique()
            if len(sorted_dates) < 3:
                return False
            diffs = pd.Series(sorted_dates).diff().dropna()
            median_diff = diffs.median()
            return bool((diffs > median_diff * 3).any())
        except Exception:
            return False

    def _duplicate_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect duplicate rows"""
        total_dupes = int(df.duplicated().sum())
        return {
            "total_duplicates": total_dupes,
            "duplicate_pct": round(total_dupes / len(df) * 100, 2) if len(df) > 0 else 0,
            "unique_rows": len(df) - total_dupes,
        }

    # ------------------------------------------------------------------
    #  Insights & recommendations generator
    # ------------------------------------------------------------------

    def _generate_insights(self, report: Dict[str, Any], df: pd.DataFrame) -> List[str]:
        """Auto-generate text insights from the EDA results"""
        insights = []
        overview = report["overview"]
        missing = report["missing_values"]
        dupes = report["duplicate_analysis"]
        corr = report["correlation_analysis"]

        # Size
        insights.append(
            f"The dataset has {overview['rows']:,} rows and {overview['columns']} columns "
            f"({overview['memory_mb']} MB in memory)."
        )

        # Missing values
        if missing["total_missing"] == 0:
            insights.append("No missing values detected — the dataset is complete.")
        else:
            insights.append(
                f"{missing['total_missing_pct']:.1f}% of all values are missing. "
                f"{len(missing['columns_with_missing'])} column(s) have missing data."
            )
            worst = missing["columns_with_missing"][0] if missing["columns_with_missing"] else None
            if worst and worst["missing_pct"] > 30:
                insights.append(
                    f"Column '{worst['column']}' is missing {worst['missing_pct']:.1f}% of values — "
                    "consider dropping or imputing it."
                )

        # Duplicates
        if dupes["total_duplicates"] > 0:
            insights.append(
                f"{dupes['total_duplicates']:,} duplicate rows detected "
                f"({dupes['duplicate_pct']:.1f}% of rows)."
            )

        # Numeric columns
        for col_info in report["numeric_analysis"]:
            if col_info["outlier_pct"] > 10:
                insights.append(
                    f"Column '{col_info['column']}' has {col_info['outlier_pct']:.1f}% outliers "
                    f"(IQR method) — consider capping or investigation."
                )
            if abs(col_info["skewness"]) > 2:
                direction = "right" if col_info["skewness"] > 0 else "left"
                insights.append(
                    f"Column '{col_info['column']}' is strongly {direction}-skewed "
                    f"(skewness={col_info['skewness']:.2f}) — log transform may help."
                )

        # Categorical columns
        for col_info in report["categorical_analysis"]:
            if col_info["is_likely_id"]:
                insights.append(
                    f"Column '{col_info['column']}' appears to be a unique identifier (all values unique)."
                )
            if col_info["most_frequent_pct"] > 80:
                insights.append(
                    f"Column '{col_info['column']}' is dominated by '{col_info['most_frequent']}' "
                    f"({col_info['most_frequent_pct']:.1f}% of rows) — low variance."
                )

        # Correlations
        if corr.get("available") and corr.get("high_correlation_pairs"):
            top = corr["high_correlation_pairs"][0]
            insights.append(
                f"Strongest correlation: '{top['col_a']}' vs '{top['col_b']}' "
                f"(r={top['correlation']:.3f})."
            )
            if corr["total_high_corr_pairs"] > 3:
                insights.append(
                    f"{corr['total_high_corr_pairs']} highly correlated column pairs found — "
                    "consider dimensionality reduction."
                )

        # Temporal
        temporal = report["temporal_analysis"]
        if temporal.get("available"):
            for ta in temporal.get("analyses", []):
                insights.append(
                    f"Column '{ta['column']}' spans {ta['date_range_days']} days "
                    f"({ta['min_date'][:10]} to {ta['max_date'][:10]})."
                )
                if ta["has_gaps"]:
                    insights.append(
                        f"Column '{ta['column']}' has irregular date gaps — time series analysis may be unreliable."
                    )

        return insights

    def _generate_recommendations(self, report: Dict[str, Any], df: pd.DataFrame) -> List[str]:
        """Auto-generate data quality recommendations"""
        recs = []
        missing = report["missing_values"]
        dupes = report["duplicate_analysis"]

        if missing["total_missing"] > 0:
            heavy = [c for c in missing["columns_with_missing"] if c["missing_pct"] > 50]
            if heavy:
                cols = ", ".join(f"'{c['column']}'" for c in heavy)
                recs.append(f"Consider dropping columns with >50% missing data: {cols}")
            moderate = [c for c in missing["columns_with_missing"] if 5 < c["missing_pct"] <= 50]
            if moderate:
                recs.append(
                    f"Impute moderate missing data in: "
                    + ", ".join(f"'{c['column']}'" for c in moderate)
                )

        if dupes["total_duplicates"] > 0:
            recs.append(
                f"Remove {dupes['total_duplicates']:,} duplicate rows before analysis."
            )

        for col_info in report["numeric_analysis"]:
            if abs(col_info["skewness"]) > 2 and col_info["min"] >= 0:
                recs.append(
                    f"Apply log1p transform to '{col_info['column']}' to reduce skewness."
                )
            if col_info["outlier_pct"] > 15:
                recs.append(
                    f"Cap outliers in '{col_info['column']}' using IQR fencing."
                )

        corr = report["correlation_analysis"]
        if corr.get("available") and corr["total_high_corr_pairs"] > 3:
            recs.append(
                "Consider PCA or feature selection to address multicollinearity."
            )

        for col_info in report["categorical_analysis"]:
            if col_info["is_likely_id"]:
                recs.append(
                    f"Exclude '{col_info['column']}' from ML features — it appears to be a row identifier."
                )

        if not recs:
            recs.append("The dataset appears to be in good shape — no critical data quality issues detected.")

        return recs

    # ------------------------------------------------------------------
    #  Report formatting
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        """Format the EDA report as Markdown"""
        if not self.results:
            return "No EDA results available. Run `run_eda()` first."

        r = self.results
        ov = r["overview"]
        lines = [
            f"# Automatic EDA Report: {r['dataset_name']}",
            "",
            "## Overview",
            f"- **Rows**: {ov['rows']:,}",
            f"- **Columns**: {ov['columns']}",
            f"- **Memory**: {ov['memory_mb']} MB",
            f"- **Numeric columns**: {len(ov['numeric_columns'])}",
            f"- **Categorical columns**: {len(ov['categorical_columns'])}",
            f"- **Datetime columns**: {len(ov['datetime_columns'])}",
            "",
            "## Key Insights",
        ]

        for insight in r["insights"]:
            lines.append(f"- {insight}")

        lines += ["", "## Recommendations"]
        for rec in r["recommendations"]:
            lines.append(f"- {rec}")

        # Missing values
        mv = r["missing_values"]
        lines += [
            "",
            "## Missing Values",
            f"- Total missing: {mv['total_missing']:,} ({mv['total_missing_pct']:.1f}%)",
            f"- Complete rows: {mv['complete_rows']:,} ({mv['complete_rows_pct']:.1f}%)",
        ]

        # Top numeric stats
        if r["numeric_analysis"]:
            lines += ["", "## Numeric Column Summary", "| Column | Mean | Std | Min | Max | Outliers% | Skewness |", "|--------|------|-----|-----|-----|-----------|----------|"]
            for c in r["numeric_analysis"][:15]:
                lines.append(
                    f"| {c['column']} | {c['mean']:.2f} | {c['std']:.2f} | "
                    f"{c['min']:.2f} | {c['max']:.2f} | {c['outlier_pct']:.1f}% | {c['skewness']:.2f} |"
                )

        # Correlations
        corr = r["correlation_analysis"]
        if corr.get("available") and corr["high_correlation_pairs"]:
            lines += ["", "## High Correlation Pairs", "| Column A | Column B | Correlation | Strength |", "|----------|----------|-------------|----------|"]
            for p in corr["high_correlation_pairs"][:8]:
                lines.append(f"| {p['col_a']} | {p['col_b']} | {p['correlation']:.3f} | {p['strength']} |")

        return "\n".join(lines)
