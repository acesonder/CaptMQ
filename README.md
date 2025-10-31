# CaptMQ

A simple, reliable message queue library with built-in retry mechanism and dead-letter queue support.

## Features

- **Retry Mechanism**: Automatically retry failed messages with configurable policies
- **Exponential Backoff**: Prevent overwhelming systems with intelligent retry delays
- **Jitter Support**: Avoid thundering herd problems with randomized delays
- **Dead-Letter Queue**: Isolate messages that consistently fail for manual inspection
- **Configurable**: Fine-tune retry behavior per queue or per message
- **Simple API**: Easy to use with minimal boilerplate

## Installation

```bash
# Clone the repository
git clone https://github.com/acesonder/CaptMQ.git
cd CaptMQ
```

## Quick Start

```python
from captmq import MessageQueue, RetryPolicy

# Create a queue with default retry policy
queue = MessageQueue()

# Enqueue messages
queue.enqueue("msg-1", {"task": "send_email", "to": "user@example.com"})
queue.enqueue("msg-2", {"task": "process_payment", "amount": 100})

# Define a message handler
def process_message(payload):
    print(f"Processing: {payload}")
    # Your processing logic here
    # Raise an exception if processing fails

# Process all messages
stats = queue.process_all(process_message)
print(f"Processed: {stats['succeeded']}, Failed: {stats['dead_lettered']}")
```

## Retry Mechanism

CaptMQ implements a robust retry mechanism with the following features:

### Retry Policy Configuration

```python
from captmq import MessageQueue, RetryPolicy

# Create a custom retry policy
retry_policy = RetryPolicy(
    max_retries=3,           # Maximum number of retry attempts
    initial_delay=1.0,       # Initial delay in seconds
    max_delay=60.0,          # Maximum delay in seconds
    exponential_base=2.0,    # Exponential backoff base
    jitter=True              # Add randomization to delays
)

queue = MessageQueue(retry_policy=retry_policy)
```

### Exponential Backoff

The retry mechanism uses exponential backoff to avoid overwhelming downstream systems:

- **First retry**: `initial_delay` seconds
- **Second retry**: `initial_delay * exponential_base` seconds
- **Third retry**: `initial_delay * exponential_base^2` seconds
- And so on, up to `max_delay`

### Jitter

When enabled, jitter adds randomization to retry delays (50-100% of calculated delay) to prevent the "thundering herd" problem where many clients retry simultaneously.

### Dead-Letter Queue

Messages that exceed the maximum retry count are automatically moved to a dead-letter queue for inspection:

```python
# Get dead-letter messages
dead_letters = queue.get_dead_letter_messages()
for msg in dead_letters:
    print(f"Failed message: {msg.id}, Error: {msg.error}, Attempts: {msg.retry_count}")

# Retry a dead-lettered message
queue.retry_dead_letter_message("msg-1")
```

## Advanced Usage

### Per-Message Retry Configuration

```python
# Override max_retries for a specific message
queue.enqueue("critical-msg", {"data": "important"}, max_retries=5)
queue.enqueue("normal-msg", {"data": "regular"}, max_retries=2)
```

### Manual Message Processing

```python
# Dequeue and process messages individually
message = queue.dequeue()
if message:
    success = queue.process_message(message, handler_function)
    if not success:
        print(f"Message failed: {message.error}")
```

### Queue Statistics

```python
stats = queue.get_stats()
print(f"Pending: {stats['pending']}")
print(f"Processing: {stats['processing']}")
print(f"Dead-letter: {stats['dead_letter']}")
```

## Examples

See `example.py` for a complete working example:

```bash
python example.py
```

## Testing

Run the comprehensive test suite:

```bash
python -m unittest test_captmq.py -v
```

## Best Practices

1. **Idempotency**: Ensure your message handlers are idempotent (safe to retry)
2. **Error Handling**: Only raise exceptions for transient failures that should be retried
3. **Monitoring**: Monitor dead-letter queues for persistent failures
4. **Timeouts**: Implement reasonable timeouts in your handlers
5. **Logging**: Use proper logging to track message processing and failures

## Architecture

CaptMQ follows these design principles:

- **Simplicity**: Easy to understand and use
- **Reliability**: Built-in retry and error handling
- **Configurability**: Flexible policies for different use cases
- **Observability**: Clear statistics and dead-letter queue inspection

## Message Lifecycle

1. **PENDING**: Message is queued and waiting to be processed
2. **PROCESSING**: Message is currently being processed
3. **COMPLETED**: Message was successfully processed
4. **FAILED**: Message processing failed (will retry if attempts remain)
5. **DEAD_LETTER**: Message exceeded max retries and moved to dead-letter queue

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.