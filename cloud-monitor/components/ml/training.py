"""
ML model training module.
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

logger = logging.getLogger('cloud-monitor.ml')

class ModelTrainer:
    """
    Trains ML models for anomaly detection.
    
    Features:
    - Automated training pipeline
    - Hyperparameter optimization
    - Model versioning and storage
    - MLflow integration
    """
    
    def __init__(self, models_dir, ml_config, experiment_id=None):
        """
        Initialize the model trainer.
        
        Args:
            models_dir (str): Directory for model storage
            ml_config (dict): ML configuration parameters
            experiment_id (str, optional): MLflow experiment ID
        """
        self.models_dir = models_dir
        self.ml_config = ml_config
        self.experiment_id = experiment_id
        self.isolation_forest_params = ml_config['isolation_forest']
        logger.info("Initialized model trainer")
    
    def train_model(self, data, service, metric, optimize=False):
        """
        Train a model for a specific service and metric.
        
        Args:
            data (list): Training data
            service (str): Service name
            metric (str): Metric name
            optimize (bool): Whether to optimize hyperparameters
            
        Returns:
            object: Trained model
        """
        # Create service directory if needed
        service_dir = os.path.join(self.models_dir, service)
        os.makedirs(service_dir, exist_ok=True)
        
        # Convert to DataFrame if needed
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        # Filter data for this service and metric
        service_data = df[(df['service'] == service) & (df['metric'] == metric)]
        
        if len(service_data) < 10:
            logger.warning(f"Insufficient data for {service}/{metric}: {len(service_data)} samples")
            return None
        
        # Extract values for training
        values = service_data['value'].values.reshape(-1, 1)
        
        # Train with MLflow tracking
        with mlflow.start_run(experiment_id=self.experiment_id,
                              run_name=f"train_{service}_{metric}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Log parameters
            mlflow.log_params({
                'service': service,
                'metric': metric,
                'num_samples': len(values),
                'timestamp': datetime.now().isoformat()
            })
            
            # Log data statistics
            mlflow.log_metrics({
                'data_mean': float(np.mean(values)),
                'data_std': float(np.std(values)),
                'data_min': float(np.min(values)),
                'data_max': float(np.max(values))
            })
            
            if optimize:
                # Hyperparameter optimization
                model, best_params = self._optimize_hyperparameters(values)
                mlflow.log_params(best_params)
            else:
                # Train with default parameters
                model = IsolationForest(
                    contamination=self.isolation_forest_params['contamination'],
                    n_estimators=self.isolation_forest_params['n_estimators'],
                    random_state=self.isolation_forest_params['random_state']
                )
                model.fit(values)
                
                mlflow.log_params({
                    'contamination': self.isolation_forest_params['contamination'],
                    'n_estimators': self.isolation_forest_params['n_estimators'],
                    'random_state': self.isolation_forest_params['random_state']
                })
            
            # Save model
            model_path = os.path.join(service_dir, f"{metric}_model.pkl")
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            
            # Log model artifact
            mlflow.log_artifact(model_path)
            
            logger.info(f"Trained model for {service}/{metric} with {len(values)} samples")
            
            return model
    
    def _optimize_hyperparameters(self, values):
        """
        Optimize hyperparameters for Isolation Forest.
        
        Args:
            values (array): Training data values
            
        Returns:
            tuple: (trained_model, best_parameters)
        """
        logger.info("Optimizing hyperparameters")
        
        # Define parameter grid
        param_grid = {
            'n_estimators': [50, 100, 200],
            'contamination': [0.01, 0.05, 0.1],
            'max_samples': ['auto', 100, 200]
        }
        
        # Initialize base model
        base_model = IsolationForest(random_state=self.isolation_forest_params['random_state'])
        
        # Define cross-validation strategy
        cv = TimeSeriesSplit(n_splits=3)
        
        # Since Isolation Forest is unsupervised, we'll use a dummy target
        y_dummy = np.zeros(len(values))
        
        # Grid search (this is a bit of a hack for unsupervised models)
        grid_search = GridSearchCV(
            base_model, 
            param_grid,
            cv=cv,
            scoring='neg_mean_squared_error'  # Not ideal but workable
        )
        
        # Fit grid search
        grid_search.fit(values, y_dummy)
        
        # Get best parameters and model
        best_params = grid_search.best_params_
        best_model = grid_search.best_estimator_
        
        logger.info(f"Best parameters: {best_params}")
        
        return best_model, best_params
    
    def batch_train_models(self, data, optimize=False):
        """
        Train models for all service/metric combinations in the data.
        
        Args:
            data (list): Training data
            optimize (bool): Whether to optimize hyperparameters
            
        Returns:
            dict: Trained models by service and metric
        """
        # Convert to DataFrame if needed
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        models = {}
        
        # Get unique service/metric combinations
        service_metrics = df.groupby(['service', 'metric']).size().reset_index()[['service', 'metric']]
        
        for _, row in service_metrics.iterrows():
            service = row['service']
            metric = row['metric']
            
            # Initialize service dictionary if needed
            if service not in models:
                models[service] = {}
            
            # Train model
            model = self.train_model(df, service, metric, optimize)
            
            if model:
                models[service][metric] = model
        
        logger.info(f"Batch trained {len(models)} models")
        
        return models
    
    def load_model(self, service, metric):
        """
        Load a trained model from disk.
        
        Args:
            service (str): Service name
            metric (str): Metric name
            
        Returns:
            object: Loaded model or None if not found
        """
        model_path = os.path.join(self.models_dir, service, f"{metric}_model.pkl")
        
        if not os.path.exists(model_path):
            logger.warning(f"Model not found: {model_path}")
            return None
        
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
                
            logger.info(f"Loaded model from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_path}: {str(e)}")
            return None
    
    def get_model_info(self, service=None, metric=None):
        """
        Get information about trained models.
        
        Args:
            service (str, optional): Filter by service
            metric (str, optional): Filter by metric
            
        Returns:
            list: Model information
        """
        models_info = []
        
        # Walk through models directory
        for root, dirs, files in os.walk(self.models_dir):
            for file in files:
                if file.endswith('_model.pkl'):
                    # Extract service and metric from path
                    path_parts = os.path.normpath(root).split(os.sep)
                    model_service = path_parts[-1] if len(path_parts) > 1 else None
                    model_metric = file.replace('_model.pkl', '')
                    
                    # Apply filters
                    if service and model_service != service:
                        continue
                        
                    if metric and model_metric != metric:
                        continue
                    
                    # Get file stats
                    model_path = os.path.join(root, file)
                    model_stats = os.stat(model_path)
                    
                    models_info.append({
                        'service': model_service,
                        'metric': model_metric,
                        'path': model_path,
                        'size_bytes': model_stats.st_size,
                        'created': datetime.fromtimestamp(model_stats.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(model_stats.st_mtime).isoformat()
                    })
        
        return models_info