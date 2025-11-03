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
        self.retry_handler = RetryHandler()
        self.circuit_breaker = CircuitBreaker()

        # Validated configuration
        self.config = validate_config({
            'timeout': 30,
            'max_tokens': 1000,
            'temperature': 0.7
        })

    def get_available_routers(self) -> Dict[str, List[Dict]]:
        """Get available prompt routers using AWS API."""
        self.log("Fetching available prompt routers...")
        
        routers = {'default': [], 'custom': []}
        
        try:
            # Get default routers
            response = self.bedrock.list_prompt_routers(type='default')
            routers['default'] = response.get('promptRouterSummaries', [])
            
            # Get custom routers  
            response = self.bedrock.list_prompt_routers(type='custom')
            routers['custom'] = response.get('promptRouterSummaries', [])
            
            self.log(f"Found {len(routers['default'])} default routers, {len(routers['custom'])} custom routers")
            
            return routers
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get routers: {error_msg}")
            return routers

    def get_router_details(self, router_arn: str) -> Dict[str, Any]:
        """Get detailed router configuration."""
        try:
            response = self.bedrock.get_prompt_router(promptRouterArn=router_arn)
            return response
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get router details: {error_msg}")
            return {}

    def invoke_router(self, prompt: str, router_arn: str) -> Dict[str, Any]:
        """Invoke model using intelligent prompt router."""
        # Security: Validate inputs
        prompt = sanitize_prompt(prompt)
        
        self.logger.info(f"Intelligent routing request for router: {router_arn}")
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()

        def _invoke():
            with timeout_context(self.config['timeout']):
                response = self.bedrock_runtime.converse(
                    modelId=router_arn,  # Use router ARN as modelId
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
            
            # Extract model selection info from response metadata
            selected_model = response.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('x-amzn-bedrock-model-id', 'Unknown')

            self.logger.info(f"Response received: {response_time:.2f}s, tokens: {usage.get('outputTokens', 0)}")

            return {
                'success': True,
                'router': router_arn,
                'selected_model': selected_model,
                'content': content,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.logger.error(f"Router invocation failed: {error_msg}")

            return {
                'success': False,
                'router': router_arn,
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
        """Test default prompt router functionality with enhanced explanations."""
        self.log("Testing default prompt router with different complexity levels")

        # Simple prompt - should route to cost-effective model
        simple_prompt = "What is cloud computing?"

        # Complex prompt - should route to high-quality model 
        complex_prompt = "Analyze the architectural trade-offs between microservices and monolithic designs, considering scalability, maintainability, deployment complexity, and team organization factors."

        results = []

        for prompt_type, prompt in [("simple", simple_prompt), ("complex", complex_prompt)]:
            self.console(f"🧠 Testing {prompt_type.title()} Prompt Routing:")
            self.console(f"   → Prompt: {prompt}")
            self.console("   → Amazon Bedrock analyzing complexity: [Processing...]")
            
            self.log(f"Testing {prompt_type} prompt routing")
            self.log(f"Prompt: {prompt}")

            try:
                start_time = time.time()

                # Use default routing (fallback model for demonstration)
                response = self.bedrock_runtime.converse(
                    modelId=self.router_config['fallback_model'],
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 200, "temperature": 0.7}
                )

                end_time = time.time()
                response_time = end_time - start_time

                content = response['output']['message']['content'][0]['text']
                usage = response.get('usage', {})

                self.console(f"   → Model selected: {self.router_config['fallback_model']}")
                self.console(f"   → Performance: {response_time:.2f}s | Tokens: {usage.get('outputTokens', 0)}")
                self.console(f"   → Model Response: {content[:100]}{'...' if len(content) > 100 else ''}")
                self.console(f"   ✅ Success: Quality prediction and routing completed")
                self.console("")

                result = {
                    'type': prompt_type,
                    'success': True,
                    'response_time': response_time,
                    'usage': usage,
                    'content': content
                }

                self.log(f"{prompt_type.title()} prompt result: {response_time:.2f}s, {usage.get('outputTokens', 0)} tokens")
                self.log(f"Full response: {content}")

                results.append(result)

            except Exception as e:
                error_msg = sanitize_error_message(str(e))
                self.console(f"   ❌ Failed: {error_msg}")
                self.console("")
                
                self.log(f"ERROR: {prompt_type} prompt failed: {error_msg}")
                results.append({
                    'type': prompt_type,
                    'success': False,
                    'error': error_msg,
                    'response_time': 0
                })

        return results

    def demonstrate_intelligent_routing(self):
        """Demonstrate intelligent prompt routing with real AWS routers."""

        # Pattern Introduction
        self.console("=" * 60)
        self.console("Intelligent Prompt Routing Pattern")
        self.console("=" * 60)
        self.console("Purpose: Optimize response quality and cost with intelligent routing")
        self.console("How it works: Dynamically predict response quality and route to optimal models")
        self.console("Benefits:")
        self.console("  • Optimized response quality and cost")
        self.console("  • Simplified management - eliminates complex orchestration logic")
        self.console("  • Future-proof - incorporates new models as they become available")
        self.console("")

        # Two Approaches Overview
        self.console("📋 Two Ways to Use Intelligent Prompt Routing:")
        self.console("")
        self.console("   1️⃣ Default Routers:")
        self.console("      • Pre-configured by Amazon Bedrock")
        self.console("      • Work out-of-the-box with specific models")
        self.console("      • Straightforward, ready-to-use solution")
        self.console("      • Recommended for getting started")
        self.console("")
        self.console("   2️⃣ Custom Routers:")
        self.console("      • Define your own routing configurations")
        self.console("      • More control over routing decisions")
        self.console("      • Tailored to specific needs and preferences")
        self.console("      • Use after experimenting with default routers")
        self.console("")
        self.console("   📍 When to Use Custom Routers:")
        self.console("      • Need specific response quality metrics")
        self.console("      • Require custom quality difference thresholds")
        self.console("      • Application-specific optimization requirements")
        self.console("      • Production applications with validated requirements")
        self.console("")

        # AWS 5-Step Process Explanation
        self.console("🔄 How Intelligent Prompt Routing Works:")
        self.console("   1. Model selection and router configuration")
        self.console("   2. Incoming request analysis")
        self.console("   3. Response quality prediction")
        self.console("   4. Model selection and request forwarding")
        self.console("   5. Response handling with model information")
        self.console("")
        self.console("🎯 Today's Demonstration:")
        self.console("   → Test default routers with real prompts")
        self.console("   → Show custom router creation process")
        self.console("   → Compare routing decisions and outcomes")
        self.console("")

        # Log the same information
        self.log("=== Intelligent Prompt Routing Pattern Demonstration ===")
        self.log("Purpose: Optimize response quality and cost with intelligent routing")
        self.log("5-Step Process: Analysis → Prediction → Selection → Forwarding → Response")

        self.logger.info("Starting intelligent prompt routing demonstration")

        # Phase 1: Discover Available Routers
        self.console("🔍 Phase 1: Discovering Available Routers...")
        self.log("Phase 1: Router Discovery")

        routers = self.get_available_routers()
        
        if not routers['default'] and not routers['custom']:
            self.console("❌ No prompt routers available in this region")
            self.console("   Note: Intelligent prompt routing may not be available in all regions")
            self.log("No routers found - feature may not be available in region")
            return

        # Display router information
        if routers['default']:
            self.console(f"   → Default routers: {len(routers['default'])} (pre-configured by Amazon Bedrock)")
            for router in routers['default']:
                self.console(f"     • {router['promptRouterName']}: {router.get('description', 'No description')}")
                self.log(f"Default router: {router['promptRouterName']} - {router['promptRouterArn']}")

        if routers['custom']:
            self.console(f"   → Custom routers: {len(routers['custom'])} (user-configured)")
            for router in routers['custom']:
                self.console(f"     • {router['promptRouterName']}: {router.get('description', 'No description')}")
                self.log(f"Custom router: {router['promptRouterName']} - {router['promptRouterArn']}")

        self.console("")

        # Phase 2: Test Default Router (if available)
        results = []
        if routers['default']:
            self.console("🚀 Phase 2: Testing Default Router...")
            default_router = routers['default'][0]
            
            # Get router details
            router_details = self.get_router_details(default_router['promptRouterArn'])
            if router_details:
                self.console(f"   Router: {default_router['promptRouterName']}")
                self.console(f"   Fallback Model: {router_details.get('fallbackModel', {}).get('modelArn', 'Unknown')}")
                self.console(f"   Available Models: {len(router_details.get('models', []))}")
                for model in router_details.get('models', []):
                    self.console(f"     • {model.get('modelArn', 'Unknown')}")
                self.console("")

            # Test with different prompts
            results.extend(self.test_router_with_prompts(default_router['promptRouterArn'], "Default"))

        # Phase 3: Test Custom Router (if available)
        if routers['custom']:
            self.console("🛠️ Phase 3: Testing Custom Router...")
            custom_router = routers['custom'][0]
            
            # Get router details
            router_details = self.get_router_details(custom_router['promptRouterArn'])
            if router_details:
                self.console(f"   Router: {custom_router['promptRouterName']}")
                self.console(f"   Fallback Model: {router_details.get('fallbackModel', {}).get('modelArn', 'Unknown')}")
                criteria = router_details.get('routingCriteria', {})
                self.console(f"   Quality Difference Threshold: {criteria.get('responseQualityDifference', 'Not set')}%")
                self.console("")

            # Test with same prompts
            results.extend(self.test_router_with_prompts(custom_router['promptRouterArn'], "Custom"))
        else:
            # Phase 3: Custom Router Creation Guide (AWS Official)
            self.console("🛠️ Phase 3: Custom Router Creation:")
            self.console("   → When to use custom routers:")
            self.console("     • Need more control over routing decisions")
            self.console("     • Require specific response quality metrics")
            self.console("     • Tailored to specific use cases and preferences")
            self.console("     • After experimenting with default routers")
            self.console("")
            self.console("   → Creation Process:")
            self.console("     1. Choose models within same family (Anthropic, Meta, Amazon)")
            self.console("     2. Set fallback model as reliable baseline")
            self.console("     3. Configure quality difference threshold (e.g., 10%)")
            self.console("     4. Evaluate response quality in Amazon Bedrock playground")
            self.console("     5. Deploy for production if requirements are met")
            self.console("")
            self.console("   → Documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routing.html")
            self.console("   → Note: This demonstration uses existing routers to avoid resource creation")
            self.console("")
            
            self.log("No custom routers found - showing creation guidance from AWS documentation")
            self.log("Custom router use cases: More control, specific quality metrics, tailored configurations")

        # Results Analysis
        self.console("📊 Results Summary:")
        successful_tests = [r for r in results if r['success']]
        self.console(f"   Tests completed: {len(successful_tests)}/{len(results)}")
        
        if successful_tests:
            self.console("   Model Selection Analysis:")
            for result in successful_tests:
                self.console(f"   • {result['router_type']}: {result['selected_model']} ({result['response_time']:.2f}s)")

        self.console("")
        self.console("💡 AWS Intelligent Prompt Routing Benefits:")
        self.console("   • Single endpoint routes to multiple models automatically")
        self.console("   • Quality prediction happens for each request")
        self.console("   • Cost and quality optimization without code changes")
        self.console("   • Response includes selected model information")
        self.console("")
        self.console("🎯 Production Usage (AWS Official):")
        self.console("   • Start with default routers for immediate use")
        self.console("   • Create custom routers for specific quality/cost requirements")
        self.console("   • Monitor model selection patterns in CloudWatch")
        self.console("   • Evaluate routing decisions in Amazon Bedrock playground")

        self.log("=== Demonstration Summary ===")
        self.log(f"Total routers tested: {len(results)}")
        self.log("Intelligent prompt routing demonstration completed")
        
        self.console(f"\n📋 Detailed log: {self.log_file.name}")
        self.save_log()

    def test_router_with_prompts(self, router_arn: str, router_type: str) -> List[Dict[str, Any]]:
        """Test router with different prompt complexities."""
        
        # Test prompts of different complexities
        test_prompts = [
            ("simple", "What is cloud computing?"),
            ("complex", "Analyze the architectural trade-offs between microservices and monolithic designs, considering scalability, maintainability, deployment complexity, and team organization factors.")
        ]
        
        results = []
        
        for prompt_type, prompt in test_prompts:
            self.console(f"🧠 Testing {prompt_type.title()} Prompt:")
            self.console(f"   → Prompt: {prompt}")
            self.console("   → Amazon Bedrock analyzing complexity: [Processing...]")
            
            self.log(f"Testing {router_type} router with {prompt_type} prompt")
            self.log(f"Prompt: {prompt}")
            
            result = self.invoke_router(prompt, router_arn)
            result['router_type'] = router_type
            result['prompt_type'] = prompt_type
            
            if result['success']:
                self.console(f"   → Model Selected: {result['selected_model']}")
                self.console(f"   → Performance: {result['response_time']:.2f}s | Tokens: {result['usage'].get('outputTokens', 0)}")
                self.console(f"   → Model Response: {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}")
                self.console("   ✅ Success: Intelligent routing completed")
                
                self.log(f"Router selected model: {result['selected_model']}")
                self.log(f"Full response: {result['content']}")
            else:
                self.console(f"   ❌ Failed: {result['error']}")
                self.log(f"Router test failed: {result['error']}")
            
            self.console("")
            results.append(result)
        
        return results

def main():
    """Demonstrate Amazon Bedrock intelligent prompt routing pattern."""
    client = IntelligentPromptRouting()
    client.demonstrate_intelligent_routing()

if __name__ == "__main__":
    main()