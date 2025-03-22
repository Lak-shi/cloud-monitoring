"""
GPT integration module for AI-powered remediation suggestions.
"""
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger('cloud-monitor.remediation')

class GPTAdvisor:
    """
    Integrates with OpenAI's GPT models for remediation suggestions.
    
    Features:
    - Provides context-aware remediation suggestions
    - Handles API errors gracefully
    - Caches similar requests to reduce API costs
    """
    
    def __init__(self, config):
        """
        Initialize the GPT advisor.
        
        Args:
            config (dict): GPT configuration
        """
        self.config = config
        self.openai_client = None
        self.cache = {}  # Simple request cache
        self.cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        
        # Try to initialize OpenAI client
        try:
            import openai
            api_key = os.environ.get('OPENAI_API_KEY')
            
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("Initialized GPT advisor with OpenAI API")
            else:
                logger.warning("GPT advisor initialized without API key")
        except ImportError:
            logger.warning("OpenAI package not installed, GPT suggestions unavailable")
    
    def get_suggestion(self, anomaly):
        """
        Get remediation suggestion from GPT for an anomaly.
        
        Args:
            anomaly (dict): Anomaly data
            
        Returns:
            dict: Suggestion result
        """
        if not self.openai_client:
            return {
                'success': False,
                'error': 'OpenAI client not initialized',
                'suggestion': None,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate cache key
        cache_key = f"{anomaly['service']}_{anomaly['metric']}_{anomaly['severity']}"
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
            
            # Return cached suggestion if still valid
            if cache_age < self.cache_ttl:
                logger.debug(f"Using cached GPT suggestion for {cache_key}")
                return cache_entry['result']
        
        # Create prompt
        prompt = self._create_prompt(anomaly)
        
        try:
            # Call OpenAI API
            start_time = time.time()
            
            response = self.openai_client.Completion.create(
                engine=self.config['model'],
                prompt=prompt,
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature']
            )
            
            duration = time.time() - start_time
            
            # Extract suggestion
            suggestion = response.choices[0].text.strip()
            
            result = {
                'success': True,
                'suggestion': suggestion,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self.cache[cache_key] = {
                'timestamp': datetime.now(),
                'result': result
            }
            
            logger.info(f"Got GPT suggestion for {anomaly['service']}/{anomaly['metric']} in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error getting GPT suggestion: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'suggestion': None,
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_prompt(self, anomaly):
        """
        Create a prompt for GPT based on anomaly data.
        
        Args:
            anomaly (dict): Anomaly data
            
        Returns:
            str: GPT prompt
        """
        service = anomaly['service']
        metric = anomaly['metric']
        value = anomaly['value']
        severity = anomaly['severity']
        
        # Get metric description
        metric_descriptions = {
            'cpu_usage': 'CPU utilization percentage',
            'memory_usage': 'memory utilization percentage',
            'response_time': 'API response time in milliseconds',
            'error_rate': 'percentage of requests resulting in errors',
            'request_count': 'number of incoming requests per minute'
        }
        
        metric_desc = metric_descriptions.get(metric, metric)
        
        # Build context-rich prompt
        prompt = f"""
        I've detected an anomaly in our cloud services:
        
        Service: {service}
        Metric: {metric_desc}
        Current Value: {value}
        Severity: {severity}
        
        As a cloud operations expert, what would be the best remediation action to take?
        Please provide a specific, actionable recommendation that addresses the root cause.
        Focus on practical steps that could be implemented immediately to resolve the issue.
        """
        
        return prompt