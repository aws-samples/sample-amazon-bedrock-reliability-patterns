#!/usr/bin/env python3
"""
Amazon Bedrock Reliability Patterns - Pre-flight Check

Validates environment, AWS access, and Bedrock connectivity.
"""

import os
import sys
import boto3
import re
from pathlib import Path
from datetime import datetime

def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to prevent information disclosure."""
    sanitized = str(error_msg).replace(str(Path.home()), "~")
    return sanitized[:200] + "..." if len(sanitized) > 200 else sanitized

def get_secure_region() -> str:
    """Get AWS region from environment with validation."""
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    if not re.match(r'^[a-z0-9-]+$', region):
        raise ValueError("Invalid region format")
    return region

class BedrockPrecheck:
    def __init__(self):
        self.project_root = Path(__file__).parent.resolve()
        self.checks_passed = 0
        self.total_checks = 0
        self.region = get_secure_region()
        
    def print_header(self):
        print("=" * 60)
        print("Amazon Bedrock Reliability Patterns - Health Check")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def check(self, description, test_func):
        """Run a check and track results."""
        self.total_checks += 1
        print(f"Checking {description}...", end=" ")
        
        try:
            result = test_func()
            if result:
                print("OK")
                self.checks_passed += 1
                return True
            else:
                print("FAILED")
                return False
        except Exception as e:
            print(f"FAILED ({sanitize_error_message(str(e))[:50]}...)")
            return False
    
    def check_python_version(self):
        return sys.version_info >= (3, 8)
    
    def check_virtual_environment(self):
        return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    def check_dependencies(self):
        try:
            import boto3, botocore, requests, PyPDF2
            return True
        except ImportError:
            return False
    
    def check_aws_credentials(self):
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except:
            return False
    
    def check_bedrock_service(self):
        try:
            client = boto3.client('bedrock', region_name=self.region)
            client.list_foundation_models()
            return True
        except:
            return False
    
    def check_bedrock_runtime(self):
        try:
            client = boto3.client('bedrock-runtime', region_name=self.region)
            return True
        except:
            return False
    
    def check_cross_region_profiles(self):
        try:
            client = boto3.client('bedrock', region_name=self.region)
            response = client.list_inference_profiles()
            return len(response.get('inferenceProfileSummaries', [])) > 0
        except:
            return False
    
    def check_directories(self):
        required_dirs = ['patterns', 'patterns/aws_native', 'patterns/custom', 'logs', 'data']
        return all((self.project_root / d).exists() for d in required_dirs)
    
    def check_sample_data(self):
        sample_file = self.project_root / "data" / "sample_batch_input.jsonl"
        return sample_file.exists() and sample_file.stat().st_size > 0
    
    def run_comprehensive_check(self):
        self.print_header()
        
        # Core environment checks
        print("Python Environment:")
        self.check("Python 3.8+", self.check_python_version)
        self.check("Virtual environment", self.check_virtual_environment)
        self.check("Required dependencies", self.check_dependencies)
        
        print("\nAWS Configuration:")
        self.check("AWS credentials", self.check_aws_credentials)
        self.check("Bedrock service access", self.check_bedrock_service)
        self.check("Bedrock runtime access", self.check_bedrock_runtime)
        self.check("Cross-region profiles", self.check_cross_region_profiles)
        
        print("\nProject Structure:")
        self.check("Required directories", self.check_directories)
        self.check("Sample data files", self.check_sample_data)
        
        # Summary
        print("\n" + "=" * 60)
        print("Health Check Summary")
        print("=" * 60)
        
        success_rate = (self.checks_passed / self.total_checks) * 100
        print(f"Checks passed: {self.checks_passed}/{self.total_checks} ({success_rate:.0f}%)")
        
        if self.checks_passed == self.total_checks:
            print("All systems go! You're ready to run all patterns.")
        elif self.checks_passed >= self.total_checks * 0.8:
            print("Most checks passed. You can run most patterns.")
            print("Check failed items above for full functionality.")
        else:
            print("Several issues detected. Run setup.py to fix.")
        
        print(f"\nQuick Start Command:")
        print(f"python patterns/aws_native/01_cross_region_inference.py")
        
        return self.checks_passed == self.total_checks

if __name__ == "__main__":
    precheck = BedrockPrecheck()
    success = precheck.run_comprehensive_check()
    sys.exit(0 if success else 1)
