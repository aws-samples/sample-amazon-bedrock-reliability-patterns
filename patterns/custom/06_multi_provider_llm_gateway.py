#!/usr/bin/env python3
"""
Multi-Provider LLM Gateway Pattern

References official AWS Solutions Guidance for unified API across multiple AI providers.
Provides provider-level failover and load balancing when AWS-native solutions
don't support your specific requirements.

For more information:
https://aws-solutions-library-samples.github.io/ai-ml/guidance-for-multi-provider-generative-ai-gateway-on-aws.html
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

class MultiProviderGateway:
    def __init__(self, region: str = None):
        """Initialize multi-provider gateway demonstration."""
        self.region = region or get_secure_region()

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"multi_provider_gateway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
        """Save detailed log entries to file with secure permissions."""
        try:
            # Security: Create file with restricted permissions
            self.log_file.touch(mode=0o640)
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=== MULTI-PROVIDER LLM GATEWAY LOG ===\\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\\n")
                f.write(f"Region: {self.region}\\n")
                f.write("=" * 50 + "\\n\\n")
                # Security: Sanitize log entries
                for entry in self.log_entries:
                    sanitized_entry = entry.replace(str(Path.home()), "~")
                    f.write(sanitized_entry + "\\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {sanitize_error_message(str(e))}")

    def demonstrate_multi_provider_gateway(self):
        """Demonstrate multi-provider gateway with AWS-documented guidance."""

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
                self.logger.info("Multi-provider gateway demonstration completed")

    def _run_demonstration(self):
        """Internal demonstration logic with AWS documentation-based explanations."""

        # Pattern Introduction
        self.console("=" * 60)
        self.console("Multi-Provider LLM Gateway Pattern")
        self.console("=" * 60)
        
        # What is this (AWS Official)
        self.console("📋 What is this:")
        self.console("This AWS Solutions Guidance demonstrates how to streamline access to numerous")
        self.console("large language models (LLMs) through a unified, industry-standard API gateway")
        self.console("based on OpenAI API standards. By deploying this Guidance, you can simplify")
        self.console("integration while gaining access to tools that track LLM usage, manage costs,")
        self.console("and implement crucial governance features. This allows easy switching between")
        self.console("models, efficient management of multiple LLM services within applications,")
        self.console("and robust control over security and expenses.")
        self.console("")

        # When to use it
        self.console("🎯 When to use it:")
        self.console("• Need provider diversification beyond AWS-native solutions")
        self.console("• Require unified API across Amazon Bedrock + external providers")
        self.console("• Enterprise-grade usage tracking and budget management")
        self.console("• Provider-level throttling protection and failover")
        self.console("• Multi-provider LLM integration with cost management")
        self.console("• Simplified development with consistent input/output format")
        self.console("")

        # More information
        self.console("📚 For more information:")
        self.console("Official AWS Solutions Guidance:")
        self.console("https://aws-solutions-library-samples.github.io/ai-ml/guidance-for-multi-provider-generative-ai-gateway-on-aws.html")
        self.console("")
        self.console("GitHub Repository:")
        self.console("https://github.com/aws-solutions-library-samples/guidance-for-multi-provider-generative-ai-gateway-on-aws")
        self.console("")

        # Implementation steps
        self.console("🚀 Implementation Steps:")
        self.console("1. Clone the GitHub repository")
        self.console("   git clone https://github.com/aws-solutions-library-samples/guidance-for-multi-provider-generative-ai-gateway-on-aws.git")
        self.console("")
        self.console("2. Configure deployment scenario in .env file")
        self.console("   • Public with CloudFront (Recommended)")
        self.console("   • Custom Domain with CloudFront")
        self.console("   • Direct ALB Access")
        self.console("   • Private VPC Only")
        self.console("")
        self.console("3. Set up prerequisites (if using custom domain)")
        self.console("   • Route53 hosted zone")
        self.console("   • ACM certificate")
        self.console("")
        self.console("4. Deploy using Terraform or CDK")
        self.console("   • Deployment time: 35-40 minutes")
        self.console("   • Supports Amazon ECS or Amazon EKS")
        self.console("")
        self.console("5. Configure LLM providers via Admin UI")
        self.console("   • Amazon Bedrock integration (built-in)")
        self.console("   • External providers (OpenAI, Anthropic, etc.)")
        self.console("")
        self.console("6. Set up governance and monitoring")
        self.console("   • Budgets and rate limits")
        self.console("   • Access controls and API keys")
        self.console("   • Usage tracking and cost allocation")

        # Log the demonstration
        self.log("=== Multi-Provider LLM Gateway Pattern Demonstration ===")
        self.log("AWS Solutions Guidance for unified API across multiple AI providers")
        self.log("Key benefits: Streamlined access, usage tracking, cost management, governance")
        self.log("Implementation: Official AWS templates with 35-40 minute deployment")
        self.log("=== Demonstration Summary ===")
        self.log("Multi-provider gateway demonstration completed")
        
        self.console("")
        self.console(f"📋 Detailed log: {self.log_file.name}")
        self.save_log()

def main():
    """Main execution function with error handling."""
    try:
        gateway = MultiProviderGateway()
        gateway.demonstrate_multi_provider_gateway()
    except KeyboardInterrupt:
        print("\\nMulti-provider gateway demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Multi-provider gateway demonstration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()