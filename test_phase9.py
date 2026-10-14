"""
Phase 9 - Advanced Analytics & ML Tests

Tests for:
- Predictive analytics (regression, classification)
- Time-series forecasting
- Anomaly detection
- Clustering
- Feature engineering
- Model validation
"""
import pandas as pd
import numpy as np
from agents.ml_analytics_agent import MLAnalyticsAgent


def test_regression():
    """Test regression analysis"""
    print("=" * 50)
    print("Testing Phase 9: Regression Analysis")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample data
    df = pd.DataFrame({
        "size": [1000, 1500, 2000, 2500, 3000, 1200, 1800, 2200, 2800, 3200],
        "bedrooms": [2, 3, 3, 4, 4, 2, 3, 4, 4, 5],
        "bathrooms": [1, 2, 2, 3, 3, 1, 2, 2, 3, 3],
        "age": [10, 5, 15, 8, 3, 12, 7, 9, 4, 2],
        "price": [200000, 350000, 400000, 500000, 600000, 220000, 380000, 480000, 550000, 650000]
    })
    
    print("\n📊 Testing regression...")
    result = ml_agent.perform_regression(df, "price")
    
    if result['success']:
        print(f"✅ Regression successful")
        print(f"   R² score: {result['r2']:.3f}")
        print(f"   MSE: {result['mse']:.2f}")
        print(f"   Top feature: {max(result['feature_importance'], key=result['feature_importance'].get)}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Regression failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Regression Tests Complete")
    print("=" * 50)


def test_classification():
    """Test classification analysis"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Classification Analysis")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample data
    df = pd.DataFrame({
        "age": [25, 30, 35, 40, 45, 28, 32, 38, 42, 48],
        "income": [50000, 60000, 70000, 80000, 90000, 55000, 65000, 75000, 85000, 95000],
        "spending": [2000, 2500, 3000, 3500, 4000, 2200, 2700, 3200, 3700, 4200],
        "churn": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0]
    })
    
    print("\n📊 Testing classification...")
    result = ml_agent.perform_classification(df, "churn")
    
    if result['success']:
        print(f"✅ Classification successful")
        print(f"   Accuracy: {result['accuracy']:.3f}")
        print(f"   Precision: {result['precision']:.3f}")
        print(f"   Recall: {result['recall']:.3f}")
        print(f"   F1 score: {result['f1']:.3f}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Classification failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Classification Tests Complete")
    print("=" * 50)


def test_clustering():
    """Test clustering analysis"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Clustering Analysis")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample data
    df = pd.DataFrame({
        "spending": [2000, 2500, 3000, 3500, 4000, 500, 800, 1200, 1500, 1800],
        "frequency": [10, 12, 15, 18, 20, 3, 5, 7, 9, 11],
        "recency": [5, 7, 10, 12, 15, 2, 4, 6, 8, 10]
    })
    
    print("\n📊 Testing clustering...")
    result = ml_agent.perform_clustering(df, n_clusters=3)
    
    if result['success']:
        print(f"✅ Clustering successful")
        print(f"   Number of clusters: {result['n_clusters']}")
        print(f"   Silhouette score: {result['silhouette_score']:.3f}")
        print(f"   Cluster stats: {result['cluster_stats']}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Clustering failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Clustering Tests Complete")
    print("=" * 50)


def test_anomaly_detection():
    """Test anomaly detection"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Anomaly Detection")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample data with anomalies
    np.random.seed(42)
    normal_data = np.random.normal(100, 10, 95)
    anomaly_data = np.array([200, 250, 300, 5, 10])  # Clear anomalies
    data = np.concatenate([normal_data, anomaly_data])
    
    df = pd.DataFrame({
        "value": data,
        "feature1": np.random.normal(50, 5, 100),
        "feature2": np.random.normal(30, 3, 100)
    })
    
    print("\n📊 Testing anomaly detection...")
    result = ml_agent.detect_anomalies(df, method="isolation_forest", contamination=0.05)
    
    if result['success']:
        print(f"✅ Anomaly detection successful")
        print(f"   Anomalies found: {result['n_anomalies']}")
        print(f"   Anomaly percentage: {result['anomaly_percentage']:.1f}%")
        print(f"   Method: {result['method']}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Anomaly detection failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Anomaly Detection Tests Complete")
    print("=" * 50)


def test_forecasting():
    """Test time-series forecasting"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Time-Series Forecasting")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample time-series data
    dates = pd.date_range(start='2023-01-01', periods=12, freq='M')
    values = [100, 110, 105, 120, 130, 125, 140, 150, 145, 160, 170, 165]
    
    df = pd.DataFrame({
        "date": dates,
        "revenue": values
    })
    
    print("\n📊 Testing forecasting...")
    result = ml_agent.perform_forecasting(df, "revenue", time_column="date", periods=6)
    
    if result['success']:
        print(f"✅ Forecasting successful")
        print(f"   Periods forecasted: {result['periods']}")
        print(f"   Last value: {result['historical'][-1]:.2f}")
        print(f"   Average forecast: {np.mean(result['forecast']):.2f}")
        print(f"   Trend: {result['trend']:.2f}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Forecasting failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Forecasting Tests Complete")
    print("=" * 50)


def test_task_detection():
    """Test ML task detection"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Task Detection")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    
    questions = [
        "Predict next month's revenue",
        "Forecast sales for the next 6 months",
        "Find unusual transactions",
        "Segment customers based on behavior",
        "Predict house price",
        "Classify customer churn"
    ]
    
    print("\n🔍 Testing task detection...")
    for question in questions:
        result = ml_agent.detect_task_type(question, df)
        print(f"   Question: '{question}'")
        print(f"   Detected task: {result['task']}")
        print(f"   Reason: {result['reason']}")
        print()
    
    ml_agent.close()
    
    print("=" * 50)
    print("✅ Task Detection Tests Complete")
    print("=" * 50)


def test_auto_ml():
    """Test automated ML pipeline"""
    print("\n" + "=" * 50)
    print("Testing Phase 9: Auto ML Pipeline")
    print("=" * 50)
    
    ml_agent = MLAnalyticsAgent()
    
    # Create sample data
    df = pd.DataFrame({
        "size": [1000, 1500, 2000, 2500, 3000],
        "bedrooms": [2, 3, 3, 4, 4],
        "price": [200000, 350000, 400000, 500000, 600000]
    })
    
    print("\n🤖 Testing auto ML...")
    result = ml_agent.run_auto_ml("Predict the price", df)
    
    if result['success']:
        print(f"✅ Auto ML successful")
        print(f"   Task: {result['task']}")
        print(f"   Metrics: {result.get('metrics', {})}")
        print(f"   Insights: {result['insights']}")
    else:
        print(f"❌ Auto ML failed: {result['error']}")
    
    ml_agent.close()
    
    print("\n" + "=" * 50)
    print("✅ Auto ML Tests Complete")
    print("=" * 50)


if __name__ == "__main__":
    test_regression()
    test_classification()
    test_clustering()
    test_anomaly_detection()
    test_forecasting()
    test_task_detection()
    test_auto_ml()
    
    print("\n" + "=" * 50)
    print("Phase 9 Advanced Analytics & ML Tests Complete")
    print("=" * 50)
