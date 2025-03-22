"""
Anomaly detection module using Isolation Forest algorithm.
Detects abnormal behavior in service metrics.
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime
import logging
import pickle
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest

logger = logging.getLogger('cloud-monitor.ml')

class AnomalyDetector:
    """
    Anomaly detection using Isolation Forest algorithm.
    
    Handles:
    - Training models for each service/metric combination
    - Detecting anomalies in new data
    - Calculating anomaly severity
    - MLflow experiment tracking
    """
    
    def __init__(self, ml_config, experiment_id):
        """
        Initialize the anomaly detector.
        
        Args:
            ml_config (dict): ML configuration parameters
            experiment_id (str): MLflow experiment ID
        """
        self.models = {}
        self.training_data = {}
        self.ml_config = ml_config
        self.experiment_id = experiment_id
        self.if_params = ml_config['isolation_forest']
        self.severity_thresholds = ml_config['detection']['severity_thresholds']
        self.run_history = []
        
        logger.info("Initialized anomaly detector with Isolation Forest")

    def safe_mlflow_tracking(func):
        """Decorator to safely wrap MLflow tracking code."""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"MLflow tracking error (continuing anyway): {str(e)}")
                return None
        return wrapper

    # Then apply this decorator to functions that use MLflow
    @safe_mlflow_tracking
    
    def train(self, data):
        """
        Train isolation forest models for each service/metric combination.
        
        Args:
            data (list): List of metric data points
        
        Returns:
            dict: Trained models
        """
        # Convert list to DataFrame for easier processing
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        # Start MLflow run for tracking
        with mlflow.start_run(experiment_id=self.experiment_id, run_name=f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
            mlflow.log_param("algorithm", "isolation_forest")
            mlflow.log_param("contamination", self.if_params['contamination'])
            mlflow.log_param("n_estimators", self.if_params['n_estimators'])
            mlflow.log_param("data_points", len(df))
            
            models_trained = 0
            services_trained = set()
            metrics_trained = set()
            
            # Group data by service and metric
            for (service, metric), group in df.groupby(['service', 'metric']):
                # Create model directories if they don't exist
                service_dir = os.path.join('models', service)
                os.makedirs(service_dir, exist_ok=True)
                
                # Only train if we have enough data
                if len(group) < 10:
                    logger.debug(f"Skipping {service}/{metric}: insufficient data ({len(group)} samples)")
                    continue
                
                # Initialize model containers if needed
                if service not in self.models:
                    self.models[service] = {}
                    self.training_data[service] = {}
                
                # Get values for this service and metric
                values = group['value'].values.reshape(-1, 1)
                
                # Log data statistics
                mlflow.log_metrics({
                    f"{service}_{metric}_mean": float(np.mean(values)),
                    f"{service}_{metric}_std": float(np.std(values)),
                    f"{service}_{metric}_min": float(np.min(values)),
                    f"{service}_{metric}_max": float(np.max(values))
                })
                
                # Store training data
                self.training_data[service][metric] = values
                
                # Train isolation forest model
                model = IsolationForest(
                    contamination=self.if_params['contamination'],
                    n_estimators=self.if_params['n_estimators'],
                    random_state=self.if_params['random_state']
                )
                model.fit(values)
                self.models[service][metric] = model
                
                # Save model file
                model_path = os.path.join(service_dir, f"{metric}_model.pkl")
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                
                # Log model with MLflow
                mlflow.log_artifact(model_path)
                models_trained += 1
                services_trained.add(service)
                metrics_trained.add(metric)
            
            # Log summary metrics
            mlflow.log_metric("models_trained", models_trained)
            mlflow.log_metric("services_trained", len(services_trained))
            mlflow.log_metric("metrics_trained", len(metrics_trained))
            
            # Store run ID in history
            self.run_history.append(run.info.run_id)
            
            logger.info(f"Trained {models_trained} anomaly detection models, run_id: {run.info.run_id}")
            
            return self.models
    
    def detect(self, data):
        """
        Detect anomalies in the new metrics data.
        
        Args:
            data (list): List of new metric data points
        
        Returns:
            list: Detected anomalies with severity
        """
        # Convert list to DataFrame for easier processing
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        # Start MLflow run for tracking
        with mlflow.start_run(experiment_id=self.experiment_id, run_name=f"detect_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
            detected_anomalies = []
            total_predictions = 0
            total_anomalies = 0
            
            # Process each service and metric
            for service in self.models:
                for metric in self.models[service]:
                    # Check if we have data for this service/metric
                    metric_data = df[(df['service'] == service) & (df['metric'] == metric)]
                    if metric_data.empty:
                        continue
                    
                    # Get the latest value
                    latest_row = metric_data.iloc[-1]
                    latest_value = latest_row['value']
                    latest_timestamp = latest_row['timestamp']
                    
                    # Predict if anomaly
                    try:
                        prediction = self.models[service][metric].predict([[latest_value]])[0]
                        total_predictions += 1
                        
                        if prediction == -1:  # Isolation forest marks anomalies as -1
                            total_anomalies += 1
                            
                            # Calculate severity based on deviation
                            severity = self._calculate_severity(service, metric, latest_value)
                            
                            # Create anomaly record
                            anomaly = {
                                'timestamp': latest_timestamp,
                                'service': service,
                                'metric': metric,
                                'value': float(latest_value),  # Convert numpy types to native Python
                                'severity': severity
                            }
                            
                            detected_anomalies.append(anomaly)
                            logger.info(f"Detected {severity} anomaly: {service}/{metric} = {latest_value:.2f}")
                    except Exception as e:
                        logger.error(f"Error predicting anomaly for {service}/{metric}: {str(e)}")
            
            # Log metrics
            if total_predictions > 0:
                mlflow.log_metrics({
                    "total_predictions": total_predictions,
                    "total_anomalies": total_anomalies,
                    "anomaly_rate": total_anomalies / total_predictions
                })
            
            return detected_anomalies
    
    def _calculate_severity(self, service, metric, value):
        """
        Calculate severity of anomaly based on deviation from training data.
        
        Args:
            service (str): Service name
            metric (str): Metric name
            value (float): Current metric value
        
        Returns:
            str: Severity level ('low', 'medium', 'high')
        """
        if service not in self.training_data or metric not in self.training_data[service]:
            return "medium"
            
        # Get training values for this service/metric
        training_values = self.training_data[service][metric].flatten()
        mean_value = np.mean(training_values)
        std_value = np.std(training_values)
        
        # Calculate z-score (how many standard deviations from mean)
        if std_value == 0:
            z_score = 0
        else:
            z_score = abs((value - mean_value) / std_value)
        
        # Determine severity based on configured thresholds
        if z_score > self.severity_thresholds['high']:
            return "high"
        elif z_score > self.severity_thresholds['medium']:
            return "medium"
        else:
            return "low"