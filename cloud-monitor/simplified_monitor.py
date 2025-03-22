#!/usr/bin/env python3
"""
AI-Driven Operational Intelligence & Incident Remediation
Enhanced version with improved visualization and anomaly display
"""
import os
import time
import logging
import yaml
import random
import pandas as pd
import numpy as np
import matplotlib
# Set non-interactive backend BEFORE importing pyplot
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, render_template_string, send_from_directory, jsonify
from sklearn.ensemble import IsolationForest

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize logging
logging.basicConfig(
    level=getattr(logging, config['general']['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cloud-monitor')

# Create necessary directories
os.makedirs(config['general']['data_dir'], exist_ok=True)
os.makedirs(config['general']['models_dir'], exist_ok=True)
os.makedirs(config['general']['static_dir'], exist_ok=True)

# Global variables
metrics_data = []
anomalies = []
remediation_history = []
is_running = True
models = {}

# Create Flask app
app = Flask(__name__, static_folder=config['general']['static_dir'])

def generate_metrics():
    """Generate metrics for all services"""
    timestamp = datetime.now().isoformat()
    data = []
    
    # Get anomaly probability from config
    anomaly_prob = config.get('simulation', {}).get('anomaly_probability', 0.1)
    
    # Random chance to introduce an anomaly (using config value or default to 10%)
    introduce_anomaly = random.random() < anomaly_prob
    anomaly_service = random.choice([s['name'] for s in config['services']]) if introduce_anomaly else None
    
    # Select random metrics to affect with anomaly
    if introduce_anomaly:
        all_metrics = []
        for service in config['services']:
            all_metrics.extend(list(service['metrics'].keys()))
        anomaly_metrics = random.sample(list(set(all_metrics)), random.randint(1, min(3, len(all_metrics))))
    else:
        anomaly_metrics = []
    
    for service in config['services']:
        service_name = service['name']
        
        for metric_name, metric_info in service['metrics'].items():
            baseline = metric_info['baseline']
            
            # Normal variation - increase from ±5% to ±10% for more variability
            variation = random.uniform(-0.1, 0.1)
            
            # Apply anomaly if selected
            if service_name == anomaly_service and metric_name in anomaly_metrics:
                # Choose anomaly type
                anomaly_patterns = config.get('simulation', {}).get('anomaly_patterns', [
                    {'name': 'sudden_spike', 'factor_range': [1.0, 2.0]},
                    {'name': 'gradual_increase', 'factor_range': [0.2, 0.6]},
                    {'name': 'service_degradation', 'factor_range': [0.3, 0.8]}
                ])
                
                # If no patterns defined, use defaults
                if not anomaly_patterns:
                    anomaly_patterns = [
                        {'name': 'sudden_spike', 'factor_range': [1.0, 2.0]},
                        {'name': 'gradual_increase', 'factor_range': [0.2, 0.6]},
                        {'name': 'service_degradation', 'factor_range': [0.3, 0.8]}
                    ]
                
                # Choose a random pattern
                pattern = random.choice(anomaly_patterns)
                anomaly_type = pattern['name']
                factor_range = pattern.get('factor_range', [0.5, 1.5])
                
                if anomaly_type == 'sudden_spike':
                    factor = random.uniform(factor_range[0], factor_range[1])
                    value = baseline * (1 + factor)
                elif anomaly_type == 'gradual_increase':
                    factor = random.uniform(factor_range[0], factor_range[1])
                    value = baseline * (1 + factor/2)  # Increased from factor/4 to factor/2
                else:  # service_degradation
                    factor = random.uniform(factor_range[0], factor_range[1])
                    value = baseline * (1 - factor/1.5) if baseline > 0 else baseline  # Increased from factor/2 to factor/1.5
                
                logger.info(f"Introduced {anomaly_type} anomaly on {service_name} affecting {metric_name}")
            else:
                value = baseline * (1 + variation)
            
            # Create metric record
            data.append({
                'timestamp': timestamp,
                'service': service_name,
                'metric': metric_name,
                'value': value
            })
    
    return data

def detect_anomalies(data):
    """
    Enhanced anomaly detection with multiple detection methods and more sensitive thresholds
    """
    detected_anomalies = []
    
    # If no data provided, return empty list
    if not data:
        return []
    
    # Group data by service and metric
    df = pd.DataFrame(data)
    
    # If DataFrame is empty, return empty list
    if df.empty:
        return []
    
    # Get historical data for context (last 100 points)
    historical_df = pd.DataFrame(metrics_data[-100:])
    
    # Get ML model settings from config
    ml_config = config.get('ml', {})
    isolation_forest_config = ml_config.get('isolation_forest', {})
    detection_config = ml_config.get('detection', {})
    
    # Get contamination parameter (with fallback)
    contamination = isolation_forest_config.get('contamination', 0.1)
    
    # Get severity thresholds (with fallbacks)
    severity_thresholds = detection_config.get('severity_thresholds', {
        'low': 0.8,
        'medium': 1.5,
        'high': 2.5
    })
    
    for service in df['service'].unique():
        for metric in df['metric'].unique():
            # Get values for this service and metric
            service_metric_data = df[(df['service'] == service) & (df['metric'] == metric)]
            
            if service_metric_data.empty:
                continue
                
            # Get historical data for this service and metric
            historical_service_metric = historical_df[
                (historical_df['service'] == service) & 
                (historical_df['metric'] == metric)
            ] if not historical_df.empty else pd.DataFrame()
            
            # Get latest value
            latest_row = service_metric_data.iloc[-1]
            latest_value = latest_row['value']
            
            # Approach 1: Use Isolation Forest if enough historical data
            if len(historical_service_metric) >= 8:
                values = historical_service_metric['value'].values.reshape(-1, 1)
                
                # Get or create model
                model_key = f"{service}_{metric}"
                if model_key not in models:
                    model = IsolationForest(
                        contamination=contamination,
                        random_state=isolation_forest_config.get('random_state', 42),
                        n_estimators=isolation_forest_config.get('n_estimators', 100)
                    )
                    model.fit(values)
                    models[model_key] = model
                else:
                    model = models[model_key]
                
                # Predict if anomaly
                prediction = model.predict([[latest_value]])[0]
                
                if prediction == -1:  # Anomaly detected by Isolation Forest
                    # Calculate severity
                    mean_value = np.mean(values)
                    std_value = np.std(values)
                    
                    if std_value == 0:
                        z_score = 0
                    else:
                        z_score = abs((latest_value - mean_value) / std_value)
                    
                    # Use thresholds from config
                    if z_score > severity_thresholds.get('high', 2.5):
                        severity = "high"
                    elif z_score > severity_thresholds.get('medium', 1.5):
                        severity = "medium"
                    else:
                        severity = "low"
                    
                    # Create anomaly record
                    anomaly = {
                        'timestamp': latest_row['timestamp'],
                        'service': service,
                        'metric': metric,
                        'value': float(latest_value),
                        'severity': severity,
                        'detection_method': 'isolation_forest',
                        'z_score': float(z_score)
                    }
                    
                    detected_anomalies.append(anomaly)
                    logger.info(f"Detected {severity} anomaly: {service}/{metric} = {latest_value:.2f} (z-score: {z_score:.2f})")
            
            # Approach 2: Use simple statistical detection for quick response or limited data
            elif len(historical_service_metric) >= 3:
                # Calculate simple statistics
                mean_value = historical_service_metric['value'].mean()
                std_value = historical_service_metric['value'].std()
                
                # Handle zero std
                if std_value == 0 or np.isnan(std_value):
                    std_value = 0.1 * mean_value if mean_value > 0 else 1.0
                
                # Calculate z-score
                z_score = abs((latest_value - mean_value) / std_value)
                
                # Detect anomalies using z-score threshold
                # More sensitive thresholds for statistical detection
                if z_score > severity_thresholds.get('low', 0.8):
                    if z_score > severity_thresholds.get('high', 2.5):
                        severity = "high"
                    elif z_score > severity_thresholds.get('medium', 1.5):
                        severity = "medium"
                    else:
                        severity = "low"
                    
                    # Create anomaly record
                    anomaly = {
                        'timestamp': latest_row['timestamp'],
                        'service': service,
                        'metric': metric,
                        'value': float(latest_value),
                        'severity': severity,
                        'detection_method': 'statistical',
                        'z_score': float(z_score)
                    }
                    
                    detected_anomalies.append(anomaly)
                    logger.info(f"Detected {severity} anomaly: {service}/{metric} = {latest_value:.2f} (z-score: {z_score:.2f}, statistical)")
            
            # Approach 3: For limited data, use baseline from config
            else:
                # Find baseline value from config
                baseline = None
                for svc in config['services']:
                    if svc['name'] == service and metric in svc['metrics']:
                        baseline = svc['metrics'][metric]['baseline']
                        break
                
                if baseline is not None:
                    # Calculate percent deviation from baseline
                    percent_deviation = abs((latest_value - baseline) / baseline) * 100 if baseline != 0 else 0
                    
                    # Detect significant deviations
                    if percent_deviation > 30:  # More than 30% deviation from baseline
                        if percent_deviation > 50:
                            severity = "high"
                        elif percent_deviation > 40:
                            severity = "medium"
                        else:
                            severity = "low"
                        
                        # Create anomaly record
                        anomaly = {
                            'timestamp': latest_row['timestamp'],
                            'service': service,
                            'metric': metric,
                            'value': float(latest_value),
                            'severity': severity,
                            'detection_method': 'baseline',
                            'percent_deviation': float(percent_deviation)
                        }
                        
                        detected_anomalies.append(anomaly)
                        logger.info(f"Detected {severity} anomaly: {service}/{metric} = {latest_value:.2f} ({percent_deviation:.1f}% from baseline)")
    
    return detected_anomalies

def apply_remediation(anomaly):
    """Apply remediation for an anomaly"""
    service = anomaly['service']
    metric = anomaly['metric']
    severity = anomaly['severity']
    
    # Get action template
    action_templates = config['remediation']['actions']
    if metric in action_templates and severity in action_templates[metric]:
        action_template = action_templates[metric][severity]
        action = action_template.format(service=service)
    else:
        action = f"Monitor {service} for further issues"
    
    # Create remediation record
    remediation_record = {
        'timestamp': datetime.now().isoformat(),
        'anomaly': anomaly,
        'action': action,
        'duration': random.uniform(0.1, 2.0),
        'status': 'completed'  # Add status for tracking
    }
    
    logger.info(f"Applied remediation: {action} for {service} ({metric})")
    
    return remediation_record

def update_plots():
    """Update dashboard plots - redirects to enhanced version if available"""
    try:
        # Try to use enhanced dashboard
        from enhanced_dashboard import update_all_charts
        update_all_charts(metrics_data, anomalies, remediation_history, config)
        return
    except ImportError:
        logger.info("Enhanced dashboard not found, using original plot generation")
    except Exception as e:
        logger.error(f"Error using enhanced dashboard: {str(e)}")
        logger.info("Falling back to original plot generation")
    
    # Original plot generation (fallback)
    try:
        # Skip if no data
        if not metrics_data:
            return
            
        static_dir = config['general']['static_dir']
        
        # Create DataFrame from metrics data
        df = pd.DataFrame(metrics_data)
        
        # Create service health chart
        plt.figure(figsize=(12, 6))
        
        # Get list of services
        services = df['service'].unique()
        
        # Calculate health score for each service
        service_health = []
        for service in services:
            service_data = df[df['service'] == service]
            
            # Use CPU and memory usage to estimate health
            cpu_data = service_data[service_data['metric'] == 'cpu_usage']
            mem_data = service_data[service_data['metric'] == 'memory_usage']
            
            cpu_avg = cpu_data['value'].mean() if not cpu_data.empty else 50
            mem_avg = mem_data['value'].mean() if not mem_data.empty else 50
            
            # Higher values mean worse health, so invert
            health_score = 100 - ((cpu_avg + mem_avg) / 2)
            
            service_health.append({
                'service': service,
                'health': health_score
            })
        
        # Create DataFrame and sort
        health_df = pd.DataFrame(service_health)
        if not health_df.empty:
            health_df = health_df.sort_values('health')
            
            plt.barh(health_df['service'], health_df['health'], color='green')
            
            plt.xlabel('Health Score (%)')
            plt.title('Service Health Overview')
            plt.xlim(0, 100)
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(os.path.join(static_dir, 'service_health.png'))
            plt.close()
        
        # Create metric trend plots
        metrics_to_plot = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'request_count']
        
        for metric in metrics_to_plot:
            plt.figure(figsize=(12, 6))
            
            # Filter data for this metric
            metric_data = df[df['metric'] == metric]
            
            if not metric_data.empty:
                # Group by service
                for service in metric_data['service'].unique():
                    service_data = metric_data[metric_data['service'] == service]
                    
                    # Plot the trend
                    plt.plot(range(len(service_data)), service_data['value'], label=service)
                
                plt.title(f'{metric.replace("_", " ").title()} Trends')
                plt.xlabel('Time Intervals')
                plt.ylabel('Value')
                plt.legend()
                plt.grid(linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, f'{metric}_trends.png'))
                plt.close()
        
        # Create anomaly distribution plot if we have anomalies
        if anomalies:
            anomalies_df = pd.DataFrame(anomalies)
            
            plt.figure(figsize=(12, 6))
            
            # Count anomalies by service and severity
            service_counts = anomalies_df.groupby(['service', 'severity']).size().unstack(fill_value=0)
            
            if not service_counts.empty:
                # Ensure all severity levels exist
                for level in ['low', 'medium', 'high']:
                    if level not in service_counts.columns:
                        service_counts[level] = 0
                
                # Plot stacked bars
                service_counts.plot(kind='bar', stacked=True, 
                                   color={'low': 'green', 'medium': 'orange', 'high': 'red'},
                                   alpha=0.7)
                
                plt.title('Anomaly Distribution by Service and Severity')
                plt.xlabel('Service')
                plt.ylabel('Count')
                plt.legend(title='Severity')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, 'anomaly_distribution.png'))
                plt.close()
                
                # Create anomalies over time plot
                plt.figure(figsize=(12, 6))
                
                # Count anomalies by severity over time
                anomalies_df['datetime'] = pd.to_datetime(anomalies_df['timestamp'])
                anomalies_df = anomalies_df.sort_values('datetime')
                
                # Plot time series for each severity
                for severity, color in [('high', 'red'), ('medium', 'orange'), ('low', 'green')]:
                    severity_data = anomalies_df[anomalies_df['severity'] == severity]
                    if not severity_data.empty:
                        plt.plot(range(len(severity_data)), 
                                [1] * len(severity_data),  # Just plot occurrence
                                'o', color=color, label=severity, alpha=0.7)
                
                plt.title('Anomalies Over Time')
                plt.xlabel('Time Intervals')
                plt.ylabel('Occurrence')
                plt.legend(title='Severity')
                plt.grid(linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, 'anomalies_time.png'))
                plt.close()
        
        # Create remediation effectiveness plot if we have remediations
        if remediation_history:
            plt.figure(figsize=(12, 6))
            
            # Count remediations by service
            remediation_df = pd.DataFrame([{
                'service': r['anomaly']['service'],
                'metric': r['anomaly']['metric'],
                'duration': r['duration']
            } for r in remediation_history])
            
            service_counts = remediation_df['service'].value_counts()
            
            if not service_counts.empty:
                plt.bar(service_counts.index, service_counts.values, color='blue', alpha=0.7)
                
                plt.title('Remediation Actions by Service')
                plt.xlabel('Service')
                plt.ylabel('Count')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
                plt.close()
    except Exception as e:
        logger.error(f"Error updating plots: {str(e)}")

