#!/usr/bin/env python3
"""
Prompt Caching Pattern

Demonstrates reduced latency and token costs using Amazon Bedrock prompt caching
with Nova models. Cache prompt prefixes with 5-minute TTL for repeated contexts
like document-based chatbots and Q&A applications.

Use prompt caching for applications with repeated contexts, document analysis,
and scenarios where the same context is used multiple times.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
"""

import boto3
import json
import sys
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

# Import security utilities
sys.path.append(str(Path(__file__).parent.parent))
from security_utils import (
    validate_model_id, sanitize_prompt, sanitize_error_message,
    get_secure_region, create_secure_log_file, RateLimiter,
    RetryHandler, CircuitBreaker, ResourceManager, validate_config,
    setup_logging, timeout_context
)

class PromptCaching:
    def __init__(self, region: str = None):
        """Initialize prompt caching demonstration."""
        self.region = region or get_secure_region()
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"prompt_caching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = setup_logging(self.log_file)
        
        # Initialize log entries
        self.log_entries = []

        # Caching configuration
        self.cache_config = {
            'model_id': 'us.amazon.nova-pro-v1:0',  # Nova models support caching
            'cache_ttl': 300,  # 5 minutes
            'min_tokens': 1024  # Minimum tokens for caching
        }

        # Sample document context (AWS CAF for AI excerpt)
        self.document_context = """
The AWS Cloud Adoption Framework for AI (AWS CAF for AI) provides guidance for organizations
looking to adopt artificial intelligence and machine learning capabilities in the cloud.

Key principles include:
1. Start with business outcomes and work backwards
2. Build a data-driven culture and capabilities
3. Implement responsible AI practices
4. Establish governance and risk management
5. Invest in talent and change management

The framework covers six perspectives: Business, People, Governance, Platform, Security, and Operations.
Each perspective provides specific guidance for AI adoption at scale.
"""

    def log(self, message: str):
        """Add message to detailed log entries."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_entries.append(f"[{timestamp}] {message}")

    def console(self, message: str):
        """Print to console only."""
        print(message)

    def save_log(self):
        """Save detailed log entries to file."""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("AMAZON BEDROCK PROMPT CACHING PATTERN - DETAILED LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source Region: {self.region}\n")
                f.write(f"Log File: {self.log_file}\n")
                f.write("=" * 80 + "\n\n")
                f.write("\n".join(self.log_entries))
                f.write(f"\n\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {e}")

    def test_with_caching(self, question: str) -> Dict[str, Any]:
        """Test inference with prompt caching."""
        self.log(f"Testing with caching - Question: {question}")

        try:
            start_time = time.time()

            # Create cached prompt with context
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {
                            "text": self.document_context,
                            "cache": {"type": "ephemeral"}  # Cache this context
                        },
                        {
                            "text": f"\n\nBased on the AWS CAF for AI document above, {question}"
                        }
                    ]
                }
            ]

            response = self.bedrock_runtime.converse(
                modelId=self.cache_config['model_id'],
                messages=messages,
                inferenceConfig={"maxTokens": 200, "temperature": 0.7}
            )

            end_time = time.time()
            response_time = end_time - start_time

            content = response['output']['message']['content'][0]['text']
            usage = response.get('usage', {})

            self.log(f"Cached inference successful: {response_time:.2f}s")
            self.log(f"Token usage: {json.dumps(usage, indent=2)}")
            self.log(f"Response: {content}")

            return {
                'success': True,
                'response_time': response_time,
                'usage': usage,
                'content': content[:100] + "..." if len(content) > 100 else content
            }

        except Exception as e:
            self.log(f"ERROR: {sanitize_error_message(str(e))}")
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }

    def test_without_caching(self, question: str) -> Dict[str, Any]:
        """Test inference without prompt caching for comparison."""
        self.log(f"Testing without caching - Question: {question}")

        try:
            start_time = time.time()

            # Regular prompt without caching
            full_prompt = f"{self.document_context}\n\nBased on the AWS CAF for AI document above, {question}"

            response = self.bedrock_runtime.converse(
                modelId=self.cache_config['model_id'],
                messages=[{"role": "user", "content": [{"text": full_prompt}]}],
                inferenceConfig={"maxTokens": 200, "temperature": 0.7}
            )

            end_time = time.time()
            response_time = end_time - start_time

            content = response['output']['message']['content'][0]['text']
            usage = response.get('usage', {})

            self.log(f"Non-cached inference successful: {response_time:.2f}s")
            self.log(f"Token usage: {json.dumps(usage, indent=2)}")
            self.log(f"Response: {content}")

            return {
                'success': True,
                'response_time': response_time,
                'usage': usage,
                'content': content[:100] + "..." if len(content) > 100 else content
            }

        except Exception as e:
            self.log(f"ERROR: {sanitize_error_message(str(e))}")
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }

    def demonstrate_prompt_caching(self):
        """Demonstrate prompt caching with clean console output."""

        # Initialize pattern demonstration
        self.console("Prompt Caching Pattern")
        self.console("Reduced latency and costs with 5-minute TTL")

        # Detailed logging
        self.log("Starting PROMPT CACHING demonstration")
        self.log("Initializing prompt caching demonstration")
        self.log(f"Source region: {self.region}")
        self.log(f"Cache configuration: {json.dumps(self.cache_config, indent=2)}")
        self.log(f"Document context length: {len(self.document_context)} characters")

        # Test questions
        questions = [
            "What are the key principles mentioned?",
            "How many perspectives does the framework cover?"
        ]

        # Test without caching first
        self.console("Testing without caching...")
        self.log("Starting non-cached inference tests")

        non_cached_results = []
        for i, question in enumerate(questions):
            result = self.test_without_caching(question)
            non_cached_results.append(result)

            if result['success']:
                self.console(f"Question {i+1}: {result['response_time']:.2f}s, {result['usage'].get('inputTokens', 0)} input tokens")

        # Test with caching
        self.console("Testing with caching...")
        self.log("Starting cached inference tests")

        cached_results = []
        for i, question in enumerate(questions):
            result = self.test_with_caching(question)
            cached_results.append(result)

            if result['success']:
                self.console(f"Question {i+1}: {result['response_time']:.2f}s, {result['usage'].get('inputTokens', 0)} input tokens")

        # Calculate improvements
        successful_cached = [r for r in cached_results if r.get('success', False)]
        successful_non_cached = [r for r in non_cached_results if r.get('success', False)]

        if successful_cached and successful_non_cached:
            avg_cached_time = sum(r['response_time'] for r in successful_cached) / len(successful_cached)
            avg_non_cached_time = sum(r['response_time'] for r in successful_non_cached) / len(successful_non_cached)

            if avg_non_cached_time > 0:
                improvement = ((avg_non_cached_time - avg_cached_time) / avg_non_cached_time) * 100
                self.console(f"\nPerformance: {improvement:.1f}% faster with caching")

            self.console(f"Test Results: {len(successful_cached)}/{len(questions)} cached passed")
        else:
            self.console(f"Status: Testing completed with mixed results")

        # Key benefits
        self.console("\nCaching Benefits:")
        self.console("• Reduced latency for repeated contexts")
        self.console("• Lower token costs for cached content")
        self.console("• 5-minute TTL for session-based applications")

        # Save detailed log
        self.log("Completed PROMPT CACHING demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate Amazon Bedrock prompt caching pattern."""
    client = PromptCaching()
    client.demonstrate_prompt_caching()

if __name__ == "__main__":
    main()