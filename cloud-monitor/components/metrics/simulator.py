"""
Metrics simulation module for cloud services.
Generates realistic metrics data for monitoring and anomaly detection.
"""
import random
import time
from datetime import datetime
import logging

logger = logging.getLogger('cloud-monitor.metrics')

class CloudMetricsSimulator:
    """
    Simulates metrics for cloud services with occasional anomalies.
    
    This class handles:
    - Baseline metrics for each service
    - Random normal variation
    - Anomaly patterns (spikes, gradual changes, etc.)
    """
    
    def __init__(self, services_config, simulation_config):
        """
        Initialize the simulator with service configurations and anomaly patterns.
        
        Args:
            services_config (list): List of service configurations
            simulation_config (dict): Simulation parameters
        """
        self.services = {}
        
        # Build baseline metrics dictionary from config
        for service_config in services_config:
            service_name = service_config['name']
            self.services[service_name] = {}
            
            for metric_name, metric_config in service_config['metrics'].items():
                self.services[service_name][metric_name] = metric_config['baseline']
        
        # Set up anomaly patterns
        self.anomaly_patterns = {}
        for pattern in simulation_config['anomaly_patterns']:
            pattern_name = pattern['name']
            if pattern_name == 'sudden_spike':
                self.anomaly_patterns[pattern_name] = lambda x, factor: x * (1 + factor)
            elif pattern_name == 'gradual_increase':
                self.anomaly_patterns[pattern_name] = lambda x, factor: x * (1 + factor/4)
            elif pattern_name == 'service_degradation':
                self.anomaly_patterns[pattern_name] = lambda x, factor: x * (1 - factor/2) if x > 0 else x
        
        self.anomaly_probability = simulation_config['anomaly_probability']
        self.current_anomalies = {}
        logger.info(f"Initialized metrics simulator with {len(self.services)} services")
    
    # Edit components/metrics/simulator.py
    def generate_metrics_batch(self, num_services=None):
        """
        Generate a batch of metrics for services using Ray for distribution.
        
        Args:
            num_services (int, optional): Number of services to generate metrics for.
                If None, generates for all services.
        
        Returns:
            list: List of metric data points
        """
        timestamp = datetime.now().isoformat()
        data = []  # Explicitly create a list
        
        # Random chance to introduce an anomaly
        if random.random() < self.anomaly_probability and not self.current_anomalies:
            self._introduce_anomaly()
        
        # Select services to generate metrics for
        service_names = list(self.services.keys())
        if num_services and num_services < len(service_names):
            selected_services = random.sample(service_names, num_services)
        else:
            selected_services = service_names
        
        # Generate metrics for each selected service
        for service_name in selected_services:
            for metric_name, baseline_value in self.services[service_name].items():
                # Apply anomaly if exists for this service and metric
                if service_name in self.current_anomalies and metric_name in self.current_anomalies[service_name]:
                    pattern, factor, duration = self.current_anomalies[service_name][metric_name]
                    value = self.anomaly_patterns[pattern](baseline_value, factor)
                    
                    # Decrease duration counter
                    self.current_anomalies[service_name][metric_name][2] -= 1
                    if self.current_anomalies[service_name][metric_name][2] <= 0:
                        del self.current_anomalies[service_name][metric_name]
                        if not self.current_anomalies[service_name]:
                            del self.current_anomalies[service_name]
                else:
                    # Normal variation (+/- 5%)
                    variation = random.uniform(-0.05, 0.05)
                    value = baseline_value * (1 + variation)
                
                # Create metric record
                data.append({
                    'timestamp': timestamp,
                    'service': service_name,
                    'metric': metric_name,
                    'value': value
                })
        
        return data  # Return list directly
    
    def _introduce_anomaly(self):
        """
        Introduce an anomaly to a random service and metric.
        
        Returns:
            tuple: (service_name, affected_metrics, anomaly_pattern)
        """
        service_name = random.choice(list(self.services.keys()))
        available_metrics = list(self.services[service_name].keys())
        metrics_affected = random.sample(available_metrics, random.randint(1, min(3, len(available_metrics))))
        pattern = random.choice(list(self.anomaly_patterns.keys()))
        
        if service_name not in self.current_anomalies:
            self.current_anomalies[service_name] = {}
        
        for metric_name in metrics_affected:
            # Different factors for different metrics
            if metric_name in ['cpu_usage', 'memory_usage', 'response_time']:
                factor = random.uniform(0.5, 1.5)  # 50-150% change
            else:
                factor = random.uniform(0.3, 0.7)  # 30-70% change
                
            # Duration of 3-7 cycles
            duration = random.randint(3, 7)
            self.current_anomalies[service_name][metric_name] = [pattern, factor, duration]
        
        logger.info(f"Introduced {pattern} anomaly on {service_name} affecting {metrics_affected}")
        return service_name, metrics_affected, pattern