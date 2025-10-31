"""
Tests for CaptMQ retry mechanism
"""
import unittest
import time
from captmq import MessageQueue, RetryPolicy, Message, MessageStatus


class TestRetryMechanism(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.retry_policy = RetryPolicy(
            max_retries=3,
            initial_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable tests
        )
        self.queue = MessageQueue(retry_policy=self.retry_policy)
    
    def test_enqueue_message(self):
        """Test enqueueing a message"""
        message = self.queue.enqueue("test-1", {"data": "test"})
        self.assertEqual(message.id, "test-1")
        self.assertEqual(message.payload, {"data": "test"})
        self.assertEqual(message.status, MessageStatus.PENDING)
        self.assertEqual(len(self.queue.queue), 1)
    
    def test_dequeue_message(self):
        """Test dequeueing a message"""
        self.queue.enqueue("test-1", {"data": "test"})
        message = self.queue.dequeue()
        self.assertIsNotNone(message)
        self.assertEqual(message.id, "test-1")
        self.assertEqual(message.status, MessageStatus.PROCESSING)
        self.assertEqual(len(self.queue.queue), 0)
    
    def test_successful_processing(self):
        """Test successful message processing"""
        message = self.queue.enqueue("test-1", {"data": "test"})
        
        def success_handler(payload):
            self.assertEqual(payload, {"data": "test"})
        
        message = self.queue.dequeue()
        success = self.queue.process_message(message, success_handler)
        
        self.assertTrue(success)
        self.assertEqual(message.status, MessageStatus.COMPLETED)
        self.assertEqual(message.retry_count, 0)
    
    def test_failed_processing_with_retry(self):
        """Test failed message processing with retry"""
        message = self.queue.enqueue("test-1", {"data": "test"})
        
        attempt_count = 0
        def failing_handler(payload):
            nonlocal attempt_count
            attempt_count += 1
            raise Exception("Simulated failure")
        
        message = self.queue.dequeue()
        success = self.queue.process_message(message, failing_handler)
        
        self.assertFalse(success)
        self.assertEqual(message.status, MessageStatus.PENDING)  # Queued for retry
        self.assertEqual(message.retry_count, 1)
        self.assertIn("Simulated failure", message.error)
        self.assertEqual(len(self.queue.queue), 1)  # Message re-queued
    
    def test_max_retries_exceeded(self):
        """Test message moved to dead-letter queue after max retries"""
        message = self.queue.enqueue("test-1", {"data": "test"})
        
        def failing_handler(payload):
            raise Exception("Always fails")
        
        # Process message until it reaches dead-letter queue
        for _ in range(self.retry_policy.max_retries + 1):
            msg = self.queue.dequeue()
            if msg:
                self.queue.process_message(msg, failing_handler)
        
        # Check message is in dead-letter queue
        self.assertEqual(len(self.queue.dead_letter_queue), 1)
        dlq_message = self.queue.dead_letter_queue[0]
        self.assertEqual(dlq_message.id, "test-1")
        self.assertEqual(dlq_message.status, MessageStatus.DEAD_LETTER)
        self.assertEqual(dlq_message.retry_count, self.retry_policy.max_retries)
    
    def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation"""
        delays = [
            self.retry_policy.get_delay(0),
            self.retry_policy.get_delay(1),
            self.retry_policy.get_delay(2),
        ]
        
        # Check delays increase exponentially
        self.assertAlmostEqual(delays[0], 0.1, places=2)
        self.assertAlmostEqual(delays[1], 0.2, places=2)
        self.assertAlmostEqual(delays[2], 0.4, places=2)
        
        # Check max delay is respected
        large_delay = self.retry_policy.get_delay(10)
        self.assertLessEqual(large_delay, self.retry_policy.max_delay)
    
    def test_retry_delay_with_jitter(self):
        """Test retry delay with jitter"""
        policy_with_jitter = RetryPolicy(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # Get multiple delays to check variance
        delays = [policy_with_jitter.get_delay(0) for _ in range(10)]
        
        # Check all delays are within expected range (0.5 to 1.0)
        for delay in delays:
            self.assertGreaterEqual(delay, 0.5)
            self.assertLessEqual(delay, 1.0)
        
        # Check there is some variance (not all the same)
        self.assertGreater(len(set(delays)), 1)
    
    def test_dead_letter_queue_retry(self):
        """Test retrying a message from dead-letter queue"""
        message = self.queue.enqueue("test-1", {"data": "test"})
        
        def failing_handler(payload):
            raise Exception("Always fails")
        
        # Process until dead-lettered
        for _ in range(self.retry_policy.max_retries + 1):
            msg = self.queue.dequeue()
            if msg:
                self.queue.process_message(msg, failing_handler)
        
        # Verify message is in dead-letter queue
        self.assertEqual(len(self.queue.dead_letter_queue), 1)
        
        # Retry the dead-lettered message
        success = self.queue.retry_dead_letter_message("test-1")
        self.assertTrue(success)
        
        # Verify message is back in queue
        self.assertEqual(len(self.queue.dead_letter_queue), 0)
        self.assertEqual(len(self.queue.queue), 1)
        
        # Verify message was reset
        msg = self.queue.dequeue()
        self.assertEqual(msg.retry_count, 0)
        self.assertEqual(msg.status, MessageStatus.PROCESSING)
        self.assertIsNone(msg.error)
    
    def test_queue_statistics(self):
        """Test queue statistics"""
        self.queue.enqueue("test-1", {"data": "test1"})
        self.queue.enqueue("test-2", {"data": "test2"})
        
        stats = self.queue.get_stats()
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['processing'], 0)
        self.assertEqual(stats['dead_letter'], 0)
        
        # Dequeue one message
        self.queue.dequeue()
        stats = self.queue.get_stats()
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['processing'], 1)
    
    def test_custom_max_retries_per_message(self):
        """Test setting custom max retries for individual messages"""
        message = self.queue.enqueue("test-1", {"data": "test"}, max_retries=5)
        self.assertEqual(message.max_retries, 5)
        
        message2 = self.queue.enqueue("test-2", {"data": "test2"})
        self.assertEqual(message2.max_retries, self.retry_policy.max_retries)
    
    def test_process_all(self):
        """Test processing all messages in queue"""
        self.queue.enqueue("test-1", {"data": "success"})
        self.queue.enqueue("test-2", {"data": "fail"})
        self.queue.enqueue("test-3", {"data": "success"})
        
        def selective_handler(payload):
            if payload.get("data") == "fail":
                raise Exception("Intentional failure")
        
        stats = self.queue.process_all(selective_handler, delay_between=0.01)
        
        self.assertEqual(stats['succeeded'], 2)
        self.assertEqual(stats['dead_lettered'], 1)
        # Initial 3 messages + retries (test-2 fails and retries max_retries times)
        expected_processed = 3 + self.retry_policy.max_retries - 1
        self.assertEqual(stats['processed'], expected_processed)
    
    def test_should_retry(self):
        """Test should_retry logic"""
        message = Message(id="test", payload={}, max_retries=3)
        
        # New message should not retry (not failed yet)
        self.assertFalse(message.should_retry())
        
        # Failed message with retries remaining should retry
        message.status = MessageStatus.FAILED
        message.retry_count = 1
        self.assertTrue(message.should_retry())
        
        # Failed message with max retries reached should not retry
        message.retry_count = 3
        self.assertFalse(message.should_retry())
        
        # Completed message should not retry
        message.status = MessageStatus.COMPLETED
        message.retry_count = 0
        self.assertFalse(message.should_retry())


class TestRetryPolicy(unittest.TestCase):
    
    def test_default_retry_policy(self):
        """Test default retry policy values"""
        policy = RetryPolicy()
        self.assertEqual(policy.max_retries, 3)
        self.assertEqual(policy.initial_delay, 1.0)
        self.assertEqual(policy.max_delay, 60.0)
        self.assertEqual(policy.exponential_base, 2.0)
        self.assertTrue(policy.jitter)
    
    def test_custom_retry_policy(self):
        """Test custom retry policy"""
        policy = RetryPolicy(
            max_retries=5,
            initial_delay=2.0,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False
        )
        self.assertEqual(policy.max_retries, 5)
        self.assertEqual(policy.initial_delay, 2.0)
        self.assertEqual(policy.max_delay, 30.0)
        self.assertEqual(policy.exponential_base, 3.0)
        self.assertFalse(policy.jitter)


if __name__ == '__main__':
    unittest.main()