# Dashboard route
@app.route('/')
def dashboard():
    """Render main dashboard"""
    try:
        # Try to use enhanced dashboard
        from enhanced_dashboard import get_enhanced_dashboard_html
        
        # Get services and metrics
        services = set()
        metrics = set()
        latest_metrics = {}
        service_health = {}
        
        for item in metrics_data:
            services.add(item['service'])
            metrics.add(item['metric'])
            
            # Update latest metrics
            if item['service'] not in latest_metrics:
                latest_metrics[item['service']] = {}
            latest_metrics[item['service']][item['metric']] = round(item['value'], 2)
        
        # Calculate service health scores (simplified)
        for service in services:
            service_data = [item for item in metrics_data if item['service'] == service]
            
            # Use CPU and memory usage as base metrics
            cpu_data = [item for item in service_data if item['metric'] == 'cpu_usage']
            mem_data = [item for item in service_data if item['metric'] == 'memory_usage']
            
            # Calculate average if data exists
            cpu_avg = sum([item['value'] for item in cpu_data]) / len(cpu_data) if cpu_data else 50
            mem_avg = sum([item['value'] for item in mem_data]) / len(mem_data) if mem_data else 50
            
            # Calculate health score - lower CPU and memory is better
            health_score = 100 - ((cpu_avg + mem_avg) / 2)
            service_health[service] = round(health_score, 1)
        
        # Create context for template
        context = {
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'refresh_interval': config['monitoring']['dashboard']['refresh_interval'],
            'services': list(services),
            'metrics': list(metrics),
            'latest_metrics': latest_metrics,
            'service_count': len(services),
            'metrics_count': len(metrics_data),
            'anomaly_count': len(anomalies),
            'remediation_count': len(remediation_history),
            'anomalies': anomalies[-20:] if anomalies else [],  # Show only the last 20
            'remediations': remediation_history[-20:] if remediation_history else [],  # Show only the last 20
            'recent_anomalies': anomalies[-5:] if anomalies else [],  # Show only the most recent 5
            'service_health': service_health
        }
        
        # Render the enhanced dashboard template
        return render_template_string(get_enhanced_dashboard_html(), **context)
    
    except (ImportError, Exception) as e:
        if isinstance(e, ImportError):
            logger.info("Enhanced dashboard not found, using original dashboard")
        else:
            logger.error(f"Error rendering enhanced dashboard: {str(e)}")
            logger.info("Falling back to original dashboard")
    
    # Original dashboard HTML template (fallback)
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloud Monitoring Dashboard</title>
        <meta http-equiv="refresh" content="{{ refresh_interval }}">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { display: flex; flex-wrap: wrap; }
            .card { margin: 10px; padding: 15px; border-radius: 5px; background-color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .metrics-card { width: 300px; }
            .anomaly-card { background-color: #ffebee; }
            .remediation-card { background-color: #e8f5e9; }
            .full-width { width: 100%; }
            h1, h2, h3 { color: #333; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            .high { color: #d32f2f; font-weight: bold; }
            .medium { color: #f57c00; }
            .low { color: #388e3c; }
            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .tabs { display: flex; margin-bottom: 20px; }
            .tab { padding: 10px 20px; cursor: pointer; border: 1px solid #ccc; background-color: #f8f8f8; }
            .tab.active { background-color: #fff; border-bottom: none; font-weight: bold; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .chart-container { margin-top: 20px; text-align: center; }
            .chart-container img { max-width: 100%; border: 1px solid #ddd; border-radius: 5px; }
            .navbar { background-color: #2196F3; color: white; padding: 15px; margin-bottom: 20px; }
            .navbar h1 { color: white; margin: 0; }
            .navigation { list-style: none; padding: 0; margin: 10px 0 0 0; }
            .navigation li { display: inline; margin-right: 20px; }
            .navigation a { color: white; text-decoration: none; }
            .navigation a:hover { text-decoration: underline; }
        </style>
        <script>
            function changeTab(tabName) {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Deactivate all tabs
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Activate selected tab and content
                document.getElementById('tab-' + tabName).classList.add('active');
                document.getElementById(tabName).classList.add('active');
            }
        </script>
    </head>
    <body>
        <div class="navbar">
            <h1>AI-Driven Operational Intelligence</h1>
            <ul class="navigation">
                <li><a href="/">Dashboard</a></li>
                <li><a href="/api/metrics" target="_blank">API</a></li>
            </ul>
        </div>
        
        <div class="tabs">
            <div class="tab active" id="tab-overview" onclick="changeTab('overview')">Overview</div>
            <div class="tab" id="tab-services" onclick="changeTab('services')">Services</div>
            <div class="tab" id="tab-anomalies" onclick="changeTab('anomalies')">Anomalies</div>
            <div class="tab" id="tab-remediation" onclick="changeTab('remediation')">Remediation</div>
        </div>
        
        <!-- Overview Tab -->
        <div id="overview" class="tab-content active">
            <div class="header-row">
                <h2>System Overview</h2>
                <div>Last updated: {{ current_time }}</div>
            </div>
            
            <div class="container">
                <div class="card">
                    <h3>System Stats</h3>
                    <table>
                        <tr><td>Active Services:</td><td>{{ service_count }}</td></tr>
                        <tr><td>Metrics Collected:</td><td>{{ metrics_count }}</td></tr>
                        <tr><td>Active Anomalies:</td><td>{{ anomaly_count }}</td></tr>
                        <tr><td>Remediation Actions:</td><td>{{ remediation_count }}</td></tr>
                    </table>
                </div>
                
                {% if anomaly_count > 0 %}
                <div class="card anomaly-card">
                    <h3>Current Alerts</h3>
                    <table>
                        {% for anomaly in recent_anomalies %}
                        <tr>
                            <td>{{ anomaly.service }}</td>
                            <td>{{ anomaly.metric }}</td>
                            <td class="{{ anomaly.severity }}">{{ anomaly.severity }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
                {% endif %}
            </div>
            
            <div class="chart-container">
                <h3>Service Health Overview</h3>
                <img src="/static/service_health.png" alt="Service Health">
            </div>
            
            <div class="chart-container">
                <h3>Anomaly Distribution</h3>
                <img src="/static/anomaly_distribution.png" alt="Anomaly Distribution">
            </div>
        </div>
        
        <!-- Services Tab -->
        <div id="services" class="tab-content">
            <h2>Service Status</h2>
            <div class="container">
                {% for service in services %}
                <div class="card metrics-card">
                    <h3>{{ service }}</h3>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        {% for metric in metrics %}
                        <tr>
                            <td>{{ metric }}</td>
                            <td>{{ latest_metrics.get(service, {}).get(metric, 'N/A') }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
                {% endfor %}
            </div>
            
            <div class="chart-container">
                <h3>CPU Usage Trends</h3>
                <img src="/static/cpu_usage_trends.png" alt="CPU Usage Trends">
            </div>
            
            <div class="chart-container">
                <h3>Memory Usage Trends</h3>
                <img src="/static/memory_usage_trends.png" alt="Memory Usage Trends">
            </div>
            
            <div class="chart-container">
                <h3>Response Time Trends</h3>
                <img src="/static/response_time_trends.png" alt="Response Time Trends">
            </div>
        </div>
        
        <!-- Anomalies Tab -->
        <div id="anomalies" class="tab-content">
            <h2>Detected Anomalies</h2>
            
            {% if anomalies %}
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Service</th>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Severity</th>
                </tr>
                {% for anomaly in anomalies %}
                <tr>
                    <td>{{ anomaly.timestamp }}</td>
                    <td>{{ anomaly.service }}</td>
                    <td>{{ anomaly.metric }}</td>
                    <td>{{ "%.2f"|format(anomaly.value) }}</td>
                    <td class="{{ anomaly.severity }}">{{ anomaly.severity }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No anomalies detected.</p>
            {% endif %}
            
            <div class="chart-container">
                <h3>Anomalies Over Time</h3>
                <img src="/static/anomalies_time.png" alt="Anomalies Over Time">
            </div>
        </div>
        
        <!-- Remediation Tab -->
        <div id="remediation" class="tab-content">
            <h2>Remediation Actions</h2>
            
            {% if remediations %}
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Service</th>
                    <th>Issue</th>
                    <th>Action Taken</th>
                </tr>
                {% for remediation in remediations %}
                <tr>
                    <td>{{ remediation.timestamp }}</td>
                    <td>{{ remediation.anomaly.service }}</td>
                    <td>{{ remediation.anomaly.metric }} ({{ remediation.anomaly.severity }})</td>
                    <td>{{ remediation.action }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No remediation actions taken.</p>
            {% endif %}
            
            <div class="chart-container">
                <h3>Remediation Effectiveness</h3>
                <img src="/static/remediation_effectiveness.png" alt="Remediation Effectiveness">
            </div>
        </div>
    </body>
    </html>
    """
    
    # Get services and metrics for original dashboard
    services = set()
    metrics = set()
    latest_metrics = {}
    
    for item in metrics_data:
        services.add(item['service'])
        metrics.add(item['metric'])
        
        # Update latest metrics
        if item['service'] not in latest_metrics:
            latest_metrics[item['service']] = {}
        latest_metrics[item['service']][item['metric']] = round(item['value'], 2)
    
    context = {
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'refresh_interval': config['monitoring']['dashboard']['refresh_interval'],
        'services': list(services),
        'metrics': list(metrics),
        'latest_metrics': latest_metrics,
        'service_count': len(services),
        'metrics_count': len(metrics_data),
        'anomaly_count': len(anomalies),
        'remediation_count': len(remediation_history),
        'anomalies': anomalies[-20:] if anomalies else [],  # Show only the last 20
        'remediations': remediation_history[-20:] if remediation_history else [],  # Show only the last 20
        'recent_anomalies': anomalies[-5:] if anomalies else []  # Show only the most recent 5
    }
    
    return render_template_string(dashboard_html, **context)