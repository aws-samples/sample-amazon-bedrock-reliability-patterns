#!/usr/bin/env python3
"""
Cross-Region Inference Pattern

Demonstrates AWS-managed cross-region inference that automatically distributes 
traffic across multiple AWS Regions for increased throughput capacity.
"""

import boto3
import json
import sys
import time
import os
import re
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

class CrossRegionInference:
    def __init__(self, region: str = None):
        """Initialize with cross-region inference profiles."""
        self.region = region or get_secure_region()
        if not re.match(r'^[a-z0-9-]+$', self.region):
            raise ValueError("Invalid region format")

        # Initialize clients with timeout
        self.client = boto3.client('bedrock-runtime', region_name=self.region)
        self.bedrock_client = boto3.client('bedrock', region_name=self.region)

        # Setup enhanced logging and utilities
        self.log_file = create_secure_log_file("cross_region_inference")
        self.logger = setup_logging(self.log_file)
        self.rate_limiter = RateLimiter()
        self.retry_handler = RetryHandler()
        self.circuit_breaker = CircuitBreaker()
        self.resource_manager = ResourceManager()

        # Initialize log entries
        self.log_entries = []

        # Validated configuration
        self.config = validate_config({
            'timeout': 30,
            'max_tokens': 1000,
            'temperature': 0.7
        })

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
            # Security: Create file with restricted permissions
            self.log_file.touch(mode=0o640)
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=== CROSS-REGION INFERENCE LOG ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Region: {self.region}\n")
                f.write("=" * 50 + "\n\n")
                # Security: Sanitize log entries
                for entry in self.log_entries:
                    sanitized_entry = entry.replace(str(Path.home()), "~")
                    f.write(sanitized_entry + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {sanitize_error_message(str(e))}")

    def invoke_model(self, prompt: str, profile_id: str) -> Dict[str, Any]:
        """Invoke model using cross-region inference profile with enhanced error handling.
        
        Example:
        >>> result = self.invoke_model("Hello", "model-id")
        >>> print(result['success'])
        True
        """
        # Security: Validate inputs
        prompt = sanitize_prompt(prompt)
        if not validate_model_id(profile_id):
            raise ValueError("Invalid model/profile ID")

        self.logger.info(f"Cross-region inference request for profile: {profile_id}")

        # Rate limiting
        self.rate_limiter.wait_if_needed()

        def _invoke():
            with timeout_context(self.config['timeout']):
                response = self.client.converse(
                    modelId=profile_id,
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
                'profile': profile_id,
                'content': content,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.logger.error(f"Cross-region inference failed: {error_msg}")

            return {
                'success': False,
                'profile': profile_id,
                'error': error_msg,
                'response_time': 0
            }

    def get_available_profiles(self) -> List[Dict[str, Any]]:
        """Get available cross-region inference profiles."""
        self.log("Fetching available cross-region inference profiles...")

        try:
            response = self.bedrock_client.list_inference_profiles()
            profiles = response.get('inferenceProfileSummaries', [])

            self.log(f"Found {len(profiles)} cross-region inference profiles")
            for profile in profiles:
                self.log(f"Profile: {profile}")

            return profiles

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: {error_msg}")
            return []

    def demonstrate_cross_region_inference(self):
        """Demonstrate cross-region inference with enhanced error handling."""

        with self.resource_manager:
            try:
                self._run_demonstration()
            except KeyboardInterrupt:
                self.console("Demonstration interrupted by user")
                raise
            except Exception as e:
                error_msg = sanitize_error_message(str(e))
                self.console(f"Demonstration failed: {error_msg}")
                self.logger.error(f"Demonstration failed: {error_msg}")
                raise
            finally:
                self.logger.info("Cross-region inference demonstration completed")

    def _run_demonstration(self):
        """Internal demonstration logic with AWS documentation-based explanations."""
        
        # Pattern Introduction (AWS Official)
        self.console("=" * 60)
        self.console("Cross-Region Inference Pattern")
        self.console("=" * 60)
        self.console("Purpose: Increase throughput with cross-Region inference (AWS Official)")
        self.console("How it works: Amazon Bedrock automatically selects optimal AWS Regions (AWS Official)")
        self.console("Benefits (AWS Official):")
        self.console("  • Seamlessly manage unplanned traffic bursts")
        self.console("  • Distribute traffic across multiple AWS Regions for higher throughput")
        self.console("  • Optimize available resources and increase model throughput")
        self.console("")

        # Log the same information
        self.log("=== Cross-Region Inference Pattern Demonstration ===")
        self.log("AWS Official Purpose: Increase throughput with cross-Region inference")
        self.log("Mechanism: Amazon Bedrock automatically selects optimal commercial AWS Regions")
        self.log("Key Benefits: Traffic distribution, unplanned burst management, resource optimization")

        self.logger.info("Starting cross-region inference demonstration")

        # Profile Discovery Phase
        self.console("🔍 Discovering inference profiles...")
        self.log("Phase 1: Profile Discovery")

        def get_profiles():
            response = self.bedrock_client.list_inference_profiles()
            return response.get('inferenceProfileSummaries', [])

        try:
            profiles = self.retry_handler.retry_with_backoff(get_profiles)
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.console("❌ No cross-region profiles available")
            self.log(f"ERROR: Failed to get profiles: {error_msg}")
            self.logger.error(f"Failed to get profiles: {error_msg}")
            return

        if not profiles:
            self.console("❌ No cross-region profiles available in this region")
            self.log("No inference profiles found")
            return

        # Categorize profiles using AWS terminology
        regional_profiles = [p for p in profiles if not p['inferenceProfileId'].startswith('global.')]
        global_profiles = [p for p in profiles if p['inferenceProfileId'].startswith('global.')]

        self.console(f"   → Regional profiles: {len(regional_profiles)} (tied to specific geography)")
        self.console(f"   → Global profiles: {len(global_profiles)} (route to optimal commercial AWS Region)")
        self.console("")
        self.console(f"   Source Region: {self.region} (where you make the API request)")
        self.console("   Destination Regions: Where Amazon Bedrock routes for optimal performance")
        self.console("")

        self.log(f"Found {len(profiles)} total inference profiles")
        self.log(f"Regional profiles: {len(regional_profiles)}")
        self.log(f"Global profiles: {len(global_profiles)}")
        self.log(f"Source region: {self.region}")

        # Test profiles with detailed explanations
        results = []

        if regional_profiles:
            profile_id = regional_profiles[0]['inferenceProfileId']
            prompt = "Explain AWS cross-region inference benefits in 2 sentences."
            
            self.console("🚀 Testing Regional Profile:")
            self.console(f"   Profile: {profile_id}")
            self.console(f"   → Source Region: {self.region}")
            self.console(f"   → Prompt: {prompt}")
            self.console("   → Amazon Bedrock routing decision: [Processing...]")
            
            self.log(f"Testing regional profile: {profile_id}")
            self.log(f"Prompt: {prompt}")
            
            result = self.invoke_model(prompt, profile_id)
            results.append(('Regional', result))

            if result['success']:
                self.console(f"   → Destination Region: Automatically selected by AWS")
                self.console(f"   → Performance: {result['response_time']:.2f}s | Tokens: {result.get('usage', {}).get('outputTokens', 0)}")
                self.console(f"   → Model Response: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
                self.console("   ✅ Success: Cross-region inference handled traffic distribution")
                self.log(f"Regional test successful: {result['response_time']:.2f}s, {result.get('usage', {}).get('outputTokens', 0)} tokens")
                self.log(f"Full response: {result['content']}")
            else:
                self.console(f"   ❌ Failed: {result['error']}")
                self.log(f"Regional test failed: {result['error']}")
            self.console("")

        if global_profiles:
            profile_id = global_profiles[0]['inferenceProfileId']
            prompt = "Describe global inference capacity benefits in 2 sentences."
            
            self.console("🌍 Testing Global Profile:")
            self.console(f"   Profile: {profile_id}")
            self.console(f"   → Source Region: {self.region}")
            self.console(f"   → Prompt: {prompt}")
            self.console("   → Amazon Bedrock routing decision: [Processing...]")
            
            self.log(f"Testing global profile: {profile_id}")
            self.log(f"Prompt: {prompt}")
            
            result = self.invoke_model(prompt, profile_id)
            results.append(('Global', result))

            if result['success']:
                self.console(f"   → Destination Region: Optimal commercial region selected")
                self.console(f"   → Performance: {result['response_time']:.2f}s | Tokens: {result.get('usage', {}).get('outputTokens', 0)}")
                self.console(f"   → Model Response: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
                self.console("   ✅ Success: Global inference profile found optimal capacity")
                self.log(f"Global test successful: {result['response_time']:.2f}s, {result.get('usage', {}).get('outputTokens', 0)} tokens")
                self.log(f"Full response: {result['content']}")
            else:
                self.console(f"   ❌ Failed: {result['error']}")
                self.log(f"Global test failed: {result['error']}")
            self.console("")

        # Results Summary with AWS Context
        successful_tests = sum(1 for _, result in results if result['success'])
        total_tests = len(results)

        self.console("📊 Results Summary:")
        self.console(f"   Tests passed: {successful_tests}/{total_tests}")
        
        if successful_tests > 0:
            self.console("   AWS Routing: Automatic region selection performed successfully")
            self.console("   Traffic Distribution: Cross-region inference operational")
        
        self.console("")
        self.console("💡 AWS Cross-Region Inference Benefits:")
        self.console("   • Utilizes compute across AWS Regions for increased throughput")
        self.console("   • Enables seamless management of unplanned traffic bursts")
        self.console("   • Optimizes available resources automatically")
        self.console("   • No code changes required for different regions")
        self.console("")
        self.console("🎯 Production Usage:")
        self.console("   • Regional profiles: For geography-specific requirements (US, EU, APAC)")
        self.console("   • Global profiles: For maximum capacity access worldwide")
        self.console("   • Monitor: CloudWatch metrics for routing patterns")

        self.log("=== Demonstration Summary ===")
        self.log(f"Total tests: {total_tests}, Successful: {successful_tests}")
        self.log("Cross-region inference demonstration completed")
        
        self.console(f"\n📋 Detailed log: {self.log_file.name}")
        self.save_log()

def main():
    """Main execution function with error handling."""
    try:
        inference = CrossRegionInference()
        inference.demonstrate_cross_region_inference()
    except KeyboardInterrupt:
        print("\nCross-region inference demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Cross-region inference demonstration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()