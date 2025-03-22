"""
Enhanced dashboard for AI-Driven Operational Intelligence & Incident Remediation
This module provides improved visualization and fixes for anomaly display
"""
import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from flask import render_template_string

logger = logging.getLogger('cloud-monitor')

def create_anomalies_time_chart(anomalies, output_path):
    """Create a chart showing anomalies over time with severity"""
    if not anomalies:
        # Create an empty chart if no anomalies
        plt.figure(figsize=(12, 6))
        plt.title('Anomalies Over Time')
        plt.xlabel('Time Intervals')
        plt.ylabel('Occurrence')
        plt.grid(linestyle='--', alpha=0.7)
        plt.text(0.5, 0.5, 'No anomalies detected', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return

    # Convert to DataFrame for easier manipulation
    anomalies_df = pd.DataFrame(anomalies)
    
    # Ensure datetime column exists
    if 'timestamp' in anomalies_df.columns:
        anomalies_df['datetime'] = pd.to_datetime(anomalies_df['timestamp'])
        anomalies_df = anomalies_df.sort_values('datetime')
    else:
        # Create a dummy timeline if no timestamp
        anomalies_df['datetime'] = pd.date_range(start=datetime.now(), periods=len(anomalies_df))
    
    # Create plot
    plt.figure(figsize=(12, 6))
    
    # Plot time series for each severity with better markers and labels
    severity_colors = {'high': 'red', 'medium': 'orange', 'low': 'green'}
    severity_markers = {'high': 'X', 'medium': 'o', 'low': '.'}
    severity_sizes = {'high': 100, 'medium': 80, 'low': 60}
    
    # Create x-axis based on sequence rather than actual timestamps
    x_range = range(len(anomalies_df))
    
    # Plot each severity level
    for severity, color in severity_colors.items():
        severity_data = anomalies_df[anomalies_df['severity'] == severity]
        if not severity_data.empty:
            # Find the positions in the original timeline
            positions = [list(anomalies_df['datetime']).index(dt) for dt in severity_data['datetime']]
            
            # Plot with enhanced markers
            plt.scatter(positions, [1] * len(severity_data), 
                       marker=severity_markers[severity], 
                       s=severity_sizes[severity],
                       color=color, label=severity, alpha=0.7)
    
    # Add services as annotations
    for i, row in enumerate(anomalies_df.itertuples()):
        service = getattr(row, 'service', '')
        metric = getattr(row, 'metric', '')
        severity = getattr(row, 'severity', '')
        
        if service and metric:
            # Only annotate high and medium severity for readability
            if severity in ['high', 'medium']:
                plt.annotate(f"{service}\n{metric}", 
                           (i, 1), 
                           xytext=(0, 10),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=8,
                           rotation=45)
    
    # Enhance plot appearance
    plt.title('Anomalies Over Time', fontsize=14)
    plt.xlabel('Time Sequence', fontsize=12)
    plt.ylabel('Occurrence', fontsize=12)
    plt.legend(title='Severity')
    plt.grid(linestyle='--', alpha=0.5)
    
    # Adjust y-axis to make room for annotations
    plt.ylim(0.5, 1.5)
    plt.yticks([])  # Hide y-ticks as they're not meaningful here
    
    # Add current time indicator
    plt.axvline(x=len(anomalies_df)-1, color='blue', linestyle='--', alpha=0.5, label='Now')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def create_service_health_chart(metrics_data, output_path):
    """Create an enhanced service health chart with better colors and information"""
    if not metrics_data:
        # Create empty chart if no data
        plt.figure(figsize=(12, 6))
        plt.title('Service Health Overview')
        plt.xlabel('Health Score (%)')
        plt.text(0.5, 0.5, 'No metrics data available', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return
        
    # Create DataFrame from metrics data
    df = pd.DataFrame(metrics_data)
    
    # Get list of services
    services = df['service'].unique()
    
    # Calculate health score for each service with more metrics
    service_health = []
    for service in services:
        service_data = df[df['service'] == service]
        
        # Use CPU and memory usage as base metrics
        cpu_data = service_data[service_data['metric'] == 'cpu_usage']
        mem_data = service_data[service_data['metric'] == 'memory_usage']
        
        # Get error rate and response time if available
        error_data = service_data[service_data['metric'] == 'error_rate']
        resp_data = service_data[service_data['metric'] == 'response_time']
        
        # Calculate weighted health score
        cpu_avg = cpu_data['value'].mean() if not cpu_data.empty else 50
        mem_avg = mem_data['value'].mean() if not mem_data.empty else 50
        error_avg = error_data['value'].mean() if not error_data.empty else 0
        resp_avg = resp_data['value'].mean() if not resp_data.empty else 100
        
        # Calculate weighted health score - lower CPU, memory, errors and response time is better
        # Higher error rates should have more penalty
        cpu_score = 100 - cpu_avg  # 0-100 where higher is better
        mem_score = 100 - mem_avg  # 0-100 where higher is better
        
        # Error rates are typically low percentages, so scale them appropriately
        error_score = 100 - (error_avg * 20) if error_avg <= 5 else 0
        
        # Normalize response time to a 0-100 scale (assuming 0-500ms is ideal)
        resp_score = 100 - (resp_avg / 5) if resp_avg <= 500 else 0
        
        # Weighted average for overall health
        health_score = (cpu_score * 0.3) + (mem_score * 0.3) + (error_score * 0.25) + (resp_score * 0.15)
        
        # Ensure health_score is within 0-100
        health_score = max(0, min(100, health_score))
        
        service_health.append({
            'service': service,
            'health': health_score,
            'cpu_score': cpu_score,
            'mem_score': mem_score,
            'error_score': error_score,
            'resp_score': resp_score
        })
    
    # Create DataFrame and sort
    health_df = pd.DataFrame(service_health)
    
    if not health_df.empty:
        # Sort by health score
        health_df = health_df.sort_values('health')
        
        plt.figure(figsize=(12, 6))
        
        # Create colormap for health scores
        colors = []
        for score in health_df['health']:
            if score >= 80:
                colors.append('#4CAF50')  # Good - Green
            elif score >= 60:
                colors.append('#FFC107')  # Warning - Yellow/Amber
            else:
                colors.append('#F44336')  # Critical - Red
        
        # Plot horizontal bar chart with better colors
        bars = plt.barh(health_df['service'], health_df['health'], color=colors)
        
        # Add data labels on bars
        for bar in bars:
            width = bar.get_width()
            label_x_pos = width if width > 10 else 10
            plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.1f}%',
                    va='center', ha='left' if width > 50 else 'right',
                    color='black' if width > 50 else 'white',
                    fontweight='bold')
        
        plt.xlabel('Health Score (%)', fontsize=12)
        plt.title('Service Health Overview', fontsize=14)
        plt.xlim(0, 100)
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        
        # Add explanation of health calculation
        plt.figtext(0.02, 0.02, 
                   "Health score: 30% CPU, 30% Memory, 25% Error Rate, 15% Response Time",
                   ha="left", fontsize=8, style='italic')
        
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

