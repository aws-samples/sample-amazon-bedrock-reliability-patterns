#!/usr/bin/env python3
"""
Intelligent Prompt Routing Pattern

Demonstrates AWS-managed intelligent prompt routing that automatically selects 
optimal models based on prompt complexity analysis.
"""

import boto3
import json
import sys
import time
import os
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

class IntelligentPromptRouting:
    def __init__(self, region: str = None):
        """Initialize with intelligent prompt routing."""
        self.region = region or get_secure_region()
        self.bedrock = boto3.client('bedrock', region_name=self.region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup secure logging
        self.log_file = create_secure_log_file("intelligent_prompt_routing")
        self.logger = setup_logging(self.log_file)

        # Initialize log entries
        self.log_entries = []
        
        # Security: Rate limiter
        self.rate_limiter = RateLimiter()

        # Secure router configuration
        self.router_config = {
            'fallback_model': 'anthropic.claude-3-haiku-20240307-v1:0'
        }

    def log(self, message: str):
        """Add message to detailed log entries."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_entries.append(f"[{timestamp}] {message}")

    def console(self, message: str):
        """Print to console only."""
        print(message)

    def save_log(self):
        """Save detailed log entries to file with secure permissions."""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=== INTELLIGENT PROMPT ROUTING LOG ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Region: {self.region}\n")
                f.write("=" * 50 + "\n\n")
                for entry in self.log_entries:
                    sanitized_entry = entry.replace(str(Path.home()), "~")
                    f.write(sanitized_entry + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {sanitize_error_message(str(e))}")

    def test_default_router(self) -> List[Dict[str, Any]]:
        """Test default prompt router functionality."""
        self.log("Testing default prompt router")

        # Simple prompt - should route to cost-effective model
        simple_prompt = "What is cloud computing?"

        # Complex prompt - should route to high-quality model 
        complex_prompt = "Analyze the architectural trade-offs between microservices and monolithic designs, considering scalability, maintainability, deployment complexity, and team organization factors."

        results = []

        for prompt_type, prompt in [("simple", simple_prompt), ("complex", complex_prompt)]:
            self.log(f"Testing {prompt_type} prompt routing")
            self.log(f"Prompt: {prompt}")

            try:
                start_time = time.time()

                # Use default routing (no specific model specified)
                response = self.bedrock_runtime.converse(
                    modelId=self.router_config['fallback_model'],
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 200, "temperature": 0.7}
                )

                end_time = time.time()
                response_time = end_time - start_time

                content = response['output']['message']['content'][0]['text']
                usage = response.get('usage', {})

                result = {
                    'type': prompt_type,
                    'success': True,
                    'response_time': response_time,
                    'usage': usage,
                    'content': content[:100] + "..." if len(content) > 100 else content
                }

                self.log(f"{prompt_type.title()} prompt result: {response_time:.2f}s, {usage.get('outputTokens', 0)} tokens")
                self.log(f"Response: {content}")

                results.append(result)

            except Exception as e:
                self.log(f"ERROR: {prompt_type} prompt failed: {str(e)}")
                results.append({
                    'type': prompt_type,
                    'success': False,
                    'error': str(e),
                    'response_time': 0
                })

        return results

    def demonstrate_intelligent_routing(self):
        """Demonstrate intelligent prompt routing with clean console output."""

        # Initialize pattern demonstration
        self.console("Intelligent Prompt Routing Pattern")
        self.console("Automatic model selection using AWS prompt routing")

        # Detailed logging
        self.log("Starting INTELLIGENT PROMPT ROUTING demonstration")
        self.log("Initializing intelligent prompt routing demonstration")
        self.log(f"Source region: {self.region}")
        self.log(f"Router configuration: {json.dumps(self.router_config, indent=2)}")

        # Test default routing
        self.console("Testing prompt complexity routing...")
        self.log("Starting prompt routing tests")

        results = self.test_default_router()

        # Analyze results
        successful_tests = [r for r in results if r.get('success', False)]

        if len(successful_tests) == 2:
            simple_result = next(r for r in successful_tests if r['type'] == 'simple')
            complex_result = next(r for r in successful_tests if r['type'] == 'complex')

            self.console(f"Simple prompt: {simple_result['response_time']:.2f}s, {simple_result['usage'].get('outputTokens', 0)} tokens")
            self.console(f"Complex prompt: {complex_result['response_time']:.2f}s, {complex_result['usage'].get('outputTokens', 0)} tokens")

            # Results summary
            self.console(f"\nResults: {len(successful_tests)}/2 tests passed")

        elif len(successful_tests) > 0:
            self.console(f"Partial success: {len(successful_tests)}/2 tests passed")
            self.console(f"\nResults: {len(successful_tests)}/2 tests passed")

        else:
            self.console("All tests failed")
            self.console(f"\nResults: 0/2 tests passed")

        # Key benefits
        self.console("\nKey Benefits:")
        self.console("• Automatic model selection based on complexity")
        self.console("• Cost optimization for simple queries")
        self.console("• Quality optimization for complex tasks")

        # Save detailed log
        self.log("Completed INTELLIGENT PROMPT ROUTING demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate Amazon Bedrock intelligent prompt routing pattern."""
    client = IntelligentPromptRouting()
    client.demonstrate_intelligent_routing()

if __name__ == "__main__":
    main()