"""
Kafka simulator module for event streaming.
Simulates Kafka-like publish-subscribe message queues.
"""
import queue
import threading
import uuid
import logging
from datetime import datetime

logger = logging.getLogger('cloud-monitor.streaming')

class KafkaSimulator:
    """
    Simulates Kafka-like publish-subscribe message queue system.
    
    Features:
    - Topic-based message publishing
    - Consumer groups and message distribution
    - Asynchronous message processing
    """
    
    def __init__(self, topics=None):
        """
        Initialize the Kafka simulator with specified topics.
        
        Args:
            topics (list, optional): List of topic names to create
        """
        self.topics = topics or ['metrics', 'anomalies', 'remediation']
        self.queues = {topic: queue.Queue() for topic in self.topics}
        self.consumers = {}
        logger.info(f"Initialized Kafka simulator with topics: {', '.join(self.topics)}")
    
    def produce(self, topic, message):
        """
        Produce a message to a topic.
        
        Args:
            topic (str): Topic to produce to
            message (dict): Message to produce
            
        Returns:
            bool: Success status
        """
        if topic not in self.queues:
            logger.error(f"Unknown topic: {topic}")
            return False
        
        # Add timestamp to message if it doesn't have one
        if isinstance(message, dict) and 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()
        
        # Put message in queue
        self.queues[topic].put(message)
        return True
    
    def consume(self, topic, group_id, callback):
        """
        Register a consumer for a topic with a callback.
        
        Args:
            topic (str): Topic to consume from
            group_id (str): Consumer group ID
            callback (function): Function to call with each message
            
        Returns:
            str: Consumer ID
        """
        if topic not in self.queues:
            logger.error(f"Unknown topic: {topic}")
            return None
        
        # Create consumer ID
        consumer_id = f"{group_id}-{str(uuid.uuid4())[:8]}"
        
        # Start consumer thread
        thread = threading.Thread(
            target=self._consume_loop,
            args=(topic, consumer_id, callback)
        )
        thread.daemon = True
        thread.start()
        
        # Register consumer
        self.consumers[consumer_id] = {
            'topic': topic,
            'group_id': group_id,
            'thread': thread,
            'active': True
        }
        
        logger.info(f"Started consumer {consumer_id} for topic {topic}")
        return consumer_id
    
    def _consume_loop(self, topic, consumer_id, callback):
        """
        Consumer loop that pulls messages and calls the callback.
        
        Args:
            topic (str): Topic to consume from
            consumer_id (str): Consumer ID
            callback (function): Function to call with each message
        """
        queue_obj = self.queues[topic]
        
        while self.consumers.get(consumer_id, {}).get('active', False):
            try:
                # Non-blocking get with timeout
                message = queue_obj.get(block=True, timeout=1.0)
                callback(message)
                queue_obj.task_done()
            except queue.Empty:
                # No message available, that's okay
                pass
            except Exception as e:
                logger.error(f"Error in consumer {consumer_id}: {str(e)}")
    
    def stop_consumer(self, consumer_id):
        """
        Stop a consumer.
        
        Args:
            consumer_id (str): Consumer ID to stop
            
        Returns:
            bool: Success status
        """
        if consumer_id in self.consumers:
            self.consumers[consumer_id]['active'] = False
            logger.info(f"Stopped consumer {consumer_id}")
            return True
        else:
            logger.warning(f"Consumer {consumer_id} not found")
            return False