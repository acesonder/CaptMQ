"""
Example usage of CaptMQ
"""
from captmq import MessageQueue, RetryPolicy
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def example_handler(payload):
    """Example message handler that fails sometimes"""
    if payload.get('should_fail', False):
        raise Exception(f"Simulated failure for message: {payload.get('id')}")
    
    print(f"Successfully processed: {payload}")


def main():
    # Create a message queue with custom retry policy
    retry_policy = RetryPolicy(
        max_retries=3,
        initial_delay=0.5,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True
    )
    
    queue = MessageQueue(retry_policy=retry_policy)
    
    # Enqueue some messages
    queue.enqueue("msg-1", {"id": 1, "data": "Hello"})
    queue.enqueue("msg-2", {"id": 2, "data": "World", "should_fail": True})
    queue.enqueue("msg-3", {"id": 3, "data": "Test"})
    queue.enqueue("msg-4", {"id": 4, "data": "Retry", "should_fail": True})
    
    print("\n=== Processing Messages ===\n")
    
    # Process all messages
    stats = queue.process_all(example_handler, delay_between=0.1)
    
    print("\n=== Processing Statistics ===")
    print(f"Total processed: {stats['processed']}")
    print(f"Succeeded: {stats['succeeded']}")
    print(f"Failed: {stats['failed']}")
    print(f"Dead-lettered: {stats['dead_lettered']}")
    
    print("\n=== Queue Statistics ===")
    queue_stats = queue.get_stats()
    print(f"Pending: {queue_stats['pending']}")
    print(f"Processing: {queue_stats['processing']}")
    print(f"Dead-letter: {queue_stats['dead_letter']}")
    
    # Show dead-letter queue
    if queue.dead_letter_queue:
        print("\n=== Dead-Letter Queue ===")
        for msg in queue.get_dead_letter_messages():
            print(f"Message {msg.id}: {msg.payload}, Error: {msg.error}, Attempts: {msg.retry_count}")


if __name__ == "__main__":
    main()
