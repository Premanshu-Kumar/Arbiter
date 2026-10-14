"""
ML Analytics Agent - Phase 9

Advanced analytics and machine learning agent for:
- Predictive analytics
- Time-series forecasting
- Anomaly detection
- Regression
- Classification
- Clustering
- Feature engineering
- Model validation
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import (
    mean_squared_error, r2_score, accuracy_score, 
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, silhouette_score
)
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
import warnings
warnings.filterwarnings('ignore')


class MLAnalyticsAgent:
    """
    Advanced analytics and machine learning agent.
    
    Supports:
    - Predictive analytics (regression, classification)
    - Time-series forecasting
    - Anomaly detection
    - Clustering
    - Feature engineering
    - Model validation
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.target_name = None
        self.task_type = None
        self.model_metrics = {}
    
    # ==================================================================
    #  Task Detection
    # ==================================================================
    
    def detect_task_type(self, question: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect the type of ML task based on question and data.
        
        Args:
            question: User's natural language question
            df: Input DataFrame
        
        Returns:
            Task type and parameters
        """
        question_lower = question.lower()
        
        # Detect forecasting
        if any(word in question_lower for word in ['forecast', 'predict next', 'future', 'trend']):
            return {
                "task": "forecasting",
                "method": "ML",
                "requires_time_series": True,
                "reason": "Question asks for forecasting"
            }
        
        # Detect anomaly detection
        if any(word in question_lower for word in ['anomaly', 'unusual', 'outlier', 'strange', 'abnormal']):
            return {
                "task": "anomaly_detection",
                "method": "ML",
                "reason": "Question asks for anomaly detection"
            }
        
        # Detect clustering
        if any(word in question_lower for word in ['cluster', 'segment', 'group', 'categorize']):
            return {
                "task": "clustering",
                "method": "ML",
                "reason": "Question asks for clustering/segmentation"
            }
        
        # Detect classification
        if any(word in question_lower for word in ['classify', 'churn', 'category', 'class', 'yes no']):
            return {
                "task": "classification",
                "method": "ML",
                "reason": "Question asks for classification"
            }
        
        # Detect regression
        if any(word in question_lower for word in ['predict', 'estimate', 'price', 'value', 'amount']):
            return {
                "task": "regression",
                "method": "ML",
                "reason": "Question asks for prediction/regression"
            }
        
        # Default to regression for prediction questions
        if 'predict' in question_lower:
            return {
                "task": "regression",
                "method": "ML",
                "reason": "Default to regression for prediction"
            }
        
        return {
            "task": "unknown",
            "method": "unknown",
            "reason": "Could not determine task type"
        }
    
    # ==================================================================
    #  Feature Engineering
    # ==================================================================
    
    def engineer_features(self, df: pd.DataFrame, task: str) -> pd.DataFrame:
        """
        Perform feature engineering for ML tasks.
        
        Args:
            df: Input DataFrame
            task: ML task type
        
        Returns:
            DataFrame with engineered features
        """
        df_engineered = df.copy()
        
        # Handle missing values
        for col in df_engineered.columns:
            if df_engineered[col].dtype in ['int64', 'float64']:
                df_engineered[col].fillna(df_engineered[col].median(), inplace=True)
            else:
                df_engineered[col].fillna(df_engineered[col].mode()[0] if not df_engineered[col].mode().empty else 'unknown', inplace=True)
        
        # Encode categorical variables
        categorical_cols = df_engineered.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df_engineered[col] = self.label_encoder.fit_transform(df_engineered[col].astype(str))
        
        # Create interaction features for regression/classification
        if task in ['regression', 'classification']:
            numeric_cols = df_engineered.select_dtypes(include=['number']).columns
            if len(numeric_cols) >= 2:
                # Add product of first two numeric columns
                df_engineered[f'{numeric_cols[0]}_x_{numeric_cols[1]}'] = (
                    df_engineered[numeric_cols[0]] * df_engineered[numeric_cols[1]]
                )
        
        return df_engineered
    
    # ==================================================================
    #  Regression
    # ==================================================================
    
    def perform_regression(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Perform regression analysis.
        
        Args:
            df: Input DataFrame
            target_column: Name of target column
            test_size: Test set size ratio
        
        Returns:
            Regression results
        """
        try:
            # Feature engineering
            df_engineered = self.engineer_features(df, 'regression')
            
            # Prepare features and target
            X = df_engineered.drop(columns=[target_column])
            y = df_engineered[target_column]
            
            self.feature_names = X.columns.tolist()
            self.target_name = target_column
            self.task_type = 'regression'
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model.fit(X_train_scaled, y_train)
            
            # Predictions
            y_pred = self.model.predict(X_test_scaled)
            
            # Metrics
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            self.model_metrics = {
                'mse': mse,
                'r2': r2,
                'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
            }
            
            return {
                "success": True,
                "task": "regression",
                "target": target_column,
                "metrics": self.model_metrics,
                "predictions": y_pred.tolist(),
                "actual": y_test.tolist(),
                "mse": mse,
                "r2": r2,
                "feature_importance": self.model_metrics['feature_importance'],
                "insights": [
                    f"Model R² score: {r2:.3f}",
                    f"Mean squared error: {mse:.2f}",
                    f"Top feature: {max(self.model_metrics['feature_importance'], key=self.model_metrics['feature_importance'].get)}"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Regression failed: {str(e)}"
            }
    
    # ==================================================================
    #  Classification
    # ==================================================================
    
    def perform_classification(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Perform classification analysis.
        
        Args:
            df: Input DataFrame
            target_column: Name of target column
            test_size: Test set size ratio
        
        Returns:
            Classification results
        """
        try:
            # Feature engineering
            df_engineered = self.engineer_features(df, 'classification')
            
            # Prepare features and target
            X = df_engineered.drop(columns=[target_column])
            y = df_engineered[target_column]
            
            self.feature_names = X.columns.tolist()
            self.target_name = target_column
            self.task_type = 'classification'
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model.fit(X_train_scaled, y_train)
            
            # Predictions
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)
            
            # Metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            self.model_metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
            }
            
            return {
                "success": True,
                "task": "classification",
                "target": target_column,
                "metrics": self.model_metrics,
                "predictions": y_pred.tolist(),
                "actual": y_test.tolist(),
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "feature_importance": self.model_metrics['feature_importance'],
                "insights": [
                    f"Model accuracy: {accuracy:.3f}",
                    f"Precision: {precision:.3f}",
                    f"Recall: {recall:.3f}",
                    f"F1 score: {f1:.3f}"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Classification failed: {str(e)}"
            }
    
    # ==================================================================
    #  Clustering
    # ==================================================================
    
    def perform_clustering(
        self,
        df: pd.DataFrame,
        n_clusters: Optional[int] = None,
        method: str = "kmeans"
    ) -> Dict[str, Any]:
        """
        Perform clustering analysis.
        
        Args:
            df: Input DataFrame
            n_clusters: Number of clusters (auto-detect if None)
            method: Clustering method (kmeans, dbscan)
        
        Returns:
            Clustering results
        """
        try:
            # Feature engineering
            df_engineered = self.engineer_features(df, 'clustering')
            
            # Use only numeric columns
            numeric_cols = df_engineered.select_dtypes(include=['number']).columns
            X = df_engineered[numeric_cols]
            
            self.feature_names = X.columns.tolist()
            self.task_type = 'clustering'
            
            # Auto-detect number of clusters if not specified
            if n_clusters is None and method == "kmeans":
                n_clusters = min(5, len(df) // 10)  # Default to 5 or 10% of data
            
            # Perform clustering
            if method == "kmeans":
                self.model = KMeans(n_clusters=n_clusters, random_state=42)
                labels = self.model.fit_predict(X)
                score = silhouette_score(X, labels) if len(set(labels)) > 1 else 0
            elif method == "dbscan":
                self.model = DBSCAN(eps=0.5, min_samples=5)
                labels = self.model.fit_predict(X)
                score = silhouette_score(X, labels) if len(set(labels)) > 1 else 0
            else:
                raise ValueError(f"Unknown clustering method: {method}")
            
            # Add cluster labels to dataframe
            df_with_clusters = df.copy()
            df_with_clusters['cluster'] = labels
            
            # Cluster statistics
            cluster_stats = {}
            for cluster_id in set(labels):
                cluster_data = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
                cluster_stats[f"cluster_{cluster_id}"] = {
                    "size": len(cluster_data),
                    "percentage": (len(cluster_data) / len(df)) * 100
                }
            
            return {
                "success": True,
                "task": "clustering",
                "method": method,
                "n_clusters": len(set(labels)),
                "labels": labels.tolist(),
                "silhouette_score": score,
                "cluster_stats": cluster_stats,
                "data_with_clusters": df_with_clusters,
                "insights": [
                    f"Found {len(set(labels))} clusters",
                    f"Silhouette score: {score:.3f}",
                    f"Largest cluster: {max(cluster_stats, key=lambda k: cluster_stats[k]['size'])}"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Clustering failed: {str(e)}"
            }
    
    # ==================================================================
    #  Anomaly Detection
    # ==================================================================
    
    def detect_anomalies(
        self,
        df: pd.DataFrame,
        method: str = "isolation_forest",
        contamination: float = 0.1
    ) -> Dict[str, Any]:
        """
        Detect anomalies in the data.
        
        Args:
            df: Input DataFrame
            method: Detection method (isolation_forest, lof)
            contamination: Expected proportion of outliers
        
        Returns:
            Anomaly detection results
        """
        try:
            # Feature engineering
            df_engineered = self.engineer_features(df, 'anomaly_detection')
            
            # Use only numeric columns
            numeric_cols = df_engineered.select_dtypes(include=['number']).columns
            X = df_engineered[numeric_cols]
            
            self.feature_names = X.columns.tolist()
            self.task_type = 'anomaly_detection'
            
            # Perform anomaly detection
            if method == "isolation_forest":
                self.model = IsolationForest(contamination=contamination, random_state=42)
                anomalies = self.model.fit_predict(X)
            elif method == "lof":
                self.model = LocalOutlierFactor(contamination=contamination)
                anomalies = self.model.fit_predict(X)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Anomalies are marked as -1
            anomaly_mask = anomalies == -1
            n_anomalies = anomaly_mask.sum()
            
            # Add anomaly labels to dataframe
            df_with_anomalies = df.copy()
            df_with_anomalies['is_anomaly'] = anomaly_mask
            
            # Anomaly statistics
            anomaly_data = df_with_anomalies[df_with_anomalies['is_anomaly']]
            
            return {
                "success": True,
                "task": "anomaly_detection",
                "method": method,
                "n_anomalies": int(n_anomalies),
                "anomaly_percentage": (n_anomalies / len(df)) * 100,
                "anomaly_indices": np.where(anomaly_mask)[0].tolist(),
                "data_with_anomalies": df_with_anomalies,
                "anomaly_data": anomaly_data,
                "insights": [
                    f"Found {n_anomalies} anomalies ({(n_anomalies / len(df)) * 100:.1f}%)",
                    f"Method: {method}",
                    f"Contamination threshold: {contamination}"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Anomaly detection failed: {str(e)}"
            }
    
    # ==================================================================
    #  Time-Series Forecasting
    # ==================================================================
    
    def perform_forecasting(
        self,
        df: pd.DataFrame,
        target_column: str,
        time_column: Optional[str] = None,
        periods: int = 5
    ) -> Dict[str, Any]:
        """
        Perform time-series forecasting.
        
        Args:
            df: Input DataFrame
            target_column: Name of target column
            time_column: Name of time column (optional)
            periods: Number of periods to forecast
        
        Returns:
            Forecasting results
        """
        try:
            # Simple moving average forecast (baseline)
            if time_column and time_column in df.columns:
                df_sorted = df.sort_values(time_column)
            else:
                df_sorted = df.copy()
            
            y = df_sorted[target_column].values
            
            # Simple forecast using last values
            last_values = y[-periods:] if len(y) >= periods else y
            forecast = np.mean(last_values) + np.random.normal(0, np.std(y) * 0.1, periods)
            
            # Trend (simple linear)
            if len(y) >= 2:
                trend = (y[-1] - y[0]) / len(y)
                forecast_trend = [y[-1] + trend * (i + 1) for i in range(periods)]
            else:
                forecast_trend = forecast
            
            return {
                "success": True,
                "task": "forecasting",
                "target": target_column,
                "periods": periods,
                "forecast": forecast_trend,
                "historical": y.tolist(),
                "trend": trend if len(y) >= 2 else 0,
                "insights": [
                    f"Forecast for next {periods} periods",
                    f"Last value: {y[-1]:.2f}",
                    f"Average forecast: {np.mean(forecast_trend):.2f}",
                    f"Trend: {trend if len(y) >= 2 else 0:.2f} per period"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Forecasting failed: {str(e)}"
            }
    
    # ==================================================================
    #  Automated ML Pipeline
    # ==================================================================
    
    def run_auto_ml(
        self,
        question: str,
        df: pd.DataFrame,
        target_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically detect task and run appropriate ML analysis.
        
        Args:
            question: User's natural language question
            df: Input DataFrame
            target_column: Target column (optional, auto-detected)
        
        Returns:
            ML analysis results
        """
        # Detect task type
        task_info = self.detect_task_type(question, df)
        task = task_info.get('task', 'unknown')
        
        if task == 'unknown':
            return {
                "success": False,
                "error": "Could not determine ML task",
                "message": "Please specify the type of analysis (forecast, predict, cluster, etc.)"
            }
        
        # Auto-detect target column if not provided
        if target_column is None and task in ['regression', 'classification', 'forecasting']:
            # Try to detect target from question
            for col in df.columns:
                if col.lower() in question.lower():
                    target_column = col
                    break
            
            if target_column is None:
                # Use last column as default
                target_column = df.columns[-1]
        
        # Run appropriate analysis
        if task == 'regression':
            return self.perform_regression(df, target_column)
        elif task == 'classification':
            return self.perform_classification(df, target_column)
        elif task == 'clustering':
            return self.perform_clustering(df)
        elif task == 'anomaly_detection':
            return self.detect_anomalies(df)
        elif task == 'forecasting':
            return self.perform_forecasting(df, target_column)
        else:
            return {
                "success": False,
                "error": f"Unsupported task: {task}",
                "message": f"Task {task} is not yet implemented"
            }
    
    def close(self):
        """Cleanup resources"""
        self.model = None
        self.scaler = None
        self.label_encoder = None
