"""
Dashboard module for visualization.
Provides a web-based dashboard for monitoring the system.
"""
import os
import threading
import time
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, send_from_directory, jsonify
from datetime import datetime

logger = logging.getLogger('cloud-monitor.monitoring')

def create_dashboard_app(config, metrics_data, anomalies, remediation_history):
    """
    Create Flask app for the dashboard.
    
    Args:
        config (dict): Application configuration
        metrics_data (list): Reference to metrics data
        anomalies (list): Reference to anomalies
        remediation_history (list): Reference to remediation history
        
    Returns:
        Flask: Flask application
    """
    app = Flask(__name__, static_folder=config['general']['static_dir'])
    
    @app.route('/')
    def dashboard():
        """
        Render the main dashboard.
        """
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
                    <li><a href="http://localhost:{{ prometheus_port }}" target="_blank">Prometheus</a></li>
                    <li><a href="http://localhost:5001" target="_blank">MLflow</a></li>
                </ul>
            </div>
            
            <div class="tabs">
                <div class="tab active" id="tab-overview" onclick="changeTab('overview')">Overview</div>
                <div class="tab" id="tab-services" onclick="changeTab('services')">Services</div>
                <div class="tab" id="tab-anomalies" onclick="changeTab('anomalies')">Anomalies</div>
                <div class="tab" id="tab-remediation" onclick="changeTab('remediation')">Remediation</div>
                <div class="tab" id="tab-models" onclick="changeTab('models')">ML Models</div>
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
                        {% if use_gpt %}
                        <th>GPT Suggestion</th>
                        {% endif %}
                    </tr>
                    {% for remediation in remediations %}
                    <tr>
                        <td>{{ remediation.timestamp }}</td>
                        <td>{{ remediation.anomaly.service }}</td>
                        <td>{{ remediation.anomaly.metric }} ({{ remediation.anomaly.severity }})</td>
                        <td>{{ remediation.action }}</td>
                        {% if use_gpt and remediation.gpt_suggestion %}
                        <td>{{ remediation.gpt_suggestion }}</td>
                        {% endif %}
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
            
            <!-- Models Tab -->
            <div id="models" class="tab-content">
                <h2>ML Models</h2>
                
                <div class="chart-container">
                    <h3>Model Performance</h3>
                    <img src="/static/model_performance.png" alt="Model Performance">
                </div>
                
                <h3>MLflow Experiments</h3>
                <p>For detailed model tracking, access the MLflow UI: <a href="http://localhost:5001" target="_blank">http://localhost:5001</a></p>
            </div>
        </body>
        </html>
        """
        
        # Get metrics data
        df = pd.DataFrame(metrics_data) if metrics_data else pd.DataFrame()
        
        # Get list of services and metrics
        services = list(set([item['service'] for item in metrics_data])) if metrics_data else []
        metrics = list(set([item['metric'] for item in metrics_data])) if metrics_data else []
        
        # Get latest metrics
        latest_metrics = {}
        if not df.empty:
            for service in services:
                latest_metrics[service] = {}
                for metric in metrics:
                    service_metric_data = df[(df['service'] == service) & (df['metric'] == metric)]
                    if not service_metric_data.empty:
                        latest_metrics[service][metric] = round(service_metric_data['value'].iloc[-1], 2)
        
        context = {
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'refresh_interval': config['monitoring']['dashboard']['refresh_interval'],
            'prometheus_port': config['monitoring']['prometheus']['port'],
            'services': services,
            'metrics': metrics,
            'latest_metrics': latest_metrics,
            'service_count': len(services),
            'metrics_count': len(metrics_data),
            'anomaly_count': len(anomalies),
            'remediation_count': len(remediation_history),
            'anomalies': anomalies[-20:],  # Show only the last 20 anomalies
            'remediations': remediation_history[-20:],  # Show only the last 20 remediations
            'recent_anomalies': anomalies[-5:],  # Show only the most recent 5 anomalies
            'use_gpt': config['remediation']['use_gpt']
        }
        
        return render_template_string(dashboard_html, **context)
    
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """
        Serve static files.
        """
        return send_from_directory(config['general']['static_dir'], filename)
    
    @app.route('/api/metrics')
    def api_metrics():
        """
        API endpoint for metrics data.
        """
        return jsonify({
            'metrics': metrics_data[-100:],  # Return last 100 data points
            'anomalies': anomalies[-20:],    # Return last 20 anomalies
            'remediations': remediation_history[-20:]  # Return last 20 remediations
        })
    
    return app

def update_plots(metrics_data, anomalies, remediation_history, config):
    """
    Update dashboard plots periodically.
    
    Args:
        metrics_data (list): Metrics data
        anomalies (list): Anomalies
        remediation_history (list): Remediation history
        config (dict): Application configuration
    """
    static_dir = config['general']['static_dir']
    
    while True:
        try:
            if not metrics_data:
                # No data yet, wait and try again
                time.sleep(5)
                continue
                
            # Convert data to DataFrame for easier processing
            df = pd.DataFrame(metrics_data)
            
            # Create service health plot
            create_service_health_plot(df, static_dir)
            
            # Create CPU, memory, and response time trends
            create_metric_trend_plots(df, static_dir)
            
            # Create anomaly plots
            if anomalies:
                anomalies_df = pd.DataFrame(anomalies)
                create_anomaly_plots(anomalies_df, static_dir)
            
            # Create remediation plots
            if remediation_history:
                remediation_df = pd.DataFrame([{
                    'timestamp': r['timestamp'],
                    'service': r['anomaly']['service'],
                    'metric': r['anomaly']['metric'],
                    'severity': r['anomaly']['severity'],
                    'action': r['action']
                } for r in remediation_history])
                create_remediation_plots(remediation_df, anomalies, static_dir)
            
            # Create model performance plot
            create_model_performance_plot(anomalies, remediation_history, static_dir)
            
            # Wait before updating again
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"Error updating plots: {str(e)}")
            time.sleep(5)

def create_service_health_plot(df, static_dir):
    """
    Create service health overview plot.
    
    Args:
        df (DataFrame): Metrics data
        static_dir (str): Directory to save plot
    """
    try:
        plt.figure(figsize=(12, 6))
        
        # Get list of services
        services = df['service'].unique()
        
        # Calculate average values for each service
        service_health = []
        for service in services:
            service_data = df[df['service'] == service]
            
            # Calculate health score based on CPU, memory, and response time
            cpu_data = service_data[service_data['metric'] == 'cpu_usage']
            mem_data = service_data[service_data['metric'] == 'memory_usage']
            resp_data = service_data[service_data['metric'] == 'response_time']
            
            # Default values if data is missing
            cpu_avg = cpu_data['value'].mean() if not cpu_data.empty else 50
            mem_avg = mem_data['value'].mean() if not mem_data.empty else 50
            
            # Normalize response time between 0-100
            if not resp_data.empty:
                resp_max = resp_data['value'].max()
                resp_min = resp_data['value'].min()
                resp_range = max(1, resp_max - resp_min)  # Avoid division by zero
                resp_avg = 100 - ((resp_data['value'].mean() - resp_min) / resp_range * 100)
            else:
                resp_avg = 50
            
            # Calculate health score (inverse of utilization)
            health_score = 100 - ((cpu_avg + mem_avg) / 2)
            
            service_health.append({
                'service': service,
                'health': health_score,
                'cpu': cpu_avg,
                'memory': mem_avg,
                'response': resp_avg
            })
        
        # Create DataFrame from health scores
        health_df = pd.DataFrame(service_health)
        
        # Plot health scores
        if not health_df.empty:
            health_df = health_df.sort_values('health')
            
            plt.barh(health_df['service'], health_df['health'], color='green', alpha=0.7)
            plt.barh(health_df['service'], health_df['cpu'], color='red', alpha=0.5)
            plt.barh(health_df['service'], health_df['memory'], color='orange', alpha=0.5)
            
            plt.xlabel('Score (%)')
            plt.title('Service Health Overview')
            plt.xlim(0, 100)
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add legend
            plt.legend(['Health Score', 'CPU Usage', 'Memory Usage'], loc='lower right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(static_dir, 'service_health.png'))
            plt.close()
    except Exception as e:
        logger.error(f"Error creating service health plot: {str(e)}")

def create_metric_trend_plots(df, static_dir):
    """
    Create trend plots for CPU, memory, and response time.
    
    Args:
        df (DataFrame): Metrics data
        static_dir (str): Directory to save plots
    """
    try:
        metrics_to_plot = {
            'cpu_usage': 'CPU Usage Trends',
            'memory_usage': 'Memory Usage Trends',
            'response_time': 'Response Time Trends'
        }
        
        for metric, title in metrics_to_plot.items():
            plt.figure(figsize=(12, 6))
            
            # Filter data for this metric
            metric_data = df[df['metric'] == metric]
            
            if not metric_data.empty:
                # Group by service and create time series
                for service in metric_data['service'].unique():
                    service_data = metric_data[metric_data['service'] == service]
                    
                    # Sort by timestamp
                    if 'timestamp' in service_data.columns:
                        service_data['datetime'] = pd.to_datetime(service_data['timestamp'])
                        service_data = service_data.sort_values('datetime')
                    
                    # Plot the trend
                    plt.plot(range(len(service_data)), service_data['value'], label=service)
                
                plt.title(title)
                plt.xlabel('Time Intervals')
                plt.ylabel('Value')
                plt.legend()
                plt.grid(linestyle='--', alpha=0.7)
                
                # Save the plot
                filename = metric + '_trends.png'
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, filename))
                plt.close()
    except Exception as e:
        logger.error(f"Error creating metric trend plots: {str(e)}")

def create_anomaly_plots(anomalies_df, static_dir):
    """
    Create plots for anomaly distribution and time series.
    
    Args:
        anomalies_df (DataFrame): Anomalies data
        static_dir (str): Directory to save plots
    """
    try:
        # Create anomaly distribution plot
        plt.figure(figsize=(12, 6))
        
        # Count anomalies by service and severity
        try:
            severity_counts = anomalies_df.groupby(['service', 'severity']).size().unstack(fill_value=0)
            
            if not severity_counts.empty:
                # Ensure all severity levels exist
                for level in ['low', 'medium', 'high']:
                    if level not in severity_counts.columns:
                        severity_counts[level] = 0
                
                # Plot stacked bars
                severity_counts.plot(kind='bar', stacked=True, color=['green', 'orange', 'red'], alpha=0.7)
                
                plt.title('Anomaly Distribution by Service and Severity')
                plt.xlabel('Service')
                plt.ylabel('Count')
                plt.legend(title='Severity')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, 'anomaly_distribution.png'))
        except Exception as e:
            logger.error(f"Error creating anomaly distribution plot: {str(e)}")
            
        plt.close()
        
        # Create anomalies over time plot
        plt.figure(figsize=(12, 6))
        
        try:
            # Convert timestamps to datetime
            if 'timestamp' in anomalies_df.columns:
                anomalies_df['datetime'] = pd.to_datetime(anomalies_df['timestamp'])
                anomalies_df = anomalies_df.sort_values('datetime')
                
                # Count anomalies per timestamp
                anomaly_counts = anomalies_df.groupby(['datetime', 'severity']).size().unstack(fill_value=0).reset_index()
                
                if not anomaly_counts.empty:
                    # Ensure all severity levels exist
                    for level in ['low', 'medium', 'high']:
                        if level not in anomaly_counts.columns:
                            anomaly_counts[level] = 0
                    
                    # Plot time series
                    plt.plot(range(len(anomaly_counts)), anomaly_counts.get('high', [0] * len(anomaly_counts)), 'r-', label='High', linewidth=2)
                    plt.plot(range(len(anomaly_counts)), anomaly_counts.get('medium', [0] * len(anomaly_counts)), 'orange', label='Medium', linewidth=2)
                    plt.plot(range(len(anomaly_counts)), anomaly_counts.get('low', [0] * len(anomaly_counts)), 'g-', label='Low', linewidth=2)
                    
                    plt.title('Anomalies Over Time')
                    plt.xlabel('Time Intervals')
                    plt.ylabel('Count')
                    plt.legend(title='Severity')
                    plt.grid(linestyle='--', alpha=0.7)
                    
                    plt.tight_layout()
                    plt.savefig(os.path.join(static_dir, 'anomalies_time.png'))
        except Exception as e:
            logger.error(f"Error creating anomalies over time plot: {str(e)}")
            
        plt.close()
    except Exception as e:
        logger.error(f"Error creating anomaly plots: {str(e)}")

def create_remediation_plots(remediation_df, anomalies, static_dir):
    """
    Create plots for remediation effectiveness.
    
    Args:
        remediation_df (DataFrame): Remediation data
        anomalies (list): Anomalies list
        static_dir (str): Directory to save plots
    """
    try:
        plt.figure(figsize=(12, 6))
        
        # Count remediations by service
        service_counts = remediation_df['service'].value_counts()
        
        if not service_counts.empty:
            # Count total anomalies by service
            anomaly_df = pd.DataFrame(anomalies)
            if not anomaly_df.empty:
                anomaly_counts = anomaly_df['service'].value_counts()
                
                # Merge remediation and anomaly counts
                services = list(set(service_counts.index) | set(anomaly_counts.index))
                
                remediation_values = [service_counts.get(s, 0) for s in services]
                anomaly_values = [anomaly_counts.get(s, 0) for s in services]
                
                # Calculate remediation rate
                remediation_rate = [
                    min(100, (r / max(1, a)) * 100) for r, a in zip(remediation_values, anomaly_values)
                ]
                
                # Create DataFrame
                plot_df = pd.DataFrame({
                    'service': services,
                    'remediations': remediation_values,
                    'anomalies': anomaly_values,
                    'rate': remediation_rate
                })
                
                # Sort by remediation rate
                plot_df = plot_df.sort_values('rate', ascending=False)
                
                # Plot bars
                x = np.arange(len(plot_df))
                width = 0.35
                
                fig, ax1 = plt.subplots(figsize=(12, 6))
                
                # Bar chart for counts
                ax1.bar(x - width/2, plot_df['anomalies'], width, label='Anomalies', color='red', alpha=0.7)
                ax1.bar(x + width/2, plot_df['remediations'], width, label='Remediations', color='green', alpha=0.7)
                
                ax1.set_xlabel('Service')
                ax1.set_ylabel('Count')
                ax1.set_title('Remediation Effectiveness')
                ax1.set_xticks(x)
                ax1.set_xticklabels(plot_df['service'], rotation=45, ha='right')
                ax1.legend(loc='upper left')
                
                # Line chart for rate
                ax2 = ax1.twinx()
                ax2.plot(x, plot_df['rate'], 'b-', label='Success Rate', linewidth=2)
                ax2.set_ylabel('Success Rate (%)')
                ax2.legend(loc='upper right')
                
                plt.tight_layout()
                plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
                plt.close()
    except Exception as e:
        logger.error(f"Error creating remediation plots: {str(e)}")

def create_model_performance_plot(anomalies, remediation_history, static_dir):
    """
    Create model performance plot.
    
    Args:
        anomalies (list): Anomalies
        remediation_history (list): Remediation history
        static_dir (str): Directory to save plot
    """
    try:
        plt.figure(figsize=(12, 6))
        
        # Calculate detection-to-remediation times
        if anomalies and remediation_history:
            # Create lookup of anomalies by service/metric/timestamp
            anomaly_lookup = {}
            for anomaly in anomalies:
                key = f"{anomaly['service']}_{anomaly['metric']}_{anomaly['timestamp']}"
                anomaly_lookup[key] = anomaly
            
            # Calculate delay for each remediation
            delays = []
            for remediation in remediation_history:
                anomaly = remediation['anomaly']
                key = f"{anomaly['service']}_{anomaly['metric']}_{anomaly['timestamp']}"
                
                if key in anomaly_lookup:
                    # Parse timestamps
                    anomaly_time = pd.to_datetime(anomaly['timestamp'])
                    remediation_time = pd.to_datetime(remediation['timestamp'])
                    
                    # Calculate delay in seconds
                    delay = (remediation_time - anomaly_time).total_seconds()
                    
                    delays.append({
                        'service': anomaly['service'],
                        'delay': delay
                    })
            
            if delays:
                # Create DataFrame
                delays_df = pd.DataFrame(delays)
                
                # Group by service
                service_delays = delays_df.groupby('service')['delay'].mean()
                
                if not service_delays.empty:
                    # Sort by delay
                    service_delays = service_delays.sort_values()
                    
                    # Plot bars
                    plt.barh(service_delays.index, service_delays, color='blue', alpha=0.7)
                    
                    plt.title('Average Detection-to-Remediation Time by Service')
                    plt.xlabel('Time (seconds)')
                    plt.ylabel('Service')
                    plt.grid(axis='x', linestyle='--', alpha=0.7)
                    
                    plt.tight_layout()
                    plt.savefig(os.path.join(static_dir, 'model_performance.png'))
                    plt.close()
    except Exception as e:
        logger.error(f"Error creating model performance plot: {str(e)}")