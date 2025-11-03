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
        
        # Security: Rate limiter and other utilities
        self.rate_limiter = RateLimiter()
        self.retry_handler = RetryHandler()
        self.circuit_breaker = CircuitBreaker()

        # Validated configuration
        self.config = validate_config({
            'timeout': 30,
            'max_tokens': 1000,
            'temperature': 0.7
        })

    def get_provisioned_throughputs(self) -> List[Dict[str, Any]]:
        """Get available provisioned throughputs using AWS API."""
        self.log("Fetching available provisioned throughputs...")
        
        try:
            response = self.bedrock.list_provisioned_model_throughputs()
            throughputs = response.get('provisionedModelSummaries', [])
            
            self.log(f"Found {len(throughputs)} provisioned throughputs")
            for throughput in throughputs:
                self.log(f"Throughput: {throughput['provisionedModelName']} - {throughput['provisionedModelArn']}")
            
            return throughputs
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get provisioned throughputs: {error_msg}")
            return []

    def get_throughput_details(self, throughput_arn: str) -> Dict[str, Any]:
        """Get detailed provisioned throughput configuration."""
        try:
            response = self.bedrock.get_provisioned_model_throughput(provisionedModelId=throughput_arn)
            return response
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get throughput details: {error_msg}")
            return {}

    def invoke_provisioned_model(self, prompt: str, model_arn: str) -> Dict[str, Any]:
        """Invoke model using provisioned throughput."""
        # Security: Validate inputs
        prompt = sanitize_prompt(prompt)
        
        self.logger.info(f"Provisioned throughput request for model: {model_arn}")
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()

        def _invoke():
            with timeout_context(self.config['timeout']):
                response = self.bedrock_runtime.converse(
                    modelId=model_arn,  # Use provisioned model ARN
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={
                        "maxTokens": self.config['max_tokens'],
                        "temperature": self.config['temperature']
                    }
                )
                return response

        try:
            start_time = time.time()
            
            # Use circuit breaker and retry logic
            response = self.circuit_breaker.call(
                self.retry_handler.retry_with_backoff, _invoke
            )
            
            end_time = time.time()
            response_time = end_time - start_time

            content = response['output']['message']['content'][0]['text']
            usage = response.get('usage', {})

            self.logger.info(f"Response received: {response_time:.2f}s, tokens: {usage.get('outputTokens', 0)}")

            return {
                'success': True,
                'model_arn': model_arn,
                'content': content,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.logger.error(f"Provisioned model invocation failed: {error_msg}")

            return {
                'success': False,
                'model_arn': model_arn,
                'error': error_msg,
                'response_time': 0
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
        """Demonstrate provisioned throughput with enhanced explanations."""

        # Pattern Introduction
        self.console("=" * 60)
        self.console("Provisioned Throughput Pattern")
        self.console("=" * 60)
        self.console("Purpose: Receive guaranteed throughput at fixed cost")
        self.console("How it works: Purchase dedicated model units with commitment terms")
        self.console("Benefits:")
        self.console("  • Guaranteed capacity and consistent performance")
        self.console("  • Fixed cost with discounted rates for longer commitments")
        self.console("  • Predictable throughput for production workloads")
        self.console("")

        # Commitment Options Overview
        self.console("📋 Provisioned Throughput Options:")
        self.console("")
        self.console("   💰 Commitment Terms:")
        self.console("      • No commitment: Hourly pricing (custom models only)")
        self.console("      • 1-month commitment: Available for base and custom models")
        self.console("      • 6-month commitment: Available for base and custom models")
        self.console("      • Longer commitments = discounted rates")
        self.console("")
        self.console("   🔧 Model Units (MU):")
        self.console("      • Specify throughput in Model Units")
        self.console("      • Each MU delivers specific input/output tokens per minute")
        self.console("      • Throughput level varies by model type")
        self.console("")
        self.console("   📍 When to Use Provisioned Throughput:")
        self.console("      • Predictable, consistent workloads")
        self.console("      • Need guaranteed capacity and performance")
        self.console("      • Cost predictability for production applications")
        self.console("      • High-volume applications with steady traffic")
        self.console("")

        # Log the same information
        self.log("=== Provisioned Throughput Pattern Demonstration ===")
        self.log("Purpose: Guaranteed throughput at fixed cost with commitment terms")
        self.log("Key Benefits: Guaranteed capacity, fixed cost, predictable performance")

        self.logger.info("Starting provisioned throughput demonstration")

        # Phase 1: Discover Existing Provisioned Throughput
        self.console("🔍 Phase 1: Discovering Provisioned Throughput...")
        self.log("Phase 1: Provisioned Throughput Discovery")

        throughputs = self.get_provisioned_throughputs()
        
        if not throughputs:
            self.console("❌ No provisioned throughput found in this region")
            self.console("   Note: Provisioned throughput must be purchased separately")
            self.log("No provisioned throughput found")
            
            # Show creation guidance
            self._show_creation_guidance()
            return

        # Display throughput information
        active_throughputs = [t for t in throughputs if t.get('status') == 'InService']
        
        self.console(f"   → Total provisioned throughputs: {len(throughputs)}")
        self.console(f"   → Active (InService): {len(active_throughputs)}")
        
        for throughput in throughputs:
            status = throughput.get('status', 'Unknown')
            name = throughput.get('provisionedModelName', 'Unknown')
            self.console(f"     • {name}: {status}")
            self.log(f"Throughput: {name} - Status: {status} - ARN: {throughput.get('provisionedModelArn', 'Unknown')}")

        self.console("")

        # Phase 2: Test Active Provisioned Throughput
        if active_throughputs:
            self.console("🚀 Phase 2: Testing Provisioned Throughput...")
            
            for i, throughput in enumerate(active_throughputs[:2]):  # Test up to 2
                throughput_arn = throughput['provisionedModelArn']
                throughput_name = throughput['provisionedModelName']
                
                # Get throughput details
                details = self.get_throughput_details(throughput_arn)
                if details:
                    self.console(f"   Throughput: {throughput_name}")
                    self.console(f"   Model Units: {details.get('modelUnits', 'Unknown')}")
                    self.console(f"   Base Model: {details.get('modelArn', 'Unknown')}")
                    commitment = details.get('commitmentDuration', 'Unknown')
                    self.console(f"   Commitment: {commitment}")
                    self.console("")

                # Test with prompt
                prompt = f"Explain the benefits of provisioned throughput for production workloads in 2 sentences."
                
                self.console(f"🧠 Testing Provisioned Model {i+1}:")
                self.console(f"   → Prompt: {prompt}")
                self.console("   → Using guaranteed capacity: [Processing...]")
                
                self.log(f"Testing provisioned throughput: {throughput_name}")
                self.log(f"Prompt: {prompt}")
                
                result = self.invoke_provisioned_model(prompt, throughput_arn)
                
                if result['success']:
                    self.console(f"   → Guaranteed Performance: {result['response_time']:.2f}s | Tokens: {result['usage'].get('outputTokens', 0)}")
                    self.console(f"   → Model Response: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
                    self.console("   ✅ Success: Provisioned throughput delivered guaranteed performance")
                    
                    self.log(f"Provisioned test successful: {result['response_time']:.2f}s")
                    self.log(f"Full response: {result['content']}")
                else:
                    self.console(f"   ❌ Failed: {result['error']}")
                    self.log(f"Provisioned test failed: {result['error']}")
                
                self.console("")

            # Results Summary
            self.console("📊 Results Summary:")
            self.console(f"   Active provisioned throughputs tested: {len(active_throughputs)}")
            self.console("   Performance: Guaranteed capacity with consistent response times")
            self.console("   Cost: Fixed pricing based on model units and commitment")
        else:
            self.console("⚠️ Phase 2: No Active Provisioned Throughput")
            self.console("   Found provisioned throughput but none are InService")
            self.console("   Status may be: Creating, Updating, or Failed")

        self.console("")
        self.console("💡 Provisioned Throughput Benefits:")
        self.console("   • Guaranteed capacity - no throttling during peak usage")
        self.console("   • Predictable performance - consistent response times")
        self.console("   • Fixed cost - budget predictability with commitment discounts")
        self.console("   • Production ready - designed for mission-critical workloads")
        self.console("")

        # Show creation guidance
        self._show_creation_guidance()

        self.log("=== Demonstration Summary ===")
        self.log(f"Total provisioned throughputs: {len(throughputs)}")
        self.log(f"Active throughputs: {len(active_throughputs)}")
        self.log("Provisioned throughput demonstration completed")
        
        self.console(f"\n📋 Detailed log: {self.log_file.name}")
        self.save_log()

    def _show_creation_guidance(self):
        """Show provisioned throughput creation guidance."""
        self.console("🛠️ Provisioned Throughput Creation:")
        self.console("   → Purchase Process:")
        self.console("     1. Choose base or custom model")
        self.console("     2. Select number of model units (MU)")
        self.console("     3. Choose commitment duration (1-month, 6-month)")
        self.console("     4. Review pricing and purchase")
        self.console("     5. Wait for InService status (can take several minutes)")
        self.console("")
        self.console("   → Pricing Considerations:")
        self.console("     • Longer commitments receive discounted rates")
        self.console("     • Model units determine throughput capacity")
        self.console("     • Fixed cost regardless of actual usage")
        self.console("     • No commitment option available for custom models only")
        self.console("")
        self.console("   → Documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html")
        self.console("   → Note: This demonstration uses existing throughput to avoid charges,")
        self.console("           if none exists, steps and guidance are shown for creating one if needed")
        
        self.log("Showing provisioned throughput creation guidance")
        self.log("Creation process: Model selection → MU configuration → Commitment → Purchase")

def main():
    """Demonstrate Amazon Bedrock provisioned throughput pattern."""
    client = ProvisionedThroughput()
    client.demonstrate_provisioned_throughput()

if __name__ == "__main__":
    main()