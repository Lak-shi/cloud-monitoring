#!/usr/bin/env python3
"""
Generate sample data for the cloud monitoring system.
This script creates sample metrics data, anomalies, and remediation actions.
"""
import os
import json
import random
import datetime
import numpy as np
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_dir(directory):
    """Ensure directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def generate_metrics(output_file, num_hours=24, num_samples_per_hour=4):
    """
    Generate sample metrics data.
    
    Args:
        output_file (str): Output file path
        num_hours (int): Number of hours of data to generate
        num_samples_per_hour (int): Number of samples per hour
    """
    services = ['api-gateway', 'auth-service', 'database', 'storage-service', 'compute-engine']
    metrics = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'request_count']
    
    # Define baseline values for each service and metric
    baselines = {
        'api-gateway': {'cpu_usage': 30, 'memory_usage': 40, 'response_time': 200, 'error_rate': 0.5, 'request_count': 500},
        'auth-service': {'cpu_usage': 25, 'memory_usage': 35, 'response_time': 100, 'error_rate': 0.2, 'request_count': 400},
        'database': {'cpu_usage': 60, 'memory_usage': 70, 'response_time': 50, 'error_rate': 0.1, 'request_count': 1000},
        'storage-service': {'cpu_usage': 40, 'memory_usage': 60, 'response_time': 150, 'error_rate': 0.3, 'request_count': 300},
        'compute-engine': {'cpu_usage': 70, 'memory_usage': 65, 'response_time': 300, 'error_rate': 0.4, 'request_count': 200}
    }
    
    # Define variation parameters for each metric
    variations = {
        'cpu_usage': {'normal': 5, 'trend': 0.3, 'anomaly_chance': 0.05, 'anomaly_factor': 2.0},
        'memory_usage': {'normal': 3, 'trend': 0.2, 'anomaly_chance': 0.04, 'anomaly_factor': 1.5},
        'response_time': {'normal': 20, 'trend': 1.0, 'anomaly_chance': 0.06, 'anomaly_factor': 3.0},
        'error_rate': {'normal': 0.1, 'trend': 0.01, 'anomaly_chance': 0.03, 'anomaly_factor': 5.0},
        'request_count': {'normal': 50, 'trend': -2.0, 'anomaly_chance': 0.02, 'anomaly_factor': 2.0}
    }
    
    data = []
    start_time = datetime.datetime.now() - datetime.timedelta(hours=num_hours)
    
    # Generate data for each time point
    for hour in range(num_hours):
        for sample in range(num_samples_per_hour):
            # Calculate timestamp
            minutes = (sample * 60) // num_samples_per_hour
            timestamp = start_time + datetime.timedelta(hours=hour, minutes=minutes)
            
            # Generate data for each service and metric
            for service in services:
                for metric in metrics:
                    # Get baseline value
                    baseline = baselines[service][metric]
                    
                    # Get variation parameters
                    var_params = variations[metric]
                    
                    # Apply normal variation
                    normal_var = np.random.normal(0, var_params['normal'])
                    
                    # Apply time trend
                    trend_var = hour * var_params['trend']
                    
                    # Determine if this is an anomaly
                    is_anomaly = random.random() < var_params['anomaly_chance']
                    anomaly_var = 0
                    if is_anomaly:
                        # Apply anomaly factor (can be positive or negative)
                        if random.random() < 0.8:  # 80% chance of positive anomaly
                            anomaly_var = baseline * (var_params['anomaly_factor'] - 1) * random.random()
                        else:
                            anomaly_var = -baseline * 0.5 * random.random()  # Negative anomaly
                    
                    # Calculate final value
                    value = max(0, baseline + normal_var + trend_var + anomaly_var)
                    
                    # Add to data
                    data.append({
                        'timestamp': timestamp.isoformat(),
                        'service': service,
                        'metric': metric,
                        'value': value,
                        'is_anomaly': is_anomaly
                    })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    logger.info(f"Generated {len(df)} metrics records to {output_file}")
    
    # Return anomalies for further processing
    return df[df['is_anomaly']].drop('is_anomaly', axis=1).to_dict('records')

def generate_anomalies(anomalies, output_file):
    """
    Generate sample anomalies based on metrics data.
    
    Args:
        anomalies (list): List of anomaly records from metrics
        output_file (str): Output file path
    """
    # Define severity thresholds for each metric
    severity_thresholds = {
        'cpu_usage': {'medium': 70, 'high': 85},
        'memory_usage': {'medium': 75, 'high': 90},
        'response_time': {'medium': 300, 'high': 500},
        'error_rate': {'medium': 1.0, 'high': 3.0},
        'request_count': {'medium': 1000, 'high': 1500}
    }
    
    # Process anomalies
    processed_anomalies = []
    for anomaly in anomalies:
        metric = anomaly['metric']
        value = anomaly['value']
        
        # Determine severity
        if metric in severity_thresholds:
            thresholds = severity_thresholds[metric]
            if value >= thresholds['high']:
                severity = 'high'
            elif value >= thresholds['medium']:
                severity = 'medium'
            else:
                severity = 'low'
        else:
            severity = 'medium'  # Default
        
        # Create anomaly record
        processed_anomalies.append({
            'timestamp': anomaly['timestamp'],
            'service': anomaly['service'],
            'metric': anomaly['metric'],
            'value': float(value),
            'severity': severity
        })
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(processed_anomalies, f, indent=2)
        
    logger.info(f"Generated {len(processed_anomalies)} anomaly records to {output_file}")
    return processed_anomalies

def generate_remediations(anomalies, output_file):
    """
    Generate sample remediation actions based on anomalies.
    
    Args:
        anomalies (list): List of anomaly records
        output_file (str): Output file path
    """
    # Define remediation actions for each metric and severity
    remediation_actions = {
        'cpu_usage': {
            'high': lambda s: f"Scaled up {s} instances by 50%",
            'medium': lambda s: f"Scaled up {s} instances by 20%",
            'low': lambda s: f"Optimized workload distribution for {s}"
        },
        'memory_usage': {
            'high': lambda s: f"Allocated additional memory to {s}",
            'medium': lambda s: f"Triggered garbage collection on {s}",
            'low': lambda s: f"Monitored memory usage on {s}"
        },
        'response_time': {
            'high': lambda s: f"Rerouted traffic from {s} to backup instances",
            'medium': lambda s: f"Optimized database queries for {s}",
            'low': lambda s: f"Enabled response time monitoring for {s}"
        },
        'error_rate': {
            'high': lambda s: f"Triggered circuit breaker for {s}",
            'medium': lambda s: f"Restarted {s} instances",
            'low': lambda s: f"Increased logging level for {s}"
        },
        'request_count': {
            'high': lambda s: f"Enabled rate limiting for {s}",
            'medium': lambda s: f"Redistributed traffic for {s}",
            'low': lambda s: f"Monitored traffic patterns for {s}"
        }
    }
    
    # Process remediations
    remediations = []
    for anomaly in anomalies:
        # 70% chance of remediation
        if random.random() < 0.7:
            metric = anomaly['metric']
            severity = anomaly['severity']
            service = anomaly['service']
            
            # Get action function
            if metric in remediation_actions and severity in remediation_actions[metric]:
                action_func = remediation_actions[metric][severity]
                action = action_func(service)
            else:
                action = f"Monitored {service} for further issues"
            
            # Calculate timestamp (1-10 minutes after anomaly)
            anomaly_time = datetime.datetime.fromisoformat(anomaly['timestamp'])
            remediation_time = anomaly_time + datetime.timedelta(minutes=random.randint(1, 10))
            
            # Create remediation record
            remediations.append({
                'timestamp': remediation_time.isoformat(),
                'anomaly': anomaly,
                'action': action,
                'duration': round(random.uniform(0.1, 2.0), 2),  # 0.1 to 2.0 seconds
                'successful': random.random() < 0.9  # 90% success rate
            })
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(remediations, f, indent=2)
        
    logger.info(f"Generated {len(remediations)} remediation records to {output_file}")

def main():
    """Main function."""
    # Ensure directories exist
    ensure_dir('data')
    
    # Generate sample data
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    metrics_file = f"data/metrics_{timestamp}.csv"
    anomalies_file = f"data/anomalies_{timestamp}.json"
    remediations_file = f"data/remediations_{timestamp}.json"
    
    # Generate metrics and get anomalies
    anomalies = generate_metrics(metrics_file)
    
    # Generate anomalies
    processed_anomalies = generate_anomalies(anomalies, anomalies_file)
    
    # Generate remediations
    generate_remediations(processed_anomalies, remediations_file)
    
    print(f"\nSample data generation complete!")
    print(f"- Metrics: {metrics_file}")
    print(f"- Anomalies: {anomalies_file}")
    print(f"- Remediations: {remediations_file}")

if __name__ == "__main__":
    main()