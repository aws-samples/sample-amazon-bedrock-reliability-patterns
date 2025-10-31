#!/usr/bin/env python3
"""
Manual Multi-Provider Single-Region Pattern

Demonstrates provider diversification within a single region when you need
provider-level redundancy but want to maintain low latency by staying
within one geographic region.

Use this pattern when you need provider diversification but latency requirements
mandate staying within a single region.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
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

class MultiProviderSingleRegion:
    def __init__(self, region: str = None):
        """Initialize multi-provider single-region demonstration."""
        self.region = region or get_secure_region()
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"multi_provider_single_region_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = setup_logging(self.log_file)
        
        # Initialize log entries
        self.log_entries = []

        # Provider models available in most regions
        self.provider_models = {
            'anthropic': 'anthropic.claude-3-haiku-20240307-v1:0',
            'amazon': 'amazon.nova-lite-v1:0',
            'meta': 'meta.llama3-8b-instruct-v1:0'
        }

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
                f.write("MULTI-PROVIDER SINGLE-REGION PATTERN - DETAILED LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source Region: {self.region}\n")
                f.write(f"Provider Models: {json.dumps(self.provider_models, indent=2)}\n")
                f.write(f"Log File: {self.log_file}\n")
                f.write("=" * 80 + "\n\n")
                f.write("\n".join(self.log_entries))
                f.write(f"\n\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {e}")

    def test_provider_availability(self, provider: str, model_id: str) -> Dict[str, Any]:
        """Test availability of a specific provider's model."""
        self.log(f"Testing provider {provider} with model: {model_id}")

        try:
            start_time = time.time()

            response = self.bedrock_runtime.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": f"Test message for {provider} provider availability."}]}],
                inferenceConfig={"maxTokens": 50, "temperature": 0.7}
            )

            end_time = time.time()
            response_time = end_time - start_time

            usage = response.get('usage', {})

            self.log(f"Provider {provider} test successful: {response_time:.2f}s")
            self.log(f"Token usage: {json.dumps(usage, indent=2)}")

            return {
                'success': True,
                'provider': provider,
                'model_id': model_id,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            self.log(f"Provider {provider} test failed: {str(e)}")
            return {
                'success': False,
                'provider': provider,
                'model_id': model_id,
                'error': str(e),
                'response_time': 0
            }

    def invoke_with_provider_fallback(self, prompt: str) -> Dict[str, Any]:
        """Invoke with multi-provider fallback logic."""
        self.log(f"Starting multi-provider fallback for prompt: {prompt}")

        for provider, model_id in self.provider_models.items():
            self.log(f"Attempting inference with provider: {provider}")

            result = self.test_provider_availability(provider, model_id)

            if result['success']:
                self.log(f"Successfully completed inference with provider: {provider}")
                return result
            else:
                self.log(f"Failed with provider {provider}, trying next provider")
                continue

        self.log("All providers failed - no successful inference")
        return {
            'success': False,
            'error': 'All providers failed',
            'providers_tried': list(self.provider_models.keys())
        }

    def demonstrate_multi_provider_single_region(self):
        """Demonstrate multi-provider single-region with clean console output."""

        # Initialize pattern demonstration
        self.console("Multi-Provider Single-Region Pattern")
        self.console("Provider diversification within one region")

        # Detailed logging
        self.log("Starting MULTI-PROVIDER SINGLE-REGION demonstration")
        self.log("Initializing multi-provider single-region demonstration")
        self.log(f"Source region: {self.region}")
        self.log(f"Provider models: {json.dumps(self.provider_models, indent=2)}")

        # Test provider availability
        self.console("Testing provider availability...")
        self.log("Testing availability of providers in target region")

        available_providers = []
        for provider, model_id in self.provider_models.items():
            result = self.test_provider_availability(provider, model_id)
            if result['success']:
                available_providers.append(provider)
                self.console(f"{provider}: Available ({result['response_time']:.2f}s)")
            else:
                self.console(f"{provider}: Failed - {result.get('error', 'Unknown error')}")

        # Test fallback logic
        if available_providers:
            self.console("Testing provider fallback...")
            self.log("Testing multi-provider fallback with sample prompt")

            test_prompt = "Explain the benefits of provider diversification in 2 sentences."
            result = self.invoke_with_provider_fallback(test_prompt)

            if result['success']:
                self.console(f"Fallback successful: {result['provider']} ({result['response_time']:.2f}s)")
                self.console(f"\nResults: Provider fallback system operational")
            else:
                self.console(f"Fallback failed: {result.get('error', 'Unknown error')}")
                self.console(f"\nResults: Provider fallback system failed")
        else:
            self.console("No providers available for testing")
            self.console(f"\nResults: No available providers found")

        # Provider benefits
        self.console("\nProvider Benefits:")
        self.console("• Provider-level redundancy within single region")
        self.console("• Low latency with geographic consistency")
        self.console("• Diverse model capabilities and pricing")

        # Implementation notes
        self.console("\nImplementation Notes:")
        self.console("• Consider Multi-Provider Gateway for full solution")
        self.console("• Use this for latency-sensitive applications")
        self.console("• Balance provider diversity with complexity")

        # Save detailed log
        self.log("Completed MULTI-PROVIDER SINGLE-REGION demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate multi-provider single-region pattern."""
    client = MultiProviderSingleRegion()
    client.demonstrate_multi_provider_single_region()

if __name__ == "__main__":
    main()