"""
Metrics collector module for storing and processing metrics data.
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import json

logger = logging.getLogger('cloud-monitor.metrics')

class MetricsCollector:
    """
    Collects and stores metrics data from various sources.
    
    Features:
    - In-memory metrics storage
    - CSV/JSON data export
    - Data filtering and aggregation
    """
    
    def __init__(self, data_dir):
        """
        Initialize the metrics collector.
        
        Args:
            data_dir (str): Directory to store exported data
        """
        self.data_dir = data_dir
        self.metrics = []
        self.max_stored_metrics = 10000  # Limit to prevent memory issues
        logger.info(f"Initialized metrics collector with storage in {data_dir}")
    
    def add_metrics(self, metrics_batch):
        """
        Add a batch of metrics to the collector.
        
        Args:
            metrics_batch (list): List of metric data points
            
        Returns:
            int: Number of metrics added
        """
        if not metrics_batch:
            return 0
            
        # Add metrics to the collection
        self.metrics.extend(metrics_batch)
        
        # Trim to maximum size if needed
        if len(self.metrics) > self.max_stored_metrics:
            self.metrics = self.metrics[-self.max_stored_metrics:]
            
        logger.debug(f"Added {len(metrics_batch)} metrics, total stored: {len(self.metrics)}")
        return len(metrics_batch)
    
    def get_metrics(self, service=None, metric=None, start_time=None, end_time=None, limit=None):
        """
        Get metrics with optional filtering.
        
        Args:
            service (str, optional): Filter by service name
            metric (str, optional): Filter by metric name
            start_time (str, optional): Filter by start time
            end_time (str, optional): Filter by end time
            limit (int, optional): Limit number of results
            
        Returns:
            list: Filtered metrics
        """
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(self.metrics)
        
        if df.empty:
            return []
            
        # Apply filters
        if service:
            df = df[df['service'] == service]
            
        if metric:
            df = df[df['metric'] == metric]
            
        if start_time:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df = df[df['datetime'] >= pd.to_datetime(start_time)]
            
        if end_time:
            if 'datetime' not in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'])
            df = df[df['datetime'] <= pd.to_datetime(end_time)]
            
        # Apply limit
        if limit and limit > 0:
            df = df.tail(limit)
            
        # Convert back to list of dictionaries
        if 'datetime' in df.columns:
            df = df.drop('datetime', axis=1)
            
        return df.to_dict('records')
    
    def export_metrics(self, format='csv', filename=None):
        """
        Export metrics to file.
        
        Args:
            format (str): Export format ('csv' or 'json')
            filename (str, optional): Output filename
            
        Returns:
            str: Path to exported file
        """
        if not self.metrics:
            logger.warning("No metrics to export")
            return None
            
        # Create default filename if not provided
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"metrics_{timestamp}.{format}"
            
        # Create full path
        filepath = os.path.join(self.data_dir, filename)
        
        # Convert to DataFrame
        df = pd.DataFrame(self.metrics)
        
        # Export based on format
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False)
        elif format.lower() == 'json':
            df.to_json(filepath, orient='records')
        else:
            logger.error(f"Unsupported export format: {format}")
            return None
            
        logger.info(f"Exported {len(self.metrics)} metrics to {filepath}")
        return filepath
    
    def get_statistics(self):
        """
        Get statistics about collected metrics.
        
        Returns:
            dict: Statistics about metrics
        """
        if not self.metrics:
            return {
                'count': 0,
                'services': [],
                'metrics': [],
                'time_range': None
            }
            
        # Convert to DataFrame
        df = pd.DataFrame(self.metrics)
        
        # Convert timestamps to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'])
        
        # Calculate statistics
        stats = {
            'count': len(df),
            'services': df['service'].unique().tolist(),
            'metrics': df['metric'].unique().tolist(),
            'time_range': {
                'start': df['datetime'].min().isoformat(),
                'end': df['datetime'].max().isoformat(),
                'duration_seconds': (df['datetime'].max() - df['datetime'].min()).total_seconds()
            }
        }
        
        return stats