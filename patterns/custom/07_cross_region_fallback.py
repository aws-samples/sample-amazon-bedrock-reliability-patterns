#!/usr/bin/env python3
"""
Manual Cross-Region Fallback Pattern

Demonstrates manual cross-region fallback for models not supported in AWS 
Cross-Region Inference profiles. Provides custom region failover logic 
when AWS-native cross-region features don't support your specific model.

Use this pattern when your model isn't available in AWS Cross-Region Inference 
profiles or you need custom region selection logic.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
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

class ManualCrossRegionFallback:
    def __init__(self, regions: List[str] = None):
        """Initialize manual cross-region fallback."""
        self.resource_manager = ResourceManager()
        # Default regions with good model availability
        self.regions = regions or ['us-east-1', 'us-west-2', 'eu-west-1']

        # Use a model that might not be in cross-region inference profiles
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'

        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"cross_region_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = setup_logging(self.log_file)
        
        # Initialize log entries
        self.log_entries = []

        # Initialize clients for each region
        self.clients = {}
        for region in self.regions:
            try:
                self.clients[region] = boto3.client('bedrock-runtime', region_name=region)
                self.log(f"Initialized client for region: {region}")
            except Exception as e:
                self.log(f"Failed to initialize client for {region}: {str(e)}")

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
                f.write("MANUAL CROSS-REGION FALLBACK PATTERN - DETAILED LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Regions: {', '.join(self.regions)}\n")
                f.write(f"Model ID: {self.model_id}\n")
                f.write(f"Log File: {self.log_file}\n")
                f.write("=" * 80 + "\n\n")
                f.write("\n".join(self.log_entries))
                f.write(f"\n\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {e}")

    def test_region_availability(self, region: str) -> Dict[str, Any]:
        """Test model availability in a specific region."""
        self.log(f"Testing model availability in region: {region}")

        if region not in self.clients:
            self.log(f"No client available for region: {region}")
            return {'success': False, 'error': 'No client available', 'region': region}

        try:
            start_time = time.time()

            response = self.clients[region].converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": "Test message for region availability."}]}],
                inferenceConfig={"maxTokens": 50, "temperature": 0.7}
            )

            end_time = time.time()
            response_time = end_time - start_time

            usage = response.get('usage', {})

            self.log(f"Region {region} test successful: {response_time:.2f}s")
            self.log(f"Token usage: {json.dumps(usage, indent=2)}")

            return {
                'success': True,
                'region': region,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            self.log(f"Region {region} test failed: {str(e)}")
            return {
                'success': False,
                'region': region,
                'error': str(e),
                'response_time': 0
            }

    def invoke_with_fallback(self, prompt: str) -> Dict[str, Any]:
        """Invoke model with cross-region fallback logic."""
        self.log(f"Starting cross-region fallback for prompt: {prompt}")

        for region in self.regions:
            self.log(f"Attempting inference in region: {region}")

            result = self.test_region_availability(region)

            if result['success']:
                self.log(f"Successfully completed inference in region: {region}")
                return result
            else:
                self.log(f"Failed in region {region}, trying next region")
                continue

        self.log("All regions failed - no successful inference")
        return {
            'success': False,
            'error': 'All regions failed',
            'regions_tried': self.regions
        }

    def demonstrate_cross_region_fallback(self):
        """Demonstrate manual cross-region fallback with clean console output."""

        # Initialize pattern demonstration
        self.console("Manual Cross-Region Fallback Pattern")
        self.console("Custom region failover for unsupported models")

        # Detailed logging
        self.log("Starting MANUAL CROSS-REGION FALLBACK demonstration")
        self.log("Initializing manual cross-region fallback demonstration")
        self.log(f"Target regions: {', '.join(self.regions)}")
        self.log(f"Model ID: {self.model_id}")

        # Test region availability
        self.console("Testing region availability...")
        self.log("Testing model availability across regions")

        available_regions = []
        for region in self.regions:
            result = self.test_region_availability(region)
            if result['success']:
                available_regions.append(region)
                self.console(f"{region}: Available ({result['response_time']:.2f}s)")
            else:
                self.console(f"{region}: Failed - {result.get('error', 'Unknown error')}")

        # Test fallback logic
        if available_regions:
            self.console("Testing fallback logic...")
            self.log("Testing cross-region fallback with sample prompt")

            test_prompt = "Explain the benefits of cross-region failover in 2 sentences."
            result = self.invoke_with_fallback(test_prompt)

            if result['success']:
                self.console(f"Fallback successful: {result['region']} ({result['response_time']:.2f}s)")
                self.console(f"\nResults: Fallback system operational")
            else:
                self.console(f"Fallback failed: {result.get('error', 'Unknown error')}")
                self.console(f"\nResults: Fallback system failed")
        else:
            self.console("No regions available for testing")
            self.console(f"\nResults: No available regions found")

        # Fallback benefits
        self.console("\nFallback Benefits:")
        self.console("• Custom region selection logic")
        self.console("• Support for models not in cross-region profiles")
        self.console("• Configurable failover ordering")

        # Implementation notes
        self.console("\nImplementation Notes:")
        self.console("• Always try AWS Cross-Region Inference first")
        self.console("• Use this only when AWS-native features insufficient")
        self.console("• Consider latency implications of region selection")

        # Save detailed log
        self.log("Completed MANUAL CROSS-REGION FALLBACK demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate manual cross-region fallback pattern."""
    client = ManualCrossRegionFallback()
    client.demonstrate_cross_region_fallback()

if __name__ == "__main__":
    main()