#!/usr/bin/env python3
"""
Security utilities for Amazon Bedrock Reliability Patterns
"""

import os
import re
import time
import signal
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Security: Allowed model patterns
ALLOWED_MODEL_PATTERNS = [
    r'^anthropic\.claude-.*',
    r'^amazon\.nova-.*', 
    r'^meta\.llama.*',
    r'^us\..*',
    r'^eu\..*',
    r'^global\..*',  # Global inference profiles
    r'^regional\..*',  # Regional inference profiles
    r'^arn:aws:bedrock:.*'  # ARN format for provisioned throughput
]

# Configuration constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0

def validate_model_id(model_id: str) -> bool:
    """
    Validate model ID against allowed patterns.

    Args:
        model_id: The model identifier to validate

    Returns:
        True if model ID matches allowed patterns, False otherwise

    Example:
        >>> validate_model_id("anthropic.claude-3-haiku-20240307-v1:0")
        True
        >>> validate_model_id("invalid.model")
        False
    """
    if not isinstance(model_id, str) or len(model_id) > 200:
        return False
    return any(re.match(pattern, model_id) for pattern in ALLOWED_MODEL_PATTERNS)

def sanitize_prompt(prompt: str) -> str:
    """
    Sanitize user input prompt for security.

    Args:
        prompt: User input prompt to sanitize

    Returns:
        Sanitized prompt string

    Raises:
        ValueError: If prompt is invalid type or too long

    Example:
        >>> sanitize_prompt(" Hello world ")
        'Hello world'
    """
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string")
    if len(prompt) > 10000:
        raise ValueError("Prompt too long")
    return prompt.strip()

def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to prevent information disclosure."""
    sanitized = str(error_msg).replace(str(Path.home()), "~")
    return sanitized[:200] + "..." if len(sanitized) > 200 else sanitized

def get_secure_region() -> str:
    """Get AWS region from environment with validation."""
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    if not re.match(r'^[a-z0-9-]+$', region):
        raise ValueError("Invalid region format")
    return region

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration parameters."""
    validated = {}

    # Validate timeout
    timeout = config.get('timeout', DEFAULT_TIMEOUT)
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
        timeout = DEFAULT_TIMEOUT
    validated['timeout'] = timeout

    # Validate max_tokens
    max_tokens = config.get('max_tokens', 1000)
    if not isinstance(max_tokens, int) or max_tokens <= 0 or max_tokens > 4000:
        max_tokens = 1000
    validated['max_tokens'] = max_tokens

    # Validate temperature
    temperature = config.get('temperature', 0.7)
    if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 1:
        temperature = 0.7
    validated['temperature'] = temperature

    return validated

def create_secure_log_file(base_name: str) -> Path:
    """Create secure log file with proper permissions."""
    project_root = Path(__file__).parent.parent.resolve()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(mode=0o750, exist_ok=True)

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f"{base_name}_{timestamp}.log"
    log_file.touch(mode=0o640)
    return log_file

def setup_logging(log_file: Path) -> logging.Logger:
    """Setup structured logging with rotation."""
    logger = logging.getLogger(f"bedrock_{log_file.stem}")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # File handler with rotation
    handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

@contextmanager
def timeout_context(seconds: int = DEFAULT_TIMEOUT):
    """Context manager for operation timeouts."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, min_interval: float = 0.1):
        self.min_interval = min_interval
        self.last_request_time = 0

    def wait_if_needed(self):
        """Wait if needed to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)
        self.last_request_time = time.time()

class RetryHandler:
    """Exponential backoff retry handler."""

    def __init__(self, max_retries: int = MAX_RETRIES, backoff: float = RETRY_BACKOFF):
        self.max_retries = max_retries
        self.backoff = backoff

    def retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.backoff * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    break

        raise last_exception

class CircuitBreaker:
    """Simple circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'

            raise e

class ResourceManager:
    """Manage resources with cleanup."""

    def __init__(self):
        self.resources = []

    def add_resource(self, resource):
        """Add resource for cleanup."""
        self.resources.append(resource)

    def cleanup(self):
        """Clean up all resources."""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception:
                pass  # Ignore cleanup errors
        self.resources.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()