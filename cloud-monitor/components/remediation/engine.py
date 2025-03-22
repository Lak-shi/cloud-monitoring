"""
Remediation engine module for automatic incident response.
Applies appropriate remediation actions based on detected anomalies.
"""
import os
import time
import logging
from datetime import datetime
import mlflow

logger = logging.getLogger('cloud-monitor.remediation')

class RemediationEngine:
    """
    Remediation engine that applies actions based on detected anomalies.
    
    Features:
    - Service and metric-specific remediation actions
    - Severity-based response selection
    - Optional GPT integration for complex scenarios
    - Tracking and evaluation of remediation effectiveness
    """
    
    def __init__(self, remediation_config):
        """
        Initialize the remediation engine.
        
        Args:
            remediation_config (dict): Remediation configuration parameters
        """
        self.config = remediation_config
        self.use_gpt = remediation_config['use_gpt']
        self.action_templates = remediation_config['actions']
        
        # Initialize GPT if configured
        self.gpt_client = None
        if self.use_gpt:
            try:
                import openai
                openai_api_key = os.environ.get('OPENAI_API_KEY')
                if openai_api_key:
                    openai.api_key = openai_api_key
                    self.gpt_client = openai
                    logger.info("GPT integration enabled for remediation suggestions")
                else:
                    logger.warning("GPT integration requested but no API key found")
                    self.use_gpt = False
            except ImportError:
                logger.warning("GPT integration requested but openai package not installed")
                self.use_gpt = False
        
        logger.info("Initialized remediation engine")
    
    def remediate(self, anomaly):
        """
        Apply remediation action based on anomaly.
        
        Args:
            anomaly (dict): Anomaly information
        
        Returns:
            dict: Remediation record or None if no action taken
        """
        service = anomaly['service']
        metric = anomaly['metric']
        severity = anomaly['severity']
        value = anomaly['value']
        
        start_time = time.time()
        
        # Get GPT suggestion if enabled
        gpt_suggestion = None
        if self.use_gpt and self.gpt_client:
            try:
                gpt_suggestion = self._get_gpt_suggestion(anomaly)
            except Exception as e:
                logger.error(f"Error getting GPT suggestion: {str(e)}")
        
        # Get action from template based on metric and severity
        action_taken = None
        if metric in self.action_templates and severity in self.action_templates[metric]:
            action_template = self.action_templates[metric][severity]
            action_taken = action_template.format(service=service)
        else:
            logger.warning(f"No action template for {metric}/{severity}")
            return None
        
        # Calculate duration
        duration = time.time() - start_time
        
        if action_taken:
            # Create remediation record
            remediation_record = {
                'timestamp': datetime.now().isoformat(),
                'anomaly': anomaly,
                'action': action_taken,
                'gpt_suggestion': gpt_suggestion,
                'duration': duration
            }
            
            logger.info(f"Applied remediation: {action_taken} for {service} ({metric})")
            
            # Log to MLflow if we have the right imports
            try:
                with mlflow.start_run(run_name=f"remediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                    mlflow.log_param("service", service)
                    mlflow.log_param("metric", metric)
                    mlflow.log_param("severity", severity)
                    mlflow.log_param("value", value)
                    mlflow.log_param("action", action_taken)
                    mlflow.log_metric("remediation_duration", duration)
                    if gpt_suggestion:
                        mlflow.log_param("gpt_suggestion", gpt_suggestion)
            except Exception as e:
                logger.warning(f"Error logging remediation to MLflow: {str(e)}")
            
            return remediation_record
        
        return None
    
    def _get_gpt_suggestion(self, anomaly):
        """Get remediation suggestion from GPT."""
        if not self.gpt_client:
            return None
        
        try:
            # Construct prompt
            prompt = f"""
            I've detected an anomaly in our cloud services:
            - Service: {anomaly['service']}
            - Metric: {anomaly['metric']}
            - Current Value: {anomaly['value']}
            - Severity: {anomaly['severity']}
            
            What would be the best remediation action to take? Give a specific, actionable recommendation.
            """
            
            # Call GPT API
            response = self.gpt_client.Completion.create(
                engine=self.config['gpt']['model'],
                prompt=prompt,
                max_tokens=self.config['gpt']['max_tokens'],
                temperature=self.config['gpt']['temperature']
            )
            
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"Error in GPT suggestion: {str(e)}")
            return None