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
from scipy import stats
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
        
        # Detect correlation analysis
        if any(word in question_lower for word in ['correlation', 'relationship', 'correlate', 'correlated']):
            return {
                "task": "correlation_analysis",
                "method": "ML",
                "reason": "Question asks for correlation analysis"
            }
        
        # Detect statistical analysis
        if any(word in question_lower for word in ['statistics', 'statistical', 'distribution', 'analyze data']):
            return {
                "task": "statistical_analysis",
                "method": "ML",
                "reason": "Question asks for statistical analysis"
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
    #  Correlation Analysis
    # ==================================================================
    
    def analyze_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform correlation analysis on numeric columns.
        
        Args:
            df: Input DataFrame
        
        Returns:
            Correlation analysis results
        """
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) < 2:
                return {
                    "success": False,
                    "error": "Need at least 2 numeric columns for correlation analysis",
                    "message": "Not enough numeric columns"
                }
            
            # Calculate correlation matrix
            corr_matrix = df[numeric_cols].corr()
            
            # Find highly correlated pairs
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:  # High correlation threshold
                        high_corr_pairs.append({
                            "feature1": corr_matrix.columns[i],
                            "feature2": corr_matrix.columns[j],
                            "correlation": corr_value
                        })
            
            # Sort by absolute correlation
            high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            return {
                "success": True,
                "task": "correlation_analysis",
                "correlation_matrix": corr_matrix.to_dict(),
                "high_correlations": high_corr_pairs[:10],  # Top 10
                "numeric_columns": numeric_cols.tolist(),
                "insights": [
                    f"Analyzed {len(numeric_cols)} numeric columns",
                    f"Found {len(high_corr_pairs)} highly correlated pairs (|r| > 0.7)",
                    f"Strongest correlation: {high_corr_pairs[0]['feature1']} <-> {high_corr_pairs[0]['feature2']} ({high_corr_pairs[0]['correlation']:.3f})" if high_corr_pairs else "No strong correlations found"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Correlation analysis failed: {str(e)}"
            }
    
    # ==================================================================
    #  Statistical Analysis
    # ==================================================================
    
    def perform_statistical_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive statistical analysis.
        
        Args:
            df: Input DataFrame
        
        Returns:
            Statistical analysis results
        """
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                return {
                    "success": False,
                    "error": "No numeric columns found",
                    "message": "Statistical analysis requires numeric data"
                }
            
            stats_results = {}
            
            for col in numeric_cols:
                col_data = df[col].dropna()
                
                # Basic statistics
                stats_results[col] = {
                    "count": len(col_data),
                    "mean": col_data.mean(),
                    "median": col_data.median(),
                    "std": col_data.std(),
                    "min": col_data.min(),
                    "max": col_data.max(),
                    "q25": col_data.quantile(0.25),
                    "q75": col_data.quantile(0.75),
                    "skewness": stats.skew(col_data),
                    "kurtosis": stats.kurtosis(col_data)
                }
            
            # Correlation with other columns
            if len(numeric_cols) > 1:
                corr_result = self.analyze_correlations(df)
                stats_results["correlations"] = corr_result.get("high_correlations", [])
            
            return {
                "success": True,
                "task": "statistical_analysis",
                "statistics": stats_results,
                "numeric_columns": numeric_cols.tolist(),
                "insights": [
                    f"Analyzed {len(numeric_cols)} numeric columns",
                    f"Skewness and kurtosis calculated for all columns",
                    f"Correlation analysis included"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Statistical analysis failed: {str(e)}"
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
        elif task == 'correlation_analysis':
            return self.analyze_correlations(df)
        elif task == 'statistical_analysis':
            return self.perform_statistical_analysis(df)
        else:
            return {
                "success": False,
                "error": f"Unsupported task: {task}",
                "message": f"Task {task} is not yet implemented"
            }
    
    # ==================================================================
    #  ML Visualization Generation
    # ==================================================================
    
    def generate_ml_visualization(
        self,
        task: str,
        results: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate ML-specific visualization data.
        
        Args:
            task: ML task type
            results: ML analysis results
            df: Input DataFrame
        
        Returns:
            Visualization data for plotting
        """
        try:
            viz_data = {
                "task": task,
                "chart_type": None,
                "data": None,
                "layout": None
            }
            
            if task == "regression":
                # Actual vs Predicted scatter plot
                actual = results.get("actual", [])
                predicted = results.get("predictions", [])
                viz_data["chart_type"] = "scatter"
                viz_data["data"] = pd.DataFrame({
                    "actual": actual,
                    "predicted": predicted
                })
                viz_data["layout"] = {
                    "title": "Actual vs Predicted",
                    "xaxis": {"title": "Actual"},
                    "yaxis": {"title": "Predicted"}
                }
            
            elif task == "classification":
                # Confusion matrix heatmap
                if results.get("predictions") and results.get("actual"):
                    viz_data["chart_type"] = "heatmap"
                    cm = confusion_matrix(results["actual"], results["predictions"])
                    viz_data["data"] = pd.DataFrame(cm)
                    viz_data["layout"] = {
                        "title": "Confusion Matrix",
                        "xaxis": {"title": "Predicted"},
                        "yaxis": {"title": "Actual"}
                    }
            
            elif task == "clustering":
                # Cluster scatter plot (if 2-3 features)
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) >= 2:
                    cluster_labels = results.get("labels", [])
                    df_viz = df[numeric_cols[:2]].copy()
                    df_viz["cluster"] = cluster_labels
                    viz_data["chart_type"] = "scatter"
                    viz_data["data"] = df_viz
                    viz_data["layout"] = {
                        "title": "Cluster Visualization",
                        "xaxis": {"title": numeric_cols[0]},
                        "yaxis": {"title": numeric_cols[1]}
                    }
            
            elif task == "anomaly_detection":
                # Time series with anomalies highlighted
                viz_data["chart_type"] = "scatter"
                df_viz = df.copy()
                df_viz["is_anomaly"] = results.get("anomaly_indices", [0] * len(df))
                viz_data["data"] = df_viz
                viz_data["layout"] = {
                    "title": "Anomaly Detection",
                    "xaxis": {"title": "Index"},
                    "yaxis": {"title": "Value"}
                }
            
            elif task == "forecasting":
                # Time series with forecast
                historical = results.get("historical", [])
                forecast = results.get("forecast", [])
                combined = historical + forecast
                labels = list(range(len(historical))) + list(range(len(historical), len(combined)))
                viz_data["chart_type"] = "line"
                viz_data["data"] = pd.DataFrame({
                    "index": labels,
                    "value": combined,
                    "type": ["historical"] * len(historical) + ["forecast"] * len(forecast)
                })
                viz_data["layout"] = {
                    "title": "Time Series Forecast",
                    "xaxis": {"title": "Period"},
                    "yaxis": {"title": "Value"}
                }
            
            elif task == "correlation_analysis":
                # Correlation heatmap
                corr_matrix = results.get("correlation_matrix", {})
                if corr_matrix:
                    viz_data["chart_type"] = "heatmap"
                    viz_data["data"] = pd.DataFrame(corr_matrix)
                    viz_data["layout"] = {
                        "title": "Correlation Matrix"
                    }
            
            return {
                "success": True,
                "visualization": viz_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Visualization generation failed: {str(e)}"
            }
    
    # ==================================================================
    #  ML Report Generation
    # ==================================================================
    
    def generate_ml_report(
        self,
        question: str,
        task: str,
        results: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate ML-specific report sections.
        
        Args:
            question: User's question
            task: ML task type
            results: ML analysis results
            df: Input DataFrame
        
        Returns:
            ML report sections
        """
        try:
            report_sections = {
                "problem_definition": f"Analysis question: {question}",
                "task_type": task,
                "dataset_info": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist()
                },
                "method_used": results.get("method", "auto"),
                "model_used": results.get("ml_model", "RandomForest"),
                "evaluation_metrics": results.get("metrics", {}),
                "predictions": results.get("predictions", [])[:10],  # First 10 predictions
                "key_findings": results.get("insights", []),
                "feature_importance": results.get("feature_importance", {})
            }
            
            # Add task-specific sections
            if task == "regression":
                report_sections["model_performance"] = {
                    "r2_score": results.get("r2"),
                    "mse": results.get("mse"),
                    "interpretation": f"Model explains {results.get('r2', 0) * 100:.1f}% of variance"
                }
            elif task == "classification":
                report_sections["model_performance"] = {
                    "accuracy": results.get("accuracy"),
                    "precision": results.get("precision"),
                    "recall": results.get("recall"),
                    "f1_score": results.get("f1")
                }
            elif task == "clustering":
                report_sections["cluster_analysis"] = {
                    "n_clusters": results.get("n_clusters"),
                    "silhouette_score": results.get("silhouette_score"),
                    "cluster_stats": results.get("cluster_stats", {})
                }
            elif task == "anomaly_detection":
                report_sections["anomaly_analysis"] = {
                    "n_anomalies": results.get("n_anomalies"),
                    "anomaly_percentage": results.get("anomaly_percentage"),
                    "method": results.get("method")
                }
            elif task == "forecasting":
                report_sections["forecast_analysis"] = {
                    "periods": results.get("periods"),
                    "trend": results.get("trend"),
                    "forecast_values": results.get("forecast", [])
                }
            
            return {
                "success": True,
                "report": report_sections
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Report generation failed: {str(e)}"
            }
    
    def close(self):
        """Cleanup resources"""
        self.model = None
        self.scaler = None
        self.label_encoder = None
