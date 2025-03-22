#!/usr/bin/env python3
"""
AI-Driven Operational Intelligence & Incident Remediation
Main entry point for the cloud monitoring system
"""
import os
import logging
import threading
import yaml
import time
import argparse
from components.metrics.simulator import CloudMetricsSimulator
from components.ml.anomaly import AnomalyDetector
from components.remediation.engine import RemediationEngine
from components.streaming.kafka import KafkaSimulator
from components.pipeline.kubeflow import KubeflowPipeline
from components.pipeline.ray import RaySimulator
from components.monitoring.prometheus import setup_prometheus_metrics
from components.monitoring.dashboard import create_dashboard_app, update_plots
import mlflow

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

def setup_mlflow(enable_mlflow=False):
    """Setup MLflow tracking if enabled"""
    if not enable_mlflow:
        logger.info("MLflow tracking disabled")
        return None
        
    mlflow_config = config['monitoring']['mlflow']
    mlflow.set_tracking_uri(mlflow_config['tracking_uri'])
    
    # Create experiment if it doesn't exist
    experiment_name = mlflow_config['experiment_name']
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
        logger.info(f"Created MLflow experiment: {experiment_name}")
    except:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        experiment_id = experiment.experiment_id
        logger.info(f"Using existing MLflow experiment: {experiment_name}")
    
    return experiment_id

