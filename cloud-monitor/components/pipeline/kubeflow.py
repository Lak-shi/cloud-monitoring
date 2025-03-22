"""
Kubeflow pipeline simulator module.
Simulates Kubeflow pipelines for orchestrating ML workflows.
"""
import uuid
import logging
import time
from datetime import datetime

logger = logging.getLogger('cloud-monitor.pipeline')

class KubeflowPipeline:
    """
    Simulates Kubeflow pipeline for orchestrating ML workflows.
    
    Features:
    - Step-based pipeline definition
    - Sequential execution of steps
    - Status tracking and error handling
    """
    
    def __init__(self, name):
        """
        Initialize a new pipeline.
        
        Args:
            name (str): Pipeline name
        """
        self.name = name
        self.steps = []
        self.status = "Not Started"
        self.run_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        logger.info(f"Created Kubeflow pipeline: {name} (ID: {self.run_id})")
    
    def add_step(self, step_name, function, **kwargs):
        """
        Add a step to the pipeline.
        
        Args:
            step_name (str): Name of the step
            function (callable): Function to execute
            **kwargs: Arguments to pass to the function
            
        Returns:
            KubeflowPipeline: Self for chaining
        """
        self.steps.append({
            'name': step_name,
            'function': function,
            'kwargs': kwargs,
            'status': 'Pending',
            'start_time': None,
            'end_time': None,
            'result': None,
            'error': None
        })
        
        logger.info(f"Added step '{step_name}' to pipeline '{self.name}'")
        return self
    
    def run(self):
        """
        Execute the pipeline steps sequentially.
        
        Returns:
            bool: Success status
        """
        self.status = "Running"
        self.start_time = datetime.now()
        logger.info(f"Starting pipeline: {self.name}")
        
        for i, step in enumerate(self.steps):
            logger.info(f"Executing step {i+1}/{len(self.steps)}: {step['name']}")
            
            # Update step status
            step['status'] = 'Running'
            step['start_time'] = datetime.now()
            
            try:
                # Prepare arguments
                kwargs = step['kwargs'].copy()
                
                # Replace any result references with actual results
                for key, value in kwargs.items():
                    if isinstance(value, str) and value.startswith('steps[') and value.endswith('][result]'):
                        # Extract step index
                        step_index = int(value.split('[')[1].split(']')[0])
                        if step_index < i:  # Only use previous steps
                            kwargs[key] = self.steps[step_index]['result']
                
                # Execute the function
                result = step['function'](**kwargs)
                
                # Update step status
                step['status'] = 'Completed'
                step['result'] = result
                step['end_time'] = datetime.now()
                
                # Log execution time
                duration = (step['end_time'] - step['start_time']).total_seconds()
                logger.info(f"Step '{step['name']}' completed in {duration:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Step '{step['name']}' failed: {str(e)}")
                step['status'] = 'Failed'
                step['error'] = str(e)
                step['end_time'] = datetime.now()
                
                # Update pipeline status
                self.status = "Failed"
                self.end_time = datetime.now()
                return False
        
        # All steps completed successfully
        self.status = "Completed"
        self.end_time = datetime.now()
        
        # Calculate total execution time
        total_duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Pipeline '{self.name}' completed successfully in {total_duration:.2f} seconds")
        
        return True
    
    def get_status(self):
        """
        Get the status of the pipeline and its steps.
        
        Returns:
            dict: Pipeline status information
        """
        return {
            'name': self.name,
            'run_id': self.run_id,
            'status': self.status,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'steps': [
                {
                    'name': step['name'],
                    'status': step['status'],
                    'start_time': step['start_time'],
                    'end_time': step['end_time'],
                    'error': step['error']
                }
                for step in self.steps
            ]
        }