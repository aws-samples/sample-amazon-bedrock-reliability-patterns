#!/usr/bin/env python3
"""
Provisioned Throughput Pattern

Demonstrates reserved capacity with guaranteed performance through Amazon Bedrock
Provisioned Throughput. Purchase dedicated model units with commitment terms
for predictable workloads and consistent performance requirements.

Use provisioned throughput when you need guaranteed capacity, predictable costs,
and consistent performance for production workloads.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html
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

class ProvisionedThroughput:
    def __init__(self, region: str = None):
        """Initialize provisioned throughput demonstration."""
        self.region = region or get_secure_region()
        self.bedrock = boto3.client('bedrock', region_name=self.region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"provisioned_throughput_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = setup_logging(self.log_file)
        
        # Initialize log entries
        self.log_entries = []

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
                f.write("AMAZON BEDROCK PROVISIONED THROUGHPUT PATTERN - DETAILED LOG\n")
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

    def check_provisioned_capacity(self) -> List[Dict[str, Any]]:
        """Check existing provisioned throughput capacity."""
        self.log("Checking existing provisioned throughput capacity")

        try:
            response = self.bedrock.list_provisioned_model_throughputs()
            throughputs = response.get('provisionedModelSummaries', [])

            self.log(f"Found {len(throughputs)} provisioned throughput instances")
            for throughput in throughputs:
                self.log(f"Provisioned capacity: {throughput}")

            return throughputs

        except Exception as e:
            self.log(f"ERROR: {sanitize_error_message(str(e))}")
            return []

    def demonstrate_provisioned_throughput(self):
        """Demonstrate provisioned throughput with clean console output."""

        # Initialize pattern demonstration
        self.console("Provisioned Throughput Pattern")
        self.console("Dedicated model capacity with performance guarantees")

        # Detailed logging
        self.log("Starting PROVISIONED THROUGHPUT demonstration")
        self.log("Initializing provisioned throughput demonstration")
        self.log(f"Source region: {self.region}")

        # Check existing capacity
        self.console("Checking provisioned capacity...")
        self.log("Checking for existing provisioned throughput instances")

        throughputs = self.check_provisioned_capacity()

        if throughputs:
            active_throughputs = [t for t in throughputs if t.get('status') == 'InService']
            self.console(f"Found {len(active_throughputs)} active provisioned instances")

            if active_throughputs:
                # Test with provisioned capacity
                self.console("Testing provisioned throughput...")

                # Use the first active provisioned throughput
                provisioned_arn = active_throughputs[0]['provisionedModelArn']
                self.log(f"Testing with provisioned model: {provisioned_arn}")

                try:
                    start_time = time.time()

                    response = self.bedrock_runtime.converse(
                        modelId=provisioned_arn,
                        messages=[{"role": "user", "content": [{"text": "Explain the benefits of provisioned throughput in 2 sentences."}]}],
                        inferenceConfig={"maxTokens": 200, "temperature": 0.7}
                    )

                    end_time = time.time()
                    response_time = end_time - start_time

                    usage = response.get('usage', {})
                    self.console(f"Provisioned: {response_time:.2f}s, {usage.get('outputTokens', 0)} tokens")

                    self.log(f"Provisioned throughput test successful: {response_time:.2f}s")
                    self.log(f"Response: {response['output']['message']['content'][0]['text']}")

                    self.console(f"\nResults: 1/1 tests passed")

                except Exception as e:
                    self.log(f"ERROR: {sanitize_error_message(str(e))}")
                    self.log(f"ERROR: Provisioned throughput test failed: {str(e)}")
                    self.console(f"\nResults: 0/1 tests passed")
            else:
                self.console("No active provisioned instances available")
                self.console(f"\nResults: Provisioned capacity exists but not active")
        else:
            self.console("No provisioned capacity found")
            self.console(f"\nResults: No provisioned throughput configured")

        # Capacity planning guidance
        self.console("\nCapacity Planning:")
        self.console("• 1-month or 6-month commitment terms available")
        self.console("• Model units determine throughput capacity")
        self.console("• Reserved pricing with upfront commitment")

        # Save detailed log
        self.log("Completed PROVISIONED THROUGHPUT demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate Amazon Bedrock provisioned throughput pattern."""
    client = ProvisionedThroughput()
    client.demonstrate_provisioned_throughput()

if __name__ == "__main__":
    main()