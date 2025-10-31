"""
CaptMQ - A simple message queue with retry mechanism
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List
from enum import Enum
from collections import deque
import traceback


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Status of a message in the queue"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class Message:
    """Represents a message in the queue"""
    id: str
    payload: Any
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    created_at: float = field(default_factory=time.time)
    last_attempt_at: Optional[float] = None
    error: Optional[str] = None
    
    def should_retry(self) -> bool:
        """Check if message should be retried"""
        return self.retry_count < self.max_retries and self.status == MessageStatus.FAILED


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay for the given retry attempt"""
        import random
        
        # Calculate exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** retry_count),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class MessageQueue:
    """A message queue with retry mechanism and dead-letter queue"""
    
    def __init__(self, retry_policy: Optional[RetryPolicy] = None):
        self.queue: deque = deque()
        self.dead_letter_queue: List[Message] = []
        self.retry_policy = retry_policy or RetryPolicy()
        self.processing: dict[str, Message] = {}
        
    def enqueue(self, message_id: str, payload: Any, max_retries: Optional[int] = None) -> Message:
        """Add a message to the queue"""
        max_retry_count = max_retries if max_retries is not None else self.retry_policy.max_retries
        message = Message(
            id=message_id,
            payload=payload,
            max_retries=max_retry_count
        )
        self.queue.append(message)
        logger.info(f"Enqueued message {message_id}")
        return message
    
    def dequeue(self) -> Optional[Message]:
        """Get the next message from the queue"""
        if not self.queue:
            return None
        
        message = self.queue.popleft()
        message.status = MessageStatus.PROCESSING
        message.last_attempt_at = time.time()
        self.processing[message.id] = message
        return message
    
    def process_message(self, message: Message, handler: Callable[[Any], None]) -> bool:
        """
        Process a message with the given handler
        Returns True if successful, False otherwise
        """
        try:
            logger.info(f"Processing message {message.id} (attempt {message.retry_count + 1})")
            handler(message.payload)
            message.status = MessageStatus.COMPLETED
            self.processing.pop(message.id, None)
            logger.info(f"Successfully processed message {message.id}")
            return True
        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error = str(e)
            message.retry_count += 1
            logger.error(f"Failed to process message {message.id}: {e}")
            
            if message.should_retry():
                # Schedule for retry
                delay = self.retry_policy.get_delay(message.retry_count - 1)
                logger.info(f"Scheduling retry for message {message.id} after {delay:.2f}s (retry {message.retry_count}/{message.max_retries})")
                # Reset status for retry
                message.status = MessageStatus.PENDING
                self.queue.append(message)
            else:
                # Move to dead-letter queue
                message.status = MessageStatus.DEAD_LETTER
                self.dead_letter_queue.append(message)
                logger.warning(f"Message {message.id} moved to dead-letter queue after {message.retry_count} attempts")
            
            self.processing.pop(message.id, None)
            return False
    
    def process_all(self, handler: Callable[[Any], None], delay_between: float = 0.1) -> dict:
        """
        Process all messages in the queue
        Returns statistics about processing
        """
        stats = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'dead_lettered': 0
        }
        
        while True:
            message = self.dequeue()
            if not message:
                break
            
            stats['processed'] += 1
            success = self.process_message(message, handler)
            
            if success:
                stats['succeeded'] += 1
            else:
                stats['failed'] += 1
                if message.status == MessageStatus.DEAD_LETTER:
                    stats['dead_lettered'] += 1
            
            # Add delay between processing to implement backoff
            if not success and message.should_retry():
                delay = self.retry_policy.get_delay(message.retry_count - 1)
                time.sleep(delay)
            else:
                time.sleep(delay_between)
        
        return stats
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            'pending': len(self.queue),
            'processing': len(self.processing),
            'dead_letter': len(self.dead_letter_queue)
        }
    
    def get_dead_letter_messages(self) -> List[Message]:
        """Get all messages in the dead-letter queue"""
        return self.dead_letter_queue.copy()
    
    def retry_dead_letter_message(self, message_id: str) -> bool:
        """
        Retry a message from the dead-letter queue
        Returns True if message was found and re-queued
        """
        for i, message in enumerate(self.dead_letter_queue):
            if message.id == message_id:
                # Reset message for retry
                message.retry_count = 0
                message.status = MessageStatus.PENDING
                message.error = None
                self.queue.append(message)
                self.dead_letter_queue.pop(i)
                logger.info(f"Re-queued message {message_id} from dead-letter queue")
                return True
        return False
