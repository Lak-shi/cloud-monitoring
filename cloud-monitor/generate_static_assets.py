#!/usr/bin/env python3
"""
Generate static assets for the dashboard.
This script creates visualization images to display on the dashboard.
"""
import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_dir(directory):
    """Ensure directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def load_sample_data():
    """
    Load sample data from data directory.
    
    Returns:
        tuple: (metrics_df, anomalies, remediations)
    """
    # Find the most recent files
    metrics_files = sorted(glob.glob("data/metrics_*.csv"))
    anomalies_files = sorted(glob.glob("data/anomalies_*.json"))
    remediations_files = sorted(glob.glob("data/remediations_*.json"))
    
    metrics_df = None
    anomalies = []
    remediations = []
    
    # Load metrics
    if metrics_files:
        latest_metrics = metrics_files[-1]
        logger.info(f"Loading metrics from {latest_metrics}")
        metrics_df = pd.read_csv(latest_metrics)
    else:
        logger.warning("No metrics files found.")
    
    # Load anomalies
    if anomalies_files:
        latest_anomalies = anomalies_files[-1]
        logger.info(f"Loading anomalies from {latest_anomalies}")
        with open(latest_anomalies, 'r') as f:
            anomalies = json.load(f)
    else:
        logger.warning("No anomalies files found.")
    
    # Load remediations
    if remediations_files:
        latest_remediations = remediations_files[-1]
        logger.info(f"Loading remediations from {latest_remediations}")
        with open(latest_remediations, 'r') as f:
            remediations = json.load(f)
    else:
        logger.warning("No remediations files found.")
    
    return metrics_df, anomalies, remediations

def create_service_health_plot(metrics_df, output_file):
    """
    Create service health plot.
    
    Args:
        metrics_df (DataFrame): Metrics data
        output_file (str): Output file path
    """
    if metrics_df is None or metrics_df.empty:
        logger.warning("No metrics data available for service health plot.")
        return
    
    plt.figure(figsize=(12, 6))
    
    # Get the latest data point for each service/metric
    latest_data = metrics_df.groupby(['service', 'metric']).last().reset_index()
    
    # Calculate health score for each service
    services = latest_data['service'].unique()
    health_scores = []
    
    for service in services:
        service_data = latest_data[latest_data['service'] == service]
        
        # Get relevant metrics
        cpu_usage = service_data[service_data['metric'] == 'cpu_usage']['value'].values[0] if 'cpu_usage' in service_data['metric'].values else 50
        memory_usage = service_data[service_data['metric'] == 'memory_usage']['value'].values[0] if 'memory_usage' in service_data['metric'].values else 50
        error_rate = service_data[service_data['metric'] == 'error_rate']['value'].values[0] if 'error_rate' in service_data['metric'].values else 1
        
        # Calculate health score (100 = perfectly healthy)
        # Lower CPU, memory, and error rate are better
        health_score = 100 - (cpu_usage * 0.4 + memory_usage * 0.4 + error_rate * 10)
        health_score = max(0, min(100, health_score))  # Clamp to 0-100
        
        health_scores.append(health_score)
    
    # Sort by health score
    sorted_indices = np.argsort(health_scores)
    sorted_services = [services[i] for i in sorted_indices]
    sorted_scores = [health_scores[i] for i in sorted_indices]
    
    # Create bar colors based on health
    colors = []
    for score in sorted_scores:
        if score >= 80:
            colors.append('green')
        elif score >= 60:
            colors.append('yellowgreen')
        elif score >= 40:
            colors.append('orange')
        else:
            colors.append('red')
    
    # Plot bars
    plt.barh(sorted_services, sorted_scores, color=colors)
    
    plt.title('Service Health Overview')
    plt.xlabel('Health Score (%)')
    plt.xlim(0, 100)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, v in enumerate(sorted_scores):
        plt.text(v + 1, i, f"{v:.1f}%", va='center')
    
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    
    logger.info(f"Created service health plot: {output_file}")

def create_metric_trend_plots(metrics_df, output_dir):
    """
    Create trend plots for each metric.
    
    Args:
        metrics_df (DataFrame): Metrics data
        output_dir (str): Output directory
    """
    if metrics_df is None or metrics_df.empty:
        logger.warning("No metrics data available for trend plots.")
        return
    
    # Convert timestamp to datetime
    metrics_df['datetime'] = pd.to_datetime(metrics_df['timestamp'])
    
    # Create plots for each metric
    metrics = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate', 'request_count']
    
    for metric in metrics:
        plt.figure(figsize=(12, 6))
        
        # Filter data for this metric
        metric_data = metrics_df[metrics_df['metric'] == metric]
        
        if metric_data.empty:
            logger.warning(f"No data for metric: {metric}")
            continue
        
        # Group by service and datetime
        for service in metric_data['service'].unique():
            service_data = metric_data[metric_data['service'] == service]
            
            # Sort by datetime
            service_data = service_data.sort_values('datetime')
            
            # Plot the trend
            plt.plot(service_data['datetime'], service_data['value'], label=service, linewidth=2, alpha=0.7)
        
        # Determine appropriate title and y-axis label
        if metric == 'cpu_usage':
            title = 'CPU Usage Trends'
            ylabel = 'CPU Usage (%)'
        elif metric == 'memory_usage':
            title = 'Memory Usage Trends'
            ylabel = 'Memory Usage (%)'
        elif metric == 'response_time':
            title = 'Response Time Trends'
            ylabel = 'Response Time (ms)'
        elif metric == 'error_rate':
            title = 'Error Rate Trends'
            ylabel = 'Error Rate (%)'
        else:  # request_count
            title = 'Request Count Trends'
            ylabel = 'Requests per Minute'
        
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(linestyle='--', alpha=0.7)
        
        # Format x-axis
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save plot
        output_file = os.path.join(output_dir, f"{metric}_trends.png")
        plt.savefig(output_file)
        plt.close()
        
        logger.info(f"Created trend plot for {metric}: {output_file}")

def create_anomaly_distribution_plot(anomalies, output_file):
    """
    Create anomaly distribution plot.
    
    Args:
        anomalies (list): Anomaly data
        output_file (str): Output file path
    """
    if not anomalies:
        logger.warning("No anomaly data available for distribution plot.")
        return
    
    plt.figure(figsize=(12, 6))
    
    # Convert to DataFrame
    anomalies_df = pd.DataFrame(anomalies)
    
    # Count anomalies by service and severity
    anomaly_counts = anomalies_df.groupby(['service', 'severity']).size().unstack(fill_value=0)
    
    # Ensure all severity levels exist
    for level in ['low', 'medium', 'high']:
        if level not in anomaly_counts.columns:
            anomaly_counts[level] = 0
    
    # Sort by total number of anomalies
    anomaly_counts['total'] = anomaly_counts.sum(axis=1)
    anomaly_counts = anomaly_counts.sort_values('total', ascending=False)
    anomaly_counts = anomaly_counts.drop('total', axis=1)
    
    # Create stacked bar chart
    anomaly_counts.plot(kind='bar', stacked=True, 
                        color={'low': 'green', 'medium': 'orange', 'high': 'red'},
                        alpha=0.7, ax=plt.gca())
    
    plt.title('Anomaly Distribution by Service and Severity')
    plt.xlabel('Service')
    plt.ylabel('Number of Anomalies')
    plt.legend(title='Severity')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    
    logger.info(f"Created anomaly distribution plot: {output_file}")

def create_remediation_effectiveness_plot(anomalies, remediations, output_file):
    """
    Create remediation effectiveness plot.
    
    Args:
        anomalies (list): Anomaly data
        remediations (list): Remediation data
        output_file (str): Output file path
    """
    if not anomalies or not remediations:
        logger.warning("Insufficient data for remediation effectiveness plot.")
        return
    
    plt.figure(figsize=(12, 6))
    
    # Count anomalies by service
    anomalies_df = pd.DataFrame(anomalies)
    anomaly_counts = anomalies_df['service'].value_counts()
    
    # Count remediations by service
    remediation_services = [r['anomaly']['service'] for r in remediations]
    remediation_df = pd.DataFrame({'service': remediation_services})
    remediation_counts = remediation_df['service'].value_counts()
    
    # Get combined list of services
    services = list(set(anomaly_counts.index) | set(remediation_counts.index))
    
    # Prepare data for plot
    service_data = []
    for service in services:
        a_count = anomaly_counts.get(service, 0)
        r_count = remediation_counts.get(service, 0)
        
        # Calculate remediation rate
        if a_count > 0:
            rate = min(100, (r_count / a_count) * 100)
        else:
            rate = 0
            
        service_data.append({
            'service': service,
            'anomalies': a_count,
            'remediations': r_count,
            'rate': rate
        })
    
    # Convert to DataFrame and sort
    service_df = pd.DataFrame(service_data)
    service_df = service_df.sort_values('rate', ascending=False)
    
    # Create plot
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot bars for counts
    x = np.arange(len(service_df))
    width = 0.35
    
    ax1.bar(x - width/2, service_df['anomalies'], width, label='Anomalies', color='red', alpha=0.7)
    ax1.bar(x + width/2, service_df['remediations'], width, label='Remediations', color='green', alpha=0.7)
    
    ax1.set_xlabel('Service')
    ax1.set_ylabel('Count')
    ax1.set_title('Remediation Effectiveness by Service')
    ax1.set_xticks(x)
    ax1.set_xticklabels(service_df['service'], rotation=45, ha='right')
    ax1.legend(loc='upper left')
    
    # Plot line for remediation rate
    ax2 = ax1.twinx()
    ax2.plot(x, service_df['rate'], 'b-', marker='o', label='Remediation Rate')
    ax2.set_ylabel('Remediation Rate (%)')
    ax2.set_ylim(0, 105)
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    
    logger.info(f"Created remediation effectiveness plot: {output_file}")

def create_model_performance_plot(anomalies, remediations, output_file):
    """
    Create model performance plot.
    
    Args:
        anomalies (list): Anomalies
        remediations (list): Remediation history
        output_file (str): Output file path
    """
    try:
        plt.figure(figsize=(12, 6))
        
        # Calculate remediation success rate by service and metric
        service_metric_success = {}
        
        for r in remediations:
            service = r['anomaly']['service']
            metric = r['anomaly']['metric']
            successful = r.get('successful', True)  # Default to True if not specified
            
            # Use a tuple as key instead of a string with underscore
            key = (service, metric)
            if key not in service_metric_success:
                service_metric_success[key] = {'total': 0, 'successful': 0}
                
            service_metric_success[key]['total'] += 1
            if successful:
                service_metric_success[key]['successful'] += 1
        
        # Calculate success rates
        services = []
        metrics = []
        success_rates = []
        
        for key, data in service_metric_success.items():
            if data['total'] > 0:
                # Unpack the tuple directly
                service, metric = key
                services.append(service)
                metrics.append(metric)
                success_rates.append((data['successful'] / data['total']) * 100)
        
        # Create DataFrame
        performance_df = pd.DataFrame({
            'service': services,
            'metric': metrics,
            'success_rate': success_rates
        })
        
        # Create a 2D matrix of service vs metric with success rate as values
        pivot_df = performance_df.pivot_table(
            index='service', 
            columns='metric', 
            values='success_rate',
            aggfunc='mean'
        ).fillna(0)
        
        # Check if pivot_df is empty
        if pivot_df.empty:
            logger.warning("Not enough data for model performance plot")
            # Create a simple placeholder plot
            plt.text(0.5, 0.5, 'Insufficient data for model performance visualization', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.tight_layout()
            plt.savefig(output_file)
            plt.close()
            return
        
        # Plot heatmap
        plt.subplot(1, 1, 1)
        im = plt.imshow(pivot_df.values, cmap='YlGn', vmin=0, vmax=100)
        
        # Add colorbar
        cbar = plt.colorbar(im)
        cbar.set_label('Success Rate (%)')
        
        # Setup axes
        plt.xticks(range(len(pivot_df.columns)), pivot_df.columns, rotation=45)
        plt.yticks(range(len(pivot_df.index)), pivot_df.index)
        
        # Add text annotations
        for i in range(len(pivot_df.index)):
            for j in range(len(pivot_df.columns)):
                value = pivot_df.iloc[i, j]
                plt.text(j, i, f"{value:.1f}%", ha='center', va='center',
                         color='black' if value > 50 else 'white')
        
        plt.title('Model Performance: Remediation Success Rate by Service and Metric')
        plt.tight_layout()
        
        plt.savefig(output_file)
        plt.close()
        
        logger.info(f"Created model performance plot: {output_file}")
    except Exception as e:
        logger.error(f"Error creating model performance plot: {str(e)}")
        # Create a basic error plot
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, f'Error creating performance plot: {str(e)}', 
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, color='red')
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()

def main():
    """Main function."""
    # Ensure directories exist
    ensure_dir('static')
    
    # Load sample data
    metrics_df, anomalies, remediations = load_sample_data()
    
    # Create service health plot
    create_service_health_plot(metrics_df, "static/service_health.png")
    
    # Create metric trend plots
    create_metric_trend_plots(metrics_df, "static")
    
    # Create anomaly distribution plot
    create_anomaly_distribution_plot(anomalies, "static/anomaly_distribution.png")
    
    # Create remediation effectiveness plot
    create_remediation_effectiveness_plot(anomalies, remediations, "static/remediation_effectiveness.png")
    
    # Create model performance plot
    create_model_performance_plot(anomalies, remediations, "static/model_performance.png")
    
    print(f"\nStatic assets generation complete!")
    print(f"All visualization images saved to the 'static' directory.")

if __name__ == "__main__":
    main()