def run_monitoring_pipeline(experiment_id):
    """Main monitoring pipeline that orchestrates all components"""
    global metrics_data, anomalies, remediation_history, is_running
    
    # Initialize components
    ray = RaySimulator(num_workers=config['pipeline']['ray']['num_workers'])
    kafka = KafkaSimulator(topics=config['streaming']['kafka']['topics'])
    simulator = CloudMetricsSimulator(config['services'], config['simulation'])
    detector = AnomalyDetector(config['ml'], experiment_id)
    remediation = RemediationEngine(config['remediation'])
    
    # Setup Prometheus metrics
    start_prometheus, metric_collectors = setup_prometheus_metrics(
        config['monitoring']['prometheus']['port']
    )
    prometheus_thread = threading.Thread(target=start_prometheus)
    prometheus_thread.daemon = True
    prometheus_thread.start()
    
    # Create Kubeflow pipeline
    pipeline = KubeflowPipeline(config['pipeline']['kubeflow']['pipeline_name'])
    
    # Define pipeline steps
    def initialize_data():
        """Initialize system with training data"""
        logger.info("Collecting initial training data...")
        
        initial_data = []
        for _ in range(20):
            # Generate metrics using Ray
            batch_id = simulator.generate_metrics_batch()
            try:
                batch_data = ray.get(batch_id)
                if isinstance(batch_data, tuple):
                    batch_data = list(batch_data)
                initial_data.extend(batch_data)
                
                # Update Prometheus metrics
                for item in batch_data:
                    service = item['service']
                    metric_name = item['metric']
                    value = item['value']
                    metric_collectors['service_metric'].labels(service=service, metric=metric_name).set(value)
            except Exception as e:
                logger.error(f"Error processing batch data: {str(e)}")
            
            time.sleep(0.1)
            
        logger.info(f"Collected {len(initial_data)} initial data points")
        return initial_data
    
    def train_models(data):
        """Train anomaly detection models"""
        logger.info("Training anomaly detection models...")
        detector.train(data)
        return detector
    
    def start_kafka_consumers():
        """Start Kafka consumers"""
        consumer_ids = []
        
        # Metrics consumer
        def process_metrics(message):
            metrics_data.append(message)
            # Limit data points to prevent memory issues
            if len(metrics_data) > 1000:
                metrics_data.pop(0)
        
        # Anomaly consumer
        def process_anomalies(message):
            anomalies.append(message)
            # Limit stored anomalies
            if len(anomalies) > 100:
                anomalies.pop(0)
        
        # Remediation consumer
        def process_remediations(message):
            remediation_history.append(message)
            # Limit stored remediation history
            if len(remediation_history) > 100:
                remediation_history.pop(0)
        
        # Register consumers
        consumer_ids.append(
            kafka.consume('metrics', config['streaming']['kafka']['consumer_groups']['metrics_processor'], process_metrics)
        )
        
        consumer_ids.append(
            kafka.consume('anomalies', config['streaming']['kafka']['consumer_groups']['anomaly_detector'], process_anomalies)
        )
        
        consumer_ids.append(
            kafka.consume('remediation', config['streaming']['kafka']['consumer_groups']['remediation_engine'], process_remediations)
        )
        
        logger.info(f"Started {len(consumer_ids)} Kafka consumers")
        return consumer_ids
    
    # Add pipeline steps
    pipeline.add_step("Initialize Data", initialize_data)
    pipeline.add_step("Train Models", train_models, data=pipeline.steps[0]['result'])
    pipeline.add_step("Start Kafka Consumers", start_kafka_consumers)
    
    # Run pipeline
    pipeline.run()
    
    # Start a thread to update dashboard plots
    plots_thread = threading.Thread(
        target=lambda: update_plots(metrics_data, anomalies, remediation_history, config) if metrics_data else None,
        daemon=True
    )
    plots_thread.start()
    
    logger.info("Starting main monitoring loop")
    
    # Main monitoring loop
    try:
        while is_running:
            try:
                # Generate new metrics using Ray
                batch_id = simulator.generate_metrics_batch()
                batch_data = ray.get(batch_id)
                if isinstance(batch_data, tuple):
                    batch_data = list(batch_data)
                
                if batch_data:
                    # Produce to Kafka
                    for item in batch_data:
                        kafka.produce('metrics', item)
                        
                        # Update Prometheus metrics
                        metric_collectors['service_metric'].labels(
                            service=item['service'], 
                            metric=item['metric']
                        ).set(item['value'])
                    
                    # Detect anomalies
                    new_anomalies = detector.detect(batch_data)
                    
                    if new_anomalies:
                        # Update anomaly counter
                        for anomaly in new_anomalies:
                            metric_collectors['anomaly_counter'].labels(
                                service=anomaly['service'], 
                                metric=anomaly['metric']
                            ).inc()
                            
                            # Produce to Kafka
                            kafka.produce('anomalies', anomaly)
                        
                        # Apply remediation
                        for anomaly in new_anomalies:
                            # Apply remediation action
                            remediation_result = remediation.remediate(anomaly)
                            
                            if remediation_result:
                                # Update remediation counter
                                metric_collectors['remediation_counter'].labels(
                                    service=remediation_result['anomaly']['service'],
                                    action_type=remediation_result['anomaly']['metric']
                                ).inc()
                                
                                # Produce to Kafka
                                kafka.produce('remediation', remediation_result)
                
                # Periodically retrain model
                if random.random() < config['ml']['training']['retrain_probability']:
                    if len(metrics_data) >= config['ml']['training']['min_samples']:
                        detector.train(metrics_data)
                
                # Sleep for the configured interval
                time.sleep(config['simulation']['interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        is_running = False

def main():
    """Main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Cloud Monitoring System")
    parser.add_argument("--enable-mlflow", action="store_true", help="Enable MLflow tracking")
    parser.add_argument("--dashboard-port", type=int, default=5050, help="Dashboard port")
    args = parser.parse_args()
    
    print("=" * 80)
    print("AI-Driven Operational Intelligence & Incident Remediation")
    print("=" * 80)
    print("Components:")
    print("  - MLOps: Kubeflow (pipeline), Ray (distributed)")
    if args.enable_mlflow:
        print("  - MLflow: Enabled (experiment tracking)")
    else:
        print("  - MLflow: Disabled")
    print("  - Streaming: Kafka for real-time event processing")
    print("  - Monitoring: Prometheus metrics + Web Dashboard")
    print("  - AI Models: Isolation Forest + GPT (if configured)")
    
    # Update dashboard port in config
    config['monitoring']['dashboard']['port'] = args.dashboard_port
    
    # Setup MLflow if enabled
    experiment_id = setup_mlflow(args.enable_mlflow)
    
    # Setup Dashboard
    dashboard_app = create_dashboard_app(config, metrics_data, anomalies, remediation_history)
    dashboard_thread = threading.Thread(
        target=lambda: dashboard_app.run(
            host='0.0.0.0', 
            port=args.dashboard_port
        )
    )
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    print(f"\nDashboard: http://localhost:{args.dashboard_port}")
    print(f"Prometheus: http://localhost:{config['monitoring']['prometheus']['port']}")
    if args.enable_mlflow:
        print(f"MLflow UI:  Use 'mlflow ui --port=5001' in another terminal")
    print("=" * 80)
    
    # Check GPT configuration
    if config['remediation']['use_gpt'] and not os.environ.get('OPENAI_API_KEY'):
        print("\nTo enable GPT-based remediation suggestions, set your OpenAI API key:")
        print("  export OPENAI_API_KEY=your_key_here")
    
    # Start monitoring pipeline
    run_monitoring_pipeline(experiment_id)

if __name__ == "__main__":
    import random  # Import here to avoid pep8 warning
    main()