def create_anomaly_distribution_chart(anomalies, output_path):
    """Create an enhanced anomaly distribution chart with better colors and layout"""
    if not anomalies:
        # Create empty chart if no anomalies
        plt.figure(figsize=(12, 6))
        plt.title('Anomaly Distribution by Service and Severity')
        plt.xlabel('Service')
        plt.ylabel('Count')
        plt.text(0.5, 0.5, 'No anomalies detected', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return
        
    anomalies_df = pd.DataFrame(anomalies)
    
    plt.figure(figsize=(12, 6))
    
    # Count anomalies by service and severity
    try:
        service_counts = anomalies_df.groupby(['service', 'severity']).size().unstack(fill_value=0)
        
        if not service_counts.empty:
            # Ensure all severity levels exist
            for level in ['low', 'medium', 'high']:
                if level not in service_counts.columns:
                    service_counts[level] = 0
            
            # Plot stacked bars with better colors and patterns
            service_counts.plot(kind='bar', stacked=True, 
                              color={'low': '#4CAF50', 'medium': '#FFC107', 'high': '#F44336'},
                              alpha=0.8)
            
            plt.title('Anomaly Distribution by Service and Severity', fontsize=14)
            plt.xlabel('Service', fontsize=12)
            plt.ylabel('Count', fontsize=12)
            plt.legend(title='Severity')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add service details as annotations
            if 'metric' in anomalies_df.columns:
                for service in service_counts.index:
                    metrics = anomalies_df[anomalies_df['service'] == service]['metric'].unique()
                    metrics_str = ", ".join(metrics[:3])  # Show at most 3 metrics to avoid clutter
                    if len(metrics) > 3:
                        metrics_str += "..."
                        
                    plt.annotate(f"Metrics: {metrics_str}", 
                               xy=(service_counts.index.get_loc(service), service_counts.loc[service].sum()),
                               xytext=(0, 10),
                               textcoords="offset points",
                               ha='center', va='bottom',
                               fontsize=8,
                               rotation=45)
            
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
        else:
            # No data case
            plt.title('Anomaly Distribution by Service and Severity')
            plt.xlabel('Service')
            plt.ylabel('Count')
            plt.text(0.5, 0.5, 'No anomalies detected', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes, fontsize=14)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
    except Exception as e:
        logger.error(f"Error creating anomaly distribution chart: {str(e)}")
        # Create a fallback chart
        plt.title('Anomaly Distribution by Service and Severity')
        plt.xlabel('Service')
        plt.ylabel('Count')
        plt.text(0.5, 0.5, 'Error generating chart', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

def update_metric_trends_charts(metrics_data, static_dir):
    """Create enhanced metric trend charts"""
    if not metrics_data:
        return
        
    # Create DataFrame from metrics data
    df = pd.DataFrame(metrics_data)
    
    # Define better colors for services
    service_colors = {
        'api-gateway': '#2196F3',      # Blue
        'auth-service': '#4CAF50',     # Green
        'database': '#FFC107',         # Amber
        'storage-service': '#9C27B0',  # Purple
        'compute-engine': '#F44336'    # Red
    }
    
    # Create metric trend plots with enhanced visuals
    metrics_to_plot = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'request_count']
    
    for metric in metrics_to_plot:
        plt.figure(figsize=(12, 6))
        
        # Filter data for this metric
        metric_data = df[df['metric'] == metric]
        
        if not metric_data.empty:
            # Group by service
            for service in metric_data['service'].unique():
                service_data = metric_data[metric_data['service'] == service]
                
                # Plot the trend with better colors and line styles
                color = service_colors.get(service, 'gray')  # Default to gray if service not in color map
                
                plt.plot(
                    range(len(service_data)), 
                    service_data['value'], 
                    label=service,
                    color=color,
                    linewidth=2,
                    marker='o',
                    markersize=3,
                    alpha=0.8
                )
            
            # Set up appropriate y-axis ranges based on metric type
            if metric == 'cpu_usage' or metric == 'memory_usage':
                plt.ylim(0, 100)
                plt.ylabel('Percent (%)', fontsize=12)
            elif metric == 'error_rate':
                plt.ylabel('Rate (%)', fontsize=12)
            elif metric == 'response_time':
                plt.ylabel('Time (ms)', fontsize=12)
            else:
                plt.ylabel('Count', fontsize=12)
            
            # Add benchmark lines for reference
            if metric == 'cpu_usage':
                plt.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='Critical Threshold')
                plt.axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='Warning Threshold')
            elif metric == 'memory_usage':
                plt.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='Critical Threshold')
                plt.axhline(y=70, color='orange', linestyle='--', alpha=0.5, label='Warning Threshold')
            elif metric == 'response_time':
                plt.axhline(y=200, color='orange', linestyle='--', alpha=0.5, label='Warning Threshold')
                plt.axhline(y=500, color='red', linestyle='--', alpha=0.5, label='Critical Threshold')
            elif metric == 'error_rate':
                plt.axhline(y=5, color='red', linestyle='--', alpha=0.5, label='Critical Threshold')
                plt.axhline(y=1, color='orange', linestyle='--', alpha=0.5, label='Warning Threshold')
            
            plt.title(f'{metric.replace("_", " ").title()} Trends', fontsize=14)
            plt.xlabel('Time Intervals', fontsize=12)
            plt.legend(fontsize=10)
            plt.grid(linestyle='--', alpha=0.7)
            
            # Add time reference
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            plt.figtext(0.02, 0.02, f"Last update: {current_time}", ha="left", fontsize=8)
            
            plt.tight_layout()
            plt.savefig(os.path.join(static_dir, f'{metric}_trends.png'))
            plt.close()

