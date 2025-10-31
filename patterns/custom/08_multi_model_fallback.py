#!/usr/bin/env python3
"""
Manual Multi-Model Fallback Pattern

Demonstrates sequential model attempts within the same provider when you need
custom routing logic beyond AWS intelligent prompt routing. Provides fallback
across different models for reliability and availability.

Use this pattern when you need custom model selection logic that goes beyond
what AWS intelligent prompt routing provides.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routers.html
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

class MultiModelFallback:
    def __init__(self, region: str = None):
        """Initialize multi-model fallback demonstration."""
        self.region = region or get_secure_region()
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"multi_model_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = setup_logging(self.log_file)
        
        # Initialize log entries
        self.log_entries = []

        # Model fallback chain (ordered by preference)
        self.model_chain = [
            'anthropic.claude-3-sonnet-20240229-v1:0',  # Primary
            'anthropic.claude-3-haiku-20240307-v1:0',   # Fallback 1
            'amazon.nova-lite-v1:0'                     # Fallback 2
        ]

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
                f.write("MULTI-MODEL FALLBACK PATTERN - DETAILED LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source Region: {self.region}\n")
                f.write(f"Model Chain: {', '.join(self.model_chain)}\n")
                f.write(f"Log File: {self.log_file}\n")
                f.write("=" * 80 + "\n\n")
                f.write("\n".join(self.log_entries))
                f.write(f"\n\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {e}")

    def test_model_availability(self, model_id: str) -> Dict[str, Any]:
        """Test availability of a specific model."""
        self.log(f"Testing model availability: {model_id}")

        try:
            start_time = time.time()

            response = self.bedrock_runtime.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "Test message for model availability."}]}],
                inferenceConfig={"maxTokens": 50, "temperature": 0.7}
            )

            end_time = time.time()
            response_time = end_time - start_time

            usage = response.get('usage', {})

            self.log(f"Model {model_id} test successful: {response_time:.2f}s")
            self.log(f"Token usage: {json.dumps(usage, indent=2)}")

            return {
                'success': True,
                'model_id': model_id,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            self.log(f"Model {model_id} test failed: {str(e)}")
            return {
                'success': False,
                'model_id': model_id,
                'error': str(e),
                'response_time': 0
            }

    def invoke_with_model_fallback(self, prompt: str) -> Dict[str, Any]:
        """Invoke with multi-model fallback logic."""
        self.log(f"Starting multi-model fallback for prompt: {prompt}")

        for model_id in self.model_chain:
            self.log(f"Attempting inference with model: {model_id}")

            result = self.test_model_availability(model_id)

            if result['success']:
                self.log(f"Successfully completed inference with model: {model_id}")
                return result
            else:
                self.log(f"Failed with model {model_id}, trying next model")
                continue

        self.log("All models failed - no successful inference")
        return {
            'success': False,
            'error': 'All models failed',
            'models_tried': self.model_chain
        }

    def demonstrate_multi_model_fallback(self):
        """Demonstrate multi-model fallback with clean console output."""

        # Initialize pattern demonstration
        self.console("Multi-Model Fallback Pattern")
        self.console("Sequential model attempts for reliability")

        # Detailed logging
        self.log("Starting MULTI-MODEL FALLBACK demonstration")
        self.log("Initializing multi-model fallback demonstration")
        self.log(f"Source region: {self.region}")
        self.log(f"Model chain: {', '.join(self.model_chain)}")

        # Test model availability
        self.console("Testing model availability...")
        self.log("Testing availability of models in fallback chain")

        available_models = []
        for model_id in self.model_chain:
            result = self.test_model_availability(model_id)
            if result['success']:
                available_models.append(model_id)
                self.console(f"{model_id}: Available ({result['response_time']:.2f}s)")
            else:
                self.console(f"{model_id}: Failed - {result.get('error', 'Unknown error')}")

        # Test fallback logic
        if available_models:
            self.console("Testing fallback logic...")
            self.log("Testing multi-model fallback with sample prompt")

            test_prompt = "Explain the benefits of model fallback strategies in 2 sentences."
            result = self.invoke_with_model_fallback(test_prompt)

            if result['success']:
                self.console(f"Fallback successful: {result['model_id']} ({result['response_time']:.2f}s)")
                self.console(f"\nResults: Model fallback system operational")
            else:
                self.console(f"Fallback failed: {result.get('error', 'Unknown error')}")
                self.console(f"\nResults: Model fallback system failed")
        else:
            self.console("No models available for testing")
            self.console(f"\nResults: No available models found")

        # Fallback benefits
        self.console("\nFallback Benefits:")
        self.console("• Custom model selection logic")
        self.console("• Reliability through model diversity")
        self.console("• Configurable model preference ordering")

        # Implementation notes
        self.console("\nImplementation Notes:")
        self.console("• Consider AWS Intelligent Prompt Routing first")
        self.console("• Use this for custom routing beyond AWS features")
        self.console("• Balance quality vs availability in model ordering")

        # Save detailed log
        self.log("Completed MULTI-MODEL FALLBACK demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate multi-model fallback pattern."""
    client = MultiModelFallback()
    client.demonstrate_multi_model_fallback()

if __name__ == "__main__":
    main()