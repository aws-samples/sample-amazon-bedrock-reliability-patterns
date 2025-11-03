#!/usr/bin/env python3
"""
Manual Fallback Patterns

Demonstrates manual fallback strategies when AWS-native solutions don't cover
your specific requirements. Shows three types of fallback approaches:

1. Cross-Region Fallback (same model, different regions)
2. Multi-Model Fallback (different models, same region)  
3. Multi-Provider Fallback (different providers, same region)

Use these patterns when AWS-native features like Cross-Region Inference,
Intelligent Prompt Routing, or Multi-Provider Gateway don't meet your needs.

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

class ManualFallbackPatterns:
    def __init__(self, regions: List[str] = None):
        """Initialize manual fallback patterns demonstration."""
        self.resource_manager = ResourceManager()
        # Default regions with good model availability
        self.regions = regions or ['us-east-1', 'us-east-2', 'us-west-2']
        
        # Use latest model that works with direct invocation
        self.model_id = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        # Artificially induce failover by using wrong version for first region only
        self.demo_model_ids = {
            'us-east-1': 'anthropic.claude-3-5-sonnet-20241022-v5:0'  # v5 doesn't exist - will fail
            # us-east-2 and us-west-2 will use the correct v2 model
        }

        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"manual_fallback_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
        """Save detailed log entries to file with secure permissions."""
        try:
            # Security: Create file with restricted permissions
            self.log_file.touch(mode=0o640)
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=== MANUAL FALLBACK PATTERNS LOG ===\\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\\n")
                f.write(f"Regions: {', '.join(self.regions)}\\n")
                f.write("=" * 50 + "\\n\\n")
                # Security: Sanitize log entries
                for entry in self.log_entries:
                    sanitized_entry = entry.replace(str(Path.home()), "~")
                    f.write(sanitized_entry + "\\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {sanitize_error_message(str(e))}")

    def test_region_availability(self, region: str) -> Dict[str, Any]:
        """Test model availability in a specific region."""
        self.log(f"Testing model availability in region: {region}")

        if region not in self.clients:
            self.log(f"No client available for region: {region}")
            return {'success': False, 'error': 'No client available', 'region': region}

        # Use demo model ID for artificial failover demonstration
        model_to_use = self.demo_model_ids.get(region, self.model_id)
        
        try:
            start_time = time.time()

            response = self.clients[region].converse(
                modelId=model_to_use,
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
                'usage': usage,
                'model_used': model_to_use
            }

        except Exception as e:
            self.log(f"Region {region} test failed: {str(e)}")
            return {
                'success': False,
                'region': region,
                'error': str(e),
                'response_time': 0,
                'model_used': model_to_use
            }

    def invoke_with_fallback(self, prompt: str) -> Dict[str, Any]:
        """Invoke model with cross-region fallback logic."""
        self.log(f"Starting cross-region fallback for prompt: {prompt}")

        for region in self.regions:
            self.log(f"Attempting inference in region: {region}")

            if region not in self.clients:
                self.log(f"No client available for region: {region}")
                continue

            # Use demo model ID for artificial failover demonstration
            model_to_use = self.demo_model_ids.get(region, self.model_id)

            try:
                start_time = time.time()

                response = self.clients[region].converse(
                    modelId=model_to_use,
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 100, "temperature": 0.7}
                )

                end_time = time.time()
                response_time = end_time - start_time

                usage = response.get('usage', {})
                content = response['output']['message']['content'][0]['text']

                self.log(f"Successfully completed inference in region: {region}")
                return {
                    'success': True,
                    'region': region,
                    'response_time': response_time,
                    'usage': usage,
                    'content': content
                }

            except Exception as e:
                self.log(f"Failed in region {region}: {str(e)}")
                continue

        self.log("All regions failed - no successful inference")
        return {
            'success': False,
            'error': 'All regions failed',
            'regions_tried': self.regions
        }

    def demonstrate_manual_fallback_patterns(self):
        """Demonstrate manual fallback patterns with AWS-documented guidance."""

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
                self.logger.info("Manual fallback patterns demonstration completed")

    def _run_demonstration(self):
        """Internal demonstration logic with AWS documentation-based explanations."""

        # Pattern Introduction
        self.console("=" * 60)
        self.console("Manual Fallback Patterns")
        self.console("=" * 60)
        
        # What is this (AWS Official)
        self.console("📋 What is this:")
        self.console("Manual fallback strategies when AWS-native solutions don't cover")
        self.console("your specific requirements. Three types of fallback approaches:")
        self.console("")
        self.console("🔄 Cross-Region Fallback (same model, different regions)")
        self.console("🔄 Multi-Model Fallback (different models, same region)")
        self.console("🔄 Multi-Provider Fallback (different providers, same region)")
        self.console("")

        # When to use it (from README)
        self.console("🎯 When to use:")
        self.console("• Need regional backup? → Cross-Region Fallback")
        self.console("• Need model alternatives? → Multi-Model Fallback")
        self.console("• Need provider diversity? → Multi-Provider Fallback")
        self.console("")
        
        # AWS-Native First Approach
        self.console("⚠️  Important - AWS-Native First:")
        self.console("Always try AWS-managed solutions first:")
        self.console("• Cross-Region Inference for automatic regional routing")
        self.console("• Intelligent Prompt Routing for automatic model selection")
        self.console("• Multi-Provider Gateway for unified API across providers")
        self.console("• Use manual fallback only when AWS-native features insufficient")
        self.console("")

        # Working Demonstration
        self.console("🚀 Working Demonstration: Cross-Region Fallback")
        self.console(f"Model: {self.model_id} (Claude 3.5 Sonnet v2 - latest)")
        self.console(f"Available in regions: {', '.join(self.regions)}")
        self.console("⚠️  Note: Artificially inducing failover for demonstration")
        self.console(f"   - {self.regions[0]}: Using v5 (doesn't exist - will fail)")
        self.console(f"   - {self.regions[1]}: Using v2 (correct version - will succeed)")
        self.console(f"   - {self.regions[2]}: Using v2 (backup)")
        self.console("")
        
        # Test each region individually
        self.console("Testing region availability...")
        available_regions = []
        for i, region in enumerate(self.regions, 1):
            self.console(f"Call {i}: Trying {region}... (model: {self.demo_model_ids.get(region, self.model_id)})")
            result = self.test_region_availability(region)
            if result['success']:
                available_regions.append(region)
                self.console(f"   ✅ SUCCESS: {region} responded in {result['response_time']:.2f}s")
                self.console(f"   📊 Tokens: {result['usage'].get('inputTokens', 0)} input, {result['usage'].get('outputTokens', 0)} output")
            else:
                error_msg = result.get('error', 'Unknown error')
                model_used = result.get('model_used', '')
                if region == 'us-east-1' and 'v5:0' in model_used:
                    self.console(f"   ❌ FAILED: {region} - Model version v5 doesn't exist (artificial failover)")
                elif 'ValidationException' in error_msg:
                    self.console(f"   ❌ FAILED: {region} - Model validation error")
                elif 'AccessDeniedException' in error_msg:
                    self.console(f"   ❌ FAILED: {region} - Access denied (check model access)")
                else:
                    self.console(f"   ❌ FAILED: {region} - {error_msg[:100]}...")
        
        self.console("")
        
        # Test fallback logic
        if available_regions:
            self.console("Testing fallback logic with new prompt...")
            test_prompt = "What are the benefits of cross-region deployment?"
            self.console(f"Prompt: {test_prompt}")
            
            result = self.invoke_with_fallback(test_prompt)
            
            if result['success']:
                self.console(f"   ✅ FALLBACK SUCCESS: Used {result['region']} ({result['response_time']:.2f}s)")
                self.console(f"   📊 Final tokens: {result['usage'].get('inputTokens', 0)} input, {result['usage'].get('outputTokens', 0)} output")
                self.console(f"   📝 Response preview: {result.get('content', 'No content')[:100]}...")
            else:
                self.console(f"   ❌ FALLBACK FAILED: {result.get('error', 'Unknown error')}")
        else:
            self.console("❌ No regions available - all regions failed")
        
        self.console("")
        self.console("📊 Results Summary:")
        self.console(f"   Available regions: {len(available_regions)}/{len(self.regions)}")
        if available_regions:
            self.console(f"   Successful fallback: {available_regions[0]} (first available)")
            self.console(f"   Fallback order: {' → '.join(self.regions)}")
        else:
            self.console("   No successful regions found")
        
        self.console("")
        self.console("💡 Pattern Extensions:")
        self.console("This Cross-Region Fallback can be extended for other scenarios:")
        self.console("")
        self.console("🔄 Multi-Model Fallback (different models, same region):")
        self.console("   models = ['claude-3-5-sonnet-v2', 'claude-3-haiku', 'titan-express']")
        self.console("   # Same fallback logic, iterate through models instead of regions")
        self.console("")
        self.console("🔄 Multi-Provider Fallback (different providers, same region):")
        self.console("   providers = {")
        self.console("       'anthropic': 'claude-3-5-sonnet-v2',")
        self.console("       'amazon': 'nova-lite-v1',")
        self.console("       'meta': 'llama-3-1-8b'")
        self.console("   }")
        self.console("   # Same fallback logic, iterate through providers instead of regions")
        self.console("")
        self.console("🔧 Implementation: Replace the regions list with your fallback array")
        self.console("   and use the same try/catch logic demonstrated above.")

        # Log the demonstration
        self.log("=== Manual Fallback Patterns Demonstration ===")
        self.log("Purpose: Manual fallback strategies for AWS-native solution gaps")
        self.log("Demonstrated: Cross-Region Fallback (same model, different regions)")
        self.log("Extensions: Multi-Model and Multi-Provider fallback using same logic")
        self.log("=== Demonstration Summary ===")
        self.log("Manual fallback patterns demonstration completed")
        
        self.console("")
        self.console(f"📋 Detailed log: {self.log_file.name}")
        self.save_log()

def main():
    """Main execution function with error handling."""
    try:
        patterns = ManualFallbackPatterns()
        patterns.demonstrate_manual_fallback_patterns()
    except KeyboardInterrupt:
        print("\\nManual fallback patterns demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Manual fallback patterns demonstration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()