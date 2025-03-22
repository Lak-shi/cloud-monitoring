#!/usr/bin/env python3
"""
Initialize directory structure and create sample files.
This script creates the necessary directories and populates them with
placeholder files to ensure the system works correctly on first run.
"""
import os
import json
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_sample_data():
    """Create sample data files."""
    data_dir = "data"
    create_directory(data_dir)
    
    # Create a README file
    with open(os.path.join(data_dir, "README.md"), "w") as f:
        f.write("""# Data Directory

This directory stores metrics data, anomalies, and remediation history.

## File Types

- `metrics_*.csv`: CSV files containing historical metrics data
- `anomalies_*.json`: JSON files containing detected anomalies
- `remediation_*.json`: JSON files containing remediation actions
- `export_*.csv`: Exported data for analysis

Data files are automatically generated and managed by the system.
        """)
    
    # Create a sample metrics CSV
    services = ['api-gateway', 'auth-service', 'database', 'storage-service', 'compute-engine']
    metrics = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'request_count']
    
    data = []
    start_time = datetime.datetime.now() - datetime.timedelta(hours=24)
    
    for hour in range(24):
        timestamp = start_time + datetime.timedelta(hours=hour)
        for service in services:
            for metric in metrics:
                # Generate realistic values
                if metric == 'cpu_usage':
                    value = 30 + np.random.normal(0, 5) + hour * 0.5
                elif metric == 'memory_usage':
                    value = 40 + np.random.normal(0, 3) + hour * 0.3
                elif metric == 'response_time':
                    value = 100 + np.random.normal(0, 10) + hour * 0.2
                elif metric == 'error_rate':
                    value = 0.5 + np.random.normal(0, 0.1)
                else:  # request_count
                    value = 500 + np.random.normal(0, 50) - hour * 5
                
                data.append({
                    'timestamp': timestamp.isoformat(),
                    'service': service,
                    'metric': metric,
                    'value': value
                })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    csv_path = os.path.join(data_dir, "metrics_sample.csv")
    df.to_csv(csv_path, index=False)
    print(f"Created sample metrics file: {csv_path}")
    
    # Create a sample anomalies JSON
    anomalies = []
    for i in range(10):
        service = np.random.choice(services)
        metric = np.random.choice(metrics)
        severity = np.random.choice(['low', 'medium', 'high'], p=[0.5, 0.3, 0.2])
        
        # Generate realistic anomaly values
        if metric == 'cpu_usage':
            value = 80 + np.random.normal(0, 5)
        elif metric == 'memory_usage':
            value = 85 + np.random.normal(0, 3)
        elif metric == 'response_time':
            value = 500 + np.random.normal(0, 50)
        elif metric == 'error_rate':
            value = 5 + np.random.normal(0, 1)
        else:  # request_count
            value = 1500 + np.random.normal(0, 100)
        
        anomalies.append({
            'timestamp': (start_time + datetime.timedelta(hours=np.random.randint(0, 24))).isoformat(),
            'service': service,
            'metric': metric,
            'value': value,
            'severity': severity
        })
    
    # Save anomalies to JSON
    anomalies_path = os.path.join(data_dir, "anomalies_sample.json")
    with open(anomalies_path, "w") as f:
        json.dump(anomalies, f, indent=2)
    print(f"Created sample anomalies file: {anomalies_path}")
    
    # Create a sample remediation JSON
    remediations = []
    for anomaly in anomalies:
        if np.random.random() < 0.7:  # 70% of anomalies are remediated
            action = ""
            if anomaly['metric'] == 'cpu_usage':
                action = f"Scaled up {anomaly['service']} instances by 30%"
            elif anomaly['metric'] == 'memory_usage':
                action = f"Allocated additional memory to {anomaly['service']}"
            elif anomaly['metric'] == 'response_time':
                action = f"Optimized database queries for {anomaly['service']}"
            elif anomaly['metric'] == 'error_rate':
                action = f"Restarted {anomaly['service']} instances"
            else:  # request_count
                action = f"Enabled rate limiting for {anomaly['service']}"
            
            remediations.append({
                'timestamp': (datetime.datetime.fromisoformat(anomaly['timestamp']) + 
                              datetime.timedelta(minutes=np.random.randint(1, 10))).isoformat(),
                'anomaly': anomaly,
                'action': action,
                'duration': np.random.random() * 2.0
            })
    
    # Save remediations to JSON
    remediation_path = os.path.join(data_dir, "remediation_sample.json")
    with open(remediation_path, "w") as f:
        json.dump(remediations, f, indent=2)
    print(f"Created sample remediation file: {remediation_path}")

def create_sample_models():
    """Create placeholder model files."""
    models_dir = "models"
    create_directory(models_dir)
    
    # Create a README file
    with open(os.path.join(models_dir, "README.md"), "w") as f:
        f.write("""# Models Directory

This directory stores trained machine learning models.

## Structure

- `<service_name>/`: Subdirectory for each service
  - `<metric_name>_model.pkl`: Trained model for specific metric

Models are automatically generated and versioned by the system.
        """)
    
    # Create placeholder directories for services
    services = ['api-gateway', 'auth-service', 'database', 'storage-service', 'compute-engine']
    for service in services:
        service_dir = os.path.join(models_dir, service)
        create_directory(service_dir)
        
        # Create a placeholder text file
        with open(os.path.join(service_dir, "placeholder.txt"), "w") as f:
            f.write(f"This directory will store trained models for {service}.\n")
            f.write("Actual model files will be generated when the system runs.\n")

def create_sample_static():
    """Create sample static assets for the dashboard."""
    static_dir = "static"
    create_directory(static_dir)
    
    # Create a README file
    with open(os.path.join(static_dir, "README.md"), "w") as f:
        f.write("""# Static Assets Directory

This directory stores static assets for the dashboard.

## Contents

- `*.png`: Visualization images
- `*.css`: Style sheets
- `*.js`: JavaScript files

These files are automatically generated and updated by the system.
        """)
    
    # Create a sample plot
    plt.figure(figsize=(10, 6))
    services = ['api-gateway', 'auth-service', 'database', 'storage-service', 'compute-engine']
    values = [65, 78, 45, 90, 55]
    plt.bar(services, values, color='skyblue')
    plt.title('Sample Service Health')
    plt.xlabel('Service')
    plt.ylabel('Health Score (%)')
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(os.path.join(static_dir, "sample_health.png"))
    plt.close()
    print(f"Created sample health plot in {static_dir}")
    
    # Create sample CSS
    with open(os.path.join(static_dir, "sample.css"), "w") as f:
        f.write("""/* Sample CSS for dashboard */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

.header {
    background-color: #2196F3;
    color: white;
    padding: 1rem;
    text-align: center;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}

.card {
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin-bottom: 1rem;
    padding: 1rem;
}

.high { color: #d32f2f; }
.medium { color: #f57c00; }
.low { color: #388e3c; }
        """)

def main():
    """Main function to initialize all directories."""
    print("Initializing directory structure...")
    create_sample_data()
    create_sample_models()
    create_sample_static()
    print("Directory structure initialized successfully!")

if __name__ == "__main__":
    main()