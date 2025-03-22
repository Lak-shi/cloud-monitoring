"""
Prometheus metrics module for monitoring.
Exposes system metrics via Prometheus endpoint.
"""
import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger('cloud-monitor.monitoring')

def setup_prometheus_metrics(port=8000):
    """
    Setup Prometheus metrics and server.
    
    Args:
        port (int): Port to expose metrics on
        
    Returns:
        tuple: (start_server_function, metrics_dict)
    """
    # Define metrics
    metrics = {
        # Counter for anomalies detected
        'anomaly_counter': Counter(
            'cloud_monitor_anomalies_total',
            'Total number of anomalies detected',
            ['service', 'metric']
        ),
        
        # Counter for remediation actions
        'remediation_counter': Counter(
            'cloud_monitor_remediations_total',
            'Total number of remediation actions taken',
            ['service', 'action_type']
        ),
        
        # Gauge for current service metrics
        'service_metric': Gauge(
            'cloud_monitor_service_metric',
            'Current service metric value',
            ['service', 'metric']
        ),
        
        # Histogram for remediation duration
        'remediation_duration': Histogram(
            'cloud_monitor_remediation_duration_seconds',
            'Time taken for remediation actions',
            ['service']
        ),
        
        # Gauge for model health
        'model_health': Gauge(
            'cloud_monitor_model_health',
            'Health status of ML models',
            ['service', 'metric']
        )
    }
    
    def start_server():
        """
        Start the Prometheus HTTP server.
        """
        start_http_server(port)
        logger.info(f"Started Prometheus metrics server on port {port}")
    
    return start_server, metrics