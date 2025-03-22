"""
ML model evaluation module.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import os
import mlflow

logger = logging.getLogger('cloud-monitor.ml')

class ModelEvaluator:
    """
    Evaluates model performance and maintains performance metrics.
    
    Features:
    - Calculates detection accuracy
    - Tracks false positives/negatives
    - Generates performance visualizations
    - Logs metrics to MLflow
    """
    
    def __init__(self, static_dir, experiment_id=None):
        """
        Initialize the model evaluator.
        
        Args:
            static_dir (str): Directory for output visualizations
            experiment_id (str, optional): MLflow experiment ID
        """
        self.static_dir = static_dir
        self.experiment_id = experiment_id
        self.true_positives = 0
        self.false_positives = 0
        self.true_negatives = 0
        self.false_negatives = 0
        self.history = []
        logger.info("Initialized model evaluator")
    
    def record_prediction(self, predicted_anomaly, actual_anomaly, service, metric, timestamp, value):
        """
        Record a prediction and its actual outcome.
        
        Args:
            predicted_anomaly (bool): Whether an anomaly was predicted
            actual_anomaly (bool): Whether an anomaly actually occurred
            service (str): Service name
            metric (str): Metric name
            timestamp (str): Prediction timestamp
            value (float): Metric value
            
        Returns:
            dict: Updated metrics
        """
        # Record prediction result
        if predicted_anomaly and actual_anomaly:
            self.true_positives += 1
            result = 'true_positive'
        elif predicted_anomaly and not actual_anomaly:
            self.false_positives += 1
            result = 'false_positive'
        elif not predicted_anomaly and actual_anomaly:
            self.false_negatives += 1
            result = 'false_negative'
        else:  # not predicted_anomaly and not actual_anomaly
            self.true_negatives += 1
            result = 'true_negative'
        
        # Add to history
        self.history.append({
            'timestamp': timestamp,
            'service': service,
            'metric': metric,
            'value': value,
            'predicted_anomaly': predicted_anomaly,
            'actual_anomaly': actual_anomaly,
            'result': result
        })
        
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        # Log to MLflow if configured
        if self.experiment_id:
            try:
                with mlflow.start_run(experiment_id=self.experiment_id):
                    mlflow.log_metrics({
                        'accuracy': metrics['accuracy'],
                        'precision': metrics['precision'],
                        'recall': metrics['recall'],
                        'f1_score': metrics['f1_score'],
                        'true_positives': self.true_positives,
                        'false_positives': self.false_positives,
                        'true_negatives': self.true_negatives,
                        'false_negatives': self.false_negatives
                    })
            except Exception as e:
                logger.error(f"Error logging to MLflow: {str(e)}")
        
        return metrics
    
    def calculate_metrics(self):
        """
        Calculate performance metrics.
        
        Returns:
            dict: Performance metrics
        """
        # Avoid division by zero
        epsilon = 1e-10
        
        # Calculate metrics
        accuracy = (self.true_positives + self.true_negatives) / max(epsilon, 
                    self.true_positives + self.true_negatives + self.false_positives + self.false_negatives)
        
        precision = self.true_positives / max(epsilon, self.true_positives + self.false_positives)
        
        recall = self.true_positives / max(epsilon, self.true_positives + self.false_negatives)
        
        f1_score = 2 * precision * recall / max(epsilon, precision + recall)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'counts': {
                'true_positives': self.true_positives,
                'false_positives': self.false_positives,
                'true_negatives': self.true_negatives,
                'false_negatives': self.false_negatives
            }
        }
    
    def generate_performance_plot(self):
        """
        Generate performance visualization.
        
        Returns:
            str: Path to generated image
        """
        if not self.history:
            logger.warning("No history data for performance plot")
            return None
        
        try:
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Create confusion matrix subplot
            plt.subplot(2, 2, 1)
            cm = np.array([
                [self.true_positives, self.false_negatives],
                [self.false_positives, self.true_negatives]
            ])
            
            plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
            plt.title('Confusion Matrix')
            plt.colorbar()
            
            classes = ['Anomaly', 'Normal']
            tick_marks = np.arange(len(classes))
            plt.xticks(tick_marks, classes, rotation=45)
            plt.yticks(tick_marks, classes)
            
            # Add text annotations
            thresh = cm.max() / 2.0
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    plt.text(j, i, format(cm[i, j], 'd'),
                             horizontalalignment="center",
                             color="white" if cm[i, j] > thresh else "black")
            
            plt.ylabel('Actual')
            plt.xlabel('Predicted')
            
            # Create metrics subplot
            plt.subplot(2, 2, 2)
            metrics = self.calculate_metrics()
            metric_values = [metrics['accuracy'], metrics['precision'], metrics['recall'], metrics['f1_score']]
            metric_names = ['Accuracy', 'Precision', 'Recall', 'F1 Score']
            
            plt.bar(metric_names, metric_values, color=['blue', 'green', 'orange', 'red'])
            plt.ylim(0, 1.0)
            plt.title('Performance Metrics')
            plt.ylabel('Score')
            
            # Create history plot by service
            plt.subplot(2, 1, 2)
            
            # Convert history to DataFrame
            history_df = pd.DataFrame(self.history)
            
            if not history_df.empty:
                # Convert timestamp to datetime
                history_df['datetime'] = pd.to_datetime(history_df['timestamp'])
                
                # Sort by timestamp
                history_df = history_df.sort_values('datetime')
                
                # Count by service and result
                results_by_service = history_df.groupby(['service', 'result']).size().unstack(fill_value=0)
                
                # Plot stacked bars
                colors = {
                    'true_positive': 'green',
                    'true_negative': 'blue',
                    'false_positive': 'orange',
                    'false_negative': 'red'
                }
                
                # Ensure all result types exist
                for result in colors.keys():
                    if result not in results_by_service.columns:
                        results_by_service[result] = 0
                
                results_by_service.plot(kind='bar', stacked=True, ax=plt.gca(), 
                                        color=[colors[col] for col in results_by_service.columns])
                
                plt.title('Prediction Results by Service')
                plt.ylabel('Count')
                plt.xlabel('Service')
                plt.legend(title='Result')
            
            plt.tight_layout()
            
            # Save figure
            filename = f"model_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.static_dir, 'model_performance.png')
            plt.savefig(filepath)
            plt.close()
            
            logger.info(f"Generated performance plot: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating performance plot: {str(e)}")
            return None
    
    def get_performance_summary(self):
        """
        Get a summary of model performance.
        
        Returns:
            dict: Performance summary
        """
        metrics = self.calculate_metrics()
        
        # Calculate per-service metrics
        service_metrics = {}
        
        if self.history:
            history_df = pd.DataFrame(self.history)
            
            for service in history_df['service'].unique():
                service_data = history_df[history_df['service'] == service]
                
                tp = len(service_data[(service_data['predicted_anomaly'] == True) & 
                                      (service_data['actual_anomaly'] == True)])
                fp = len(service_data[(service_data['predicted_anomaly'] == True) & 
                                      (service_data['actual_anomaly'] == False)])
                tn = len(service_data[(service_data['predicted_anomaly'] == False) & 
                                      (service_data['actual_anomaly'] == False)])
                fn = len(service_data[(service_data['predicted_anomaly'] == False) & 
                                      (service_data['actual_anomaly'] == True)])
                
                # Calculate metrics (with protection against division by zero)
                epsilon = 1e-10
                
                accuracy = (tp + tn) / max(epsilon, tp + tn + fp + fn)
                precision = tp / max(epsilon, tp + fp)
                recall = tp / max(epsilon, tp + fn)
                f1_score = 2 * precision * recall / max(epsilon, precision + recall)
                
                service_metrics[service] = {
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1_score,
                    'counts': {
                        'true_positives': tp,
                        'false_positives': fp,
                        'true_negatives': tn,
                        'false_negatives': fn
                    }
                }
        
        return {
            'overall': metrics,
            'by_service': service_metrics,
            'total_predictions': len(self.history),
            'timestamp': datetime.now().isoformat()
        }