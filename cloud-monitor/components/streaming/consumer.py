"""
Kafka consumer module for processing streaming data.
"""
import logging
import threading
from datetime import datetime

logger = logging.getLogger('cloud-monitor.streaming')

class StreamConsumer:
    """
    Manages consumer groups for processing stream data.
    
    Features:
    - Topic-based event processing
    - Consumer group management
    - Message aggregation and processing
    """
    
    def __init__(self, kafka_client):
        """
        Initialize the stream consumer.
        
        Args:
            kafka_client: Kafka client instance
        """
        self.kafka = kafka_client
        self.consumers = {}
        self.running = False
        self.handlers = {}
        self.aggregators = {}
        logger.info("Initialized stream consumer")
    
    def register_handler(self, topic, handler):
        """
        Register a handler for a topic.
        
        Args:
            topic (str): Topic name
            handler (callable): Function to handle messages
            
        Returns:
            bool: Success status
        """
        if topic not in self.handlers:
            self.handlers[topic] = []
            
        self.handlers[topic].append(handler)
        logger.info(f"Registered handler for topic {topic}")
        return True
    
    def register_aggregator(self, topic, window_size, aggregator):
        """
        Register an aggregator for a topic.
        
        Args:
            topic (str): Topic name
            window_size (int): Window size in number of messages
            aggregator (callable): Function to aggregate messages
            
        Returns:
            bool: Success status
        """
        self.aggregators[topic] = {
            'window_size': window_size,
            'function': aggregator,
            'buffer': [],
            'last_processed': datetime.now()
        }
        
        logger.info(f"Registered aggregator for topic {topic} with window size {window_size}")
        return True
    
    def start(self, group_id='default-consumer'):
        """
        Start consuming from all registered topics.
        
        Args:
            group_id (str): Consumer group ID
            
        Returns:
            bool: Success status
        """
        if self.running:
            logger.warning("Consumer already running")
            return False
            
        self.running = True
        
        # Start consumers for all registered handlers
        for topic in self.handlers:
            self._start_consumer(topic, group_id)
        
        # Start consumers for all registered aggregators
        for topic in self.aggregators:
            if topic not in self.handlers:  # Don't start twice
                self._start_consumer(topic, group_id)
        
        logger.info(f"Started {len(self.consumers)} consumers with group ID {group_id}")
        return True
    
    def _start_consumer(self, topic, group_id):
        """
        Start a consumer for a specific topic.
        
        Args:
            topic (str): Topic to consume from
            group_id (str): Consumer group ID
        """
        # Create consumer ID
        consumer_id = f"{group_id}-{topic}"
        
        # Define message processor
        def process_message(message):
            # Call all handlers for this topic
            if topic in self.handlers:
                for handler in self.handlers[topic]:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Error in handler for {topic}: {str(e)}")
            
            # Process with aggregator if defined
            if topic in self.aggregators:
                try:
                    aggregator = self.aggregators[topic]
                    buffer = aggregator['buffer']
                    
                    # Add message to buffer
                    buffer.append(message)
                    
                    # Check if we have enough messages
                    if len(buffer) >= aggregator['window_size']:
                        # Call aggregator function
                        result = aggregator['function'](buffer)
                        
                        # Update last processed time
                        aggregator['last_processed'] = datetime.now()
                        
                        # Clear buffer
                        buffer.clear()
                        
                        logger.debug(f"Processed {aggregator['window_size']} messages with aggregator for {topic}")
                        
                        return result
                except Exception as e:
                    logger.error(f"Error in aggregator for {topic}: {str(e)}")
        
        # Register consumer with Kafka
        consumer_id = self.kafka.consume(topic, group_id, process_message)
        
        # Store consumer ID
        self.consumers[topic] = consumer_id
    
    def stop(self):
        """
        Stop all consumers.
        
        Returns:
            bool: Success status
        """
        if not self.running:
            logger.warning("Consumer not running")
            return False
            
        # Stop all consumers
        for topic, consumer_id in self.consumers.items():
            self.kafka.stop_consumer(consumer_id)
            
        self.consumers = {}
        self.running = False
        
        logger.info("Stopped all consumers")
        return True
    
    def get_status(self):
        """
        Get consumer status.
        
        Returns:
            dict: Consumer status information
        """
        return {
            'running': self.running,
            'consumers': len(self.consumers),
            'handlers': {topic: len(handlers) for topic, handlers in self.handlers.items()},
            'aggregators': {topic: {
                'window_size': agg['window_size'],
                'buffer_size': len(agg['buffer']),
                'last_processed': agg['last_processed'].isoformat()
            } for topic, agg in self.aggregators.items()}
        }

class MessageProcessor:
    """
    Common message processing functions for stream data.
    
    These static methods can be used as handlers or aggregators.
    """
    
    @staticmethod
    def log_message(message):
        """
        Simple handler that logs messages.
        
        Args:
            message: Message to log
        """
        logger.debug(f"Message received: {message}")
    
    @staticmethod
    def count_aggregator(messages):
        """
        Simple aggregator that counts messages by type.
        
        Args:
            messages (list): List of messages
            
        Returns:
            dict: Message counts by type
        """
        counts = {}
        
        for message in messages:
            # Get message type (assuming messages have a 'type' field)
            msg_type = message.get('type', 'unknown')
            
            if msg_type not in counts:
                counts[msg_type] = 0
                
            counts[msg_type] += 1
            
        return {
            'total': len(messages),
            'counts': counts,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def avg_value_aggregator(messages, value_field='value'):
        """
        Aggregator that calculates average values.
        
        Args:
            messages (list): List of messages
            value_field (str): Field name for value
            
        Returns:
            dict: Average values by group
        """
        groups = {}
        
        for message in messages:
            # Skip messages without required fields
            if value_field not in message:
                continue
                
            # Get group (assuming messages have 'service' and 'metric' fields)
            service = message.get('service', 'unknown')
            metric = message.get('metric', 'unknown')
            group_key = f"{service}_{metric}"
            
            if group_key not in groups:
                groups[group_key] = {
                    'service': service,
                    'metric': metric,
                    'values': [],
                    'count': 0
                }
                
            # Add value to group
            value = message[value_field]
            groups[group_key]['values'].append(value)
            groups[group_key]['count'] += 1
            
        # Calculate averages
        results = []
        for group_key, group in groups.items():
            if group['values']:
                avg_value = sum(group['values']) / len(group['values'])
                
                results.append({
                    'service': group['service'],
                    'metric': group['metric'],
                    'avg_value': avg_value,
                    'count': group['count'],
                    'timestamp': datetime.now().isoformat()
                })
            
        return results