def update_remediation_chart(remediation_history, static_dir):
    """Create enhanced remediation effectiveness chart"""
    if not remediation_history:
        # Create empty chart if no data
        plt.figure(figsize=(12, 6))
        plt.title('Remediation Actions by Service', fontsize=14)
        plt.xlabel('Service', fontsize=12)
        plt.ylabel('Count', fontsize=12)
        plt.text(0.5, 0.5, 'No remediation actions taken', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
        plt.close()
        return
    
    plt.figure(figsize=(12, 6))
    
    try:
        # Create a DataFrame for remediation actions
        remediation_df = pd.DataFrame([{
            'service': r['anomaly']['service'],
            'metric': r['anomaly']['metric'],
            'severity': r['anomaly']['severity'],
            'action': r['action'],
            'duration': r['duration'],
            'timestamp': r['timestamp'] if 'timestamp' in r else None
        } for r in remediation_history])
        
        # Count remediations by service
        service_counts = remediation_df['service'].value_counts()
        
        if not service_counts.empty:
            # Create color map based on remediation counts
            max_count = service_counts.max()
            colors = []
            for count in service_counts:
                intensity = min(1.0, count / max_count)
                colors.append((0.2, 0.4, 0.8, 0.6 + 0.4 * intensity))  # Blue with varying intensity
            
            # Plot bars with colors
            bars = plt.bar(service_counts.index, service_counts.values, color=colors)
            
            # Add count labels on top of bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}',
                        ha='center', va='bottom')
            
            # Add remediation details as annotations
            for service in service_counts.index:
                actions = remediation_df[remediation_df['service'] == service]['action'].unique()
                actions_str = ", ".join([a[:20] + "..." if len(a) > 20 else a for a in actions[:2]])
                if len(actions) > 2:
                    actions_str += "..."
                    
                plt.annotate(f"Actions: {actions_str}", 
                           xy=(list(service_counts.index).index(service), service_counts[service]),
                           xytext=(0, 10),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=8,
                           rotation=45)
            
            plt.title('Remediation Actions by Service', fontsize=14)
            plt.xlabel('Service', fontsize=12)
            plt.ylabel('Count', fontsize=12)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add effectiveness info if duration data is available
            if 'duration' in remediation_df.columns:
                avg_duration = remediation_df.groupby('service')['duration'].mean()
                
                # Add a second y-axis for average remediation time
                ax2 = plt.twinx()
                ax2.plot(avg_duration.index, avg_duration, 'ro-', markersize=8, label='Avg Time')
                ax2.set_ylabel('Avg. Remediation Time (s)', color='r', fontsize=12)
                ax2.tick_params(axis='y', labelcolor='r')
                
                # Add legend for the secondary axis
                from matplotlib.lines import Line2D
                custom_lines = [Line2D([0], [0], color='r', lw=2, marker='o')]
                ax2.legend(custom_lines, ['Avg. Remediation Time'], loc='upper right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
            plt.close()
        else:
            # Create empty chart if no data
            plt.title('Remediation Actions by Service', fontsize=14)
            plt.xlabel('Service', fontsize=12)
            plt.ylabel('Count', fontsize=12)
            plt.text(0.5, 0.5, 'No remediation actions taken', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes, fontsize=14)
            plt.tight_layout()
            plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
            plt.close()
    except Exception as e:
        logger.error(f"Error creating remediation chart: {str(e)}")
        # Create a fallback chart
        plt.title('Remediation Actions by Service', fontsize=14)
        plt.xlabel('Service', fontsize=12)
        plt.ylabel('Count', fontsize=12)
        plt.text(0.5, 0.5, 'Error generating chart', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(static_dir, 'remediation_effectiveness.png'))
        plt.close()

def update_all_charts(metrics_data, anomalies, remediation_history, config):
    """Update all dashboard charts with enhanced visuals"""
    try:
        static_dir = config['general']['static_dir']
        
        # Create enhanced service health chart
        create_service_health_chart(
            metrics_data, 
            os.path.join(static_dir, 'service_health.png')
        )
        
        # Create enhanced anomaly distribution chart
        create_anomaly_distribution_chart(
            anomalies,
            os.path.join(static_dir, 'anomaly_distribution.png')
        )
        
        # Create enhanced anomalies time chart
        create_anomalies_time_chart(
            anomalies,
            os.path.join(static_dir, 'anomalies_time.png')
        )
        
        # Update remaining charts as needed
        update_metric_trends_charts(metrics_data, static_dir)
        update_remediation_chart(remediation_history, static_dir)
        
    except Exception as e:
        logger.error(f"Error updating all charts: {str(e)}")

def get_enhanced_dashboard_html():
    """Returns the HTML template for the enhanced dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI-Driven Operational Intelligence</title>
        <meta http-equiv="refresh" content="{{ refresh_interval }}">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root {
                --primary-color: #2196F3;
                --secondary-color: #1976D2;
                --success-color: #4CAF50;
                --warning-color: #FFC107;
                --danger-color: #F44336;
                --light-color: #f5f5f5;
                --dark-color: #333;
                --text-color: #212121;
                --border-color: #e0e0e0;
            }
            
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: var(--light-color); 
                color: var(--text-color);
            }
            
            .navbar {
                background-color: var(--primary-color);
                color: white;
                padding: 15px 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            .navbar h1 {
                margin: 0;
                font-size: 1.6rem;
                font-weight: 400;
            }
            
            .navbar-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .navigation {
                list-style: none;
                margin: 0;
                padding: 0;
                display: flex;
            }
            
            .navigation li {
                margin-left: 20px;
            }
            
            .navigation a {
                color: white;
                text-decoration: none;
                font-size: 0.9rem;
                opacity: 0.9;
                transition: opacity 0.2s;
            }
            
            .navigation a:hover {
                opacity: 1;
                text-decoration: none;
            }
            
            .system-stats {
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                margin: 20px;
                border-radius: 4px;
                overflow: hidden;
            }
            
            .stats-title {
                background-color: var(--secondary-color);
                color: white;
                padding: 15px 20px;
                margin: 0;
                font-size: 1.1rem;
                font-weight: 400;
            }
            
            .stats-container {
                display: flex;
                flex-wrap: wrap;
                padding: 15px;
            }
            
            .stat-card {
                flex: 1;
                min-width: 200px;
                padding: 15px;
                text-align: center;
                border-right: 1px solid var(--border-color);
            }
            
            .stat-card:last-child {
                border-right: none;
            }
            
            .stat-value {
                font-size: 2rem;
                font-weight: 300;
                margin: 10px 0;
                color: var(--primary-color);
            }
            
            .stat-label {
                font-size: 0.9rem;
                color: #757575;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .content {
                padding: 20px;
            }
            
            .tabs {
                display: flex;
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                margin-bottom: 20px;
                border-radius: 4px;
                overflow: hidden;
            }
            
            .tab {
                padding: 15px 20px;
                cursor: pointer;
                transition: background-color 0.2s;
                font-weight: 500;
                color: #757575;
                border-bottom: 2px solid transparent;
            }
            
            .tab:hover {
                background-color: rgba(33, 150, 243, 0.05);
            }
            
            .tab.active {
                color: var(--primary-color);
                border-bottom: 2px solid var(--primary-color);
            }
            
            .tab-content {
                display: none;
            }
            
            .tab-content.active {
                display: block;
            }
            
            .section {
                background-color: white;
                margin-bottom: 20px;
                border-radius: 4px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            }
            
            .section-title {
                padding: 15px 20px;
                margin: 0;
                font-size: 1.1rem;
                font-weight: 400;
                background-color: #f9f9f9;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .section-content {
                padding: 20px;
            }
            
            .chart-container {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .chart-container:last-child {
                margin-bottom: 0;
            }
            
            .chart-container img {
                max-width: 100%;
                border-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            .chart-title {
                margin-bottom: 15px;
                font-weight: 400;
                color: #424242;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            
            table:last-child {
                margin-bottom: 0;
            }
            
            th, td {
                text-align: left;
                padding: 12px 15px;
                border-bottom: 1px solid var(--border-color);
            }
            
            th {
                background-color: #f9f9f9;
                font-weight: 500;
            }
            
            tr:hover {
                background-color: #f5f5f5;
            }
            
            .status-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
            }
            
            .status-good {
                background-color: var(--success-color);
            }
            
            .status-warning {
                background-color: var(--warning-color);
            }
            
            .status-critical {
                background-color: var(--danger-color);
            }
            
            .severity-high {
                color: var(--danger-color);
                font-weight: bold;
            }
            
            .severity-medium {
                color: var(--warning-color);
                font-weight: bold;
            }
            
            .severity-low {
                color: var(--success-color);
            }
            
            .service-card-container {
                display: flex;
                flex-wrap: wrap;
                margin: 0 -10px;
            }
            
            .service-card {
                flex: 1;
                min-width: 300px;
                margin: 10px;
                background-color: white;
                border-radius: 4px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            }
            
            .service-header {
                padding: 15px;
                border-bottom: 1px solid var(--border-color);
                font-weight: 500;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .service-content {
                padding: 0;
            }
            
            .service-content table {
                margin: 0;
            }
            
            .card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            
            .alert-card {
                background-color: rgba(244, 67, 54, 0.05);
                border-left: 4px solid var(--danger-color);
            }
            
            .date-display {
                font-size: 0.9rem;
                color: #757575;
            }
            
            .empty-state {
                padding: 40px 20px;
                text-align: center;
                color: #757575;
            }
            
            .empty-state p {
                margin: 10px 0 0;
            }
            
            .footer {
                text-align: center;
                padding: 20px;
                color: #757575;
                font-size: 0.8rem;
                border-top: 1px solid var(--border-color);
                margin-top: 30px;
            }
            
            /* Animation for highlighting new anomalies */
            @keyframes highlight {
                0% { background-color: rgba(255, 193, 7, 0.2); }
                100% { background-color: transparent; }
            }
            
            .highlight {
                animation: highlight 2s ease-in-out;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .stats-container {
                    flex-direction: column;
                }
                
                .stat-card {
                    border-right: none;
                    border-bottom: 1px solid var(--border-color);
                }
                
                .stat-card:last-child {
                    border-bottom: none;
                }
                
                .service-card {
                    min-width: 100%;
                }
                
                .tabs {
                    overflow-x: auto;
                }
            }
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
                
                // Store the active tab in local storage
                localStorage.setItem('activeTab', tabName);
            }
            
            // Set the active tab based on localStorage when page loads
            window.onload = function() {
                const activeTab = localStorage.getItem('activeTab') || 'overview';
                changeTab(activeTab);
            };
        </script>
    </head>
    <body>
        <div class="navbar">
            <div class="navbar-content">
                <h1>AI-Driven Operational Intelligence</h1>
                <ul class="navigation">
                    <li><a href="/">Dashboard</a></li>
                    <li><a href="/api/metrics" target="_blank">API</a></li>
                </ul>
            </div>
        </div>
        
        <div class="content">
            <div class="system-stats">
                <h2 class="stats-title">System Overview</h2>
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-value">{{ service_count }}</div>
                        <div class="stat-label">Active Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ metrics_count }}</div>
                        <div class="stat-label">Metrics Collected</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ anomaly_count }}</div>
                        <div class="stat-label">Active Anomalies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ remediation_count }}</div>
                        <div class="stat-label">Remediation Actions</div>
                    </div>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab" id="tab-overview" onclick="changeTab('overview')">Overview</div>
                <div class="tab" id="tab-services" onclick="changeTab('services')">Services</div>
                <div class="tab" id="tab-anomalies" onclick="changeTab('anomalies')">Anomalies</div>
                <div class="tab" id="tab-remediation" onclick="changeTab('remediation')">Remediation</div>
            </div>
            
            <!-- Overview Tab -->
            <div id="overview" class="tab-content">
                {% if anomaly_count > 0 %}
                <div class="section alert-card">
                    <h3 class="section-title">
                        Current Alerts
                        <span class="date-display">Last updated: {{ current_time }}</span>
                    </h3>
                    <div class="section-content">
                        <table>
                            <tr>
                                <th>Service</th>
                                <th>Metric</th>
                                <th>Value</th>
                                <th>Severity</th>
                                <th>Detected At</th>
                            </tr>
                            {% for anomaly in recent_anomalies %}
                            <tr class="highlight">
                                <td>
                                    <span class="status-indicator status-{{ 'critical' if anomaly.severity == 'high' else 'warning' if anomaly.severity == 'medium' else 'good' }}"></span>
                                    {{ anomaly.service }}
                                </td>
                                <td>{{ anomaly.metric }}</td>
                                <td>{{ "%.2f"|format(anomaly.value) }}</td>
                                <td class="severity-{{ anomaly.severity }}">{{ anomaly.severity }}</td>
                                <td>{{ anomaly.timestamp }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>
                {% endif %}
                
                <div class="section">
                    <h3 class="section-title">Service Health Overview</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/service_health.png" alt="Service Health">
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Anomaly Distribution</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/anomaly_distribution.png" alt="Anomaly Distribution">
                        </div>
                    </div>
                </div>
                
                {% if anomalies %}
                <div class="section">
                    <h3 class="section-title">Anomalies Over Time</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/anomalies_time.png" alt="Anomalies Over Time">
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
            
            <!-- Services Tab -->
            <div id="services" class="tab-content">
                <div class="section">
                    <h3 class="section-title">
                        Service Status
                        <span class="date-display">Last updated: {{ current_time }}</span>
                    </h3>
                    <div class="section-content">
                        <div class="service-card-container">
                            {% for service in services %}
                            <div class="service-card">
                                <div class="service-header">
                                    <span>{{ service }}</span>
                                    {% set health = service_health.get(service, 0) %}
                                    <span class="status-indicator status-{{ 'good' if health >= 80 else 'warning' if health >= 60 else 'critical' }}"></span>
                                </div>
                                <div class="service-content">
                                    <table>
                                        {% for metric in metrics %}
                                        <tr>
                                            <td>{{ metric }}</td>
                                            <td>{{ latest_metrics.get(service, {}).get(metric, 'N/A') }}</td>
                                        </tr>
                                        {% endfor %}
                                    </table>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">CPU Usage Trends</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/cpu_usage_trends.png" alt="CPU Usage Trends">
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Memory Usage Trends</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/memory_usage_trends.png" alt="Memory Usage Trends">
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Response Time Trends</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/response_time_trends.png" alt="Response Time Trends">
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Anomalies Tab -->
            <div id="anomalies" class="tab-content">
                <div class="section">
                    <h3 class="section-title">
                        Detected Anomalies
                        <span class="date-display">Last updated: {{ current_time }}</span>
                    </h3>
                    <div class="section-content">
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
                                <td>
                                    <span class="status-indicator status-{{ 'critical' if anomaly.severity == 'high' else 'warning' if anomaly.severity == 'medium' else 'good' }}"></span>
                                    {{ anomaly.service }}
                                </td>
                                <td>{{ anomaly.metric }}</td>
                                <td>{{ "%.2f"|format(anomaly.value) }}</td>
                                <td class="severity-{{ anomaly.severity }}">{{ anomaly.severity }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                        {% else %}
                        <div class="empty-state">
                            <h4>No anomalies detected</h4>
                            <p>The system is currently not detecting any anomalies across the monitored services.</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Anomalies Over Time</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/anomalies_time.png" alt="Anomalies Over Time">
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Remediation Tab -->
            <div id="remediation" class="tab-content">
                <div class="section">
                    <h3 class="section-title">
                        Remediation Actions
                        <span class="date-display">Last updated: {{ current_time }}</span>
                    </h3>
                    <div class="section-content">
                        {% if remediations %}
                        <table>
                            <tr>
                                <th>Timestamp</th>
                                <th>Service</th>
                                <th>Issue</th>
                                <th>Action Taken</th>
                                <th>Duration (s)</th>
                            </tr>
                            {% for remediation in remediations %}
                            <tr>
                                <td>{{ remediation.timestamp }}</td>
                                <td>{{ remediation.anomaly.service }}</td>
                                <td>
                                    {{ remediation.anomaly.metric }} 
                                    <span class="severity-{{ remediation.anomaly.severity }}">({{ remediation.anomaly.severity }})</span>
                                </td>
                                <td>{{ remediation.action }}</td>
                                <td>{{ "%.2f"|format(remediation.duration) }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                        {% else %}
                        <div class="empty-state">
                            <h4>No remediation actions taken</h4>
                            <p>The system has not executed any remediation actions yet.</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Remediation Effectiveness</h3>
                    <div class="section-content">
                        <div class="chart-container">
                            <img src="/static/remediation_effectiveness.png" alt="Remediation Effectiveness">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>AI-Driven Operational Intelligence &copy; 2025</p>
            </div>
        </div>
    </body>
    </html>
    """