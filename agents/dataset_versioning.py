"""
Dataset Versioning — Phase 7

Tracks versions of uploaded datasets so users can compare, restore, and
audit changes over time. Versions are stored as Parquet snapshots in a
local versioning directory.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd
import json
import os
import hashlib
import shutil
from datetime import datetime


VERSIONS_DIR = os.path.join("data", ".versions")


class DatasetVersion:
    """Metadata for a single dataset version"""

    def __init__(
        self,
        version_id: str,
        dataset_name: str,
        timestamp: str,
        row_count: int,
        column_count: int,
        columns: List[str],
        source_file: str,
        description: str,
        checksum: str,
        parquet_path: str,
    ):
        self.version_id = version_id
        self.dataset_name = dataset_name
        self.timestamp = timestamp
        self.row_count = row_count
        self.column_count = column_count
        self.columns = columns
        self.source_file = source_file
        self.description = description
        self.checksum = checksum
        self.parquet_path = parquet_path

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetVersion":
        return cls(**d)


class DatasetVersionManager:
    """
    Manages versioned snapshots of datasets.

    Each named dataset has its own version history stored in:
        data/.versions/<dataset_name>/

    Each version contains:
        - metadata.json  (version metadata)
        - data.parquet   (snapshot of the DataFrame)
    """

    def __init__(self, versions_dir: str = VERSIONS_DIR):
        self.versions_dir = versions_dir
        os.makedirs(versions_dir, exist_ok=True)

    # ------------------------------------------------------------------
    #  Saving versions
    # ------------------------------------------------------------------

    def save_version(
        self,
        dataset_name: str,
        df: pd.DataFrame,
        source_file: str = "",
        description: str = "",
    ) -> DatasetVersion:
        """
        Save a new version snapshot of a dataset.

        Args:
            dataset_name: Logical name of the dataset
            df: Current DataFrame
            source_file: Original file path that produced this dataset
            description: Human-readable description of this version

        Returns:
            DatasetVersion metadata object
        """
        timestamp = datetime.utcnow().isoformat()
        checksum = self._compute_checksum(df)
        version_id = f"v{self._next_version_number(dataset_name):04d}"

        version_dir = os.path.join(self.versions_dir, dataset_name, version_id)
        os.makedirs(version_dir, exist_ok=True)

        parquet_path = os.path.join(version_dir, "data.parquet")
        df.to_parquet(parquet_path, index=False)

        version = DatasetVersion(
            version_id=version_id,
            dataset_name=dataset_name,
            timestamp=timestamp,
            row_count=len(df),
            column_count=len(df.columns),
            columns=df.columns.tolist(),
            source_file=source_file,
            description=description or f"Version {version_id}",
            checksum=checksum,
            parquet_path=parquet_path,
        )

        meta_path = os.path.join(version_dir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(version.to_dict(), f, indent=2)

        print(f"💾 Dataset '{dataset_name}' saved as {version_id}")
        return version

    # ------------------------------------------------------------------
    #  Loading versions
    # ------------------------------------------------------------------

    def load_version(self, dataset_name: str, version_id: str) -> Optional[pd.DataFrame]:
        """
        Load a specific version of a dataset.

        Args:
            dataset_name: Logical name of the dataset
            version_id: e.g. 'v0001'

        Returns:
            DataFrame or None if not found
        """
        version_dir = os.path.join(self.versions_dir, dataset_name, version_id)
        parquet_path = os.path.join(version_dir, "data.parquet")

        if not os.path.exists(parquet_path):
            print(f"Version {version_id} of '{dataset_name}' not found.")
            return None

        df = pd.read_parquet(parquet_path)
        print(f"📂 Loaded {dataset_name} {version_id}: {len(df):,} rows")
        return df

    def load_latest_version(self, dataset_name: str) -> Optional[pd.DataFrame]:
        """Load the most recent version of a dataset"""
        versions = self.list_versions(dataset_name)
        if not versions:
            return None
        latest = versions[-1]
        return self.load_version(dataset_name, latest.version_id)

    # ------------------------------------------------------------------
    #  Listing & metadata
    # ------------------------------------------------------------------

    def list_versions(self, dataset_name: str) -> List[DatasetVersion]:
        """List all versions for a dataset, oldest first"""
        dataset_dir = os.path.join(self.versions_dir, dataset_name)
        if not os.path.exists(dataset_dir):
            return []

        versions = []
        for version_id in sorted(os.listdir(dataset_dir)):
            meta_path = os.path.join(dataset_dir, version_id, "metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    data = json.load(f)
                versions.append(DatasetVersion.from_dict(data))

        return versions

    def list_all_datasets(self) -> List[str]:
        """List all dataset names that have at least one version"""
        if not os.path.exists(self.versions_dir):
            return []
        return [
            d
            for d in os.listdir(self.versions_dir)
            if os.path.isdir(os.path.join(self.versions_dir, d))
        ]

    def get_version_metadata(
        self, dataset_name: str, version_id: str
    ) -> Optional[DatasetVersion]:
        """Get metadata for a specific version without loading the data"""
        meta_path = os.path.join(
            self.versions_dir, dataset_name, version_id, "metadata.json"
        )
        if not os.path.exists(meta_path):
            return None
        with open(meta_path) as f:
            return DatasetVersion.from_dict(json.load(f))

    # ------------------------------------------------------------------
    #  Comparison
    # ------------------------------------------------------------------

    def compare_versions(
        self,
        dataset_name: str,
        version_id_a: str,
        version_id_b: str,
    ) -> Dict[str, Any]:
        """
        Compare two versions of a dataset.

        Returns a structured diff including:
        - Row/column count changes
        - New/removed columns
        - Numeric column value drift (mean, std)
        """
        meta_a = self.get_version_metadata(dataset_name, version_id_a)
        meta_b = self.get_version_metadata(dataset_name, version_id_b)

        if not meta_a or not meta_b:
            return {"error": "One or both versions not found"}

        df_a = self.load_version(dataset_name, version_id_a)
        df_b = self.load_version(dataset_name, version_id_b)

        if df_a is None or df_b is None:
            return {"error": "Could not load one or both version DataFrames"}

        cols_a = set(df_a.columns)
        cols_b = set(df_b.columns)

        added_cols = list(cols_b - cols_a)
        removed_cols = list(cols_a - cols_b)
        common_cols = list(cols_a & cols_b)

        numeric_drift = []
        for col in common_cols:
            if pd.api.types.is_numeric_dtype(df_a[col]) and pd.api.types.is_numeric_dtype(df_b[col]):
                mean_a = float(df_a[col].mean())
                mean_b = float(df_b[col].mean())
                std_a = float(df_a[col].std())
                std_b = float(df_b[col].std())
                drift = {
                    "column": col,
                    "mean_a": round(mean_a, 4),
                    "mean_b": round(mean_b, 4),
                    "mean_change_pct": round(
                        (mean_b - mean_a) / (abs(mean_a) + 1e-9) * 100, 2
                    ),
                    "std_a": round(std_a, 4),
                    "std_b": round(std_b, 4),
                }
                numeric_drift.append(drift)

        return {
            "dataset_name": dataset_name,
            "version_a": version_id_a,
            "version_b": version_id_b,
            "timestamp_a": meta_a.timestamp,
            "timestamp_b": meta_b.timestamp,
            "row_count_a": meta_a.row_count,
            "row_count_b": meta_b.row_count,
            "row_count_change": meta_b.row_count - meta_a.row_count,
            "column_count_a": meta_a.column_count,
            "column_count_b": meta_b.column_count,
            "added_columns": added_cols,
            "removed_columns": removed_cols,
            "common_columns": len(common_cols),
            "numeric_drift": numeric_drift,
            "schema_changed": bool(added_cols or removed_cols),
            "identical_checksums": meta_a.checksum == meta_b.checksum,
        }

    # ------------------------------------------------------------------
    #  Deletion
    # ------------------------------------------------------------------

    def delete_version(self, dataset_name: str, version_id: str) -> bool:
        """Delete a specific version snapshot"""
        version_dir = os.path.join(self.versions_dir, dataset_name, version_id)
        if os.path.exists(version_dir):
            shutil.rmtree(version_dir)
            print(f"Deleted {dataset_name} {version_id}")
            return True
        return False

    def delete_dataset_history(self, dataset_name: str) -> bool:
        """Delete all versions of a dataset"""
        dataset_dir = os.path.join(self.versions_dir, dataset_name)
        if os.path.exists(dataset_dir):
            shutil.rmtree(dataset_dir)
            print(f"Deleted all versions of '{dataset_name}'")
            return True
        return False

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _compute_checksum(self, df: pd.DataFrame) -> str:
        """Compute a hash checksum for a DataFrame's contents"""
        try:
            content = pd.util.hash_pandas_object(df, index=True).values.tobytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return hashlib.sha256(str(df.shape).encode()).hexdigest()[:16]

    def _next_version_number(self, dataset_name: str) -> int:
        """Return the next sequential version number"""
        existing = self.list_versions(dataset_name)
        return len(existing) + 1

    def to_dataframe(self, dataset_name: str) -> pd.DataFrame:
        """Return the version history of a dataset as a DataFrame"""
        versions = self.list_versions(dataset_name)
        if not versions:
            return pd.DataFrame()
        return pd.DataFrame([v.to_dict() for v in versions]).drop(
            columns=["parquet_path", "checksum"], errors="ignore"
        )
