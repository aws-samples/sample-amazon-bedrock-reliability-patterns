#!/usr/bin/env python3
"""
Batch Processing Pattern

Demonstrates cost-effective bulk processing for large datasets using Amazon Bedrock
batch inference. Process multiple prompts asynchronously via S3 for significant
cost savings on high-volume workloads.

Use batch processing for large datasets, data pipelines, and cost-sensitive workloads
where real-time response is not required.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html
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

class BatchProcessing:
    def __init__(self, region: str = None):
        """Initialize batch processing demonstration."""
        self.region = region or get_secure_region()
        self.bedrock = boto3.client('bedrock', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"batch_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

    def get_batch_jobs(self) -> List[Dict[str, Any]]:
        """Get existing batch inference jobs using AWS API."""
        self.log("Fetching existing batch inference jobs...")
        
        try:
            response = self.bedrock.list_model_invocation_jobs()
            jobs = response.get('invocationJobSummaries', [])
            
            self.log(f"Found {len(jobs)} batch inference jobs")
            for job in jobs:
                self.log(f"Job: {job['jobName']} - Status: {job['status']} - ARN: {job['jobArn']}")
            
            return jobs
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get batch jobs: {error_msg}")
            return []

    def get_job_details(self, job_arn: str) -> Dict[str, Any]:
        """Get detailed batch job information."""
        try:
            response = self.bedrock.get_model_invocation_job(jobIdentifier=job_arn)
            return response
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to get job details: {error_msg}")
            return {}

    def monitor_job_progress(self, job_arn: str, job_name: str) -> Dict[str, Any]:
        """Monitor batch job progress with status updates."""
        self.console(f"   → Monitoring job: {job_name}")
        
        try:
            details = self.get_job_details(job_arn)
            if details:
                status = details.get('status', 'Unknown')
                progress = details.get('jobStatistics', {})
                
                self.console(f"   → Status: {status}")
                if progress:
                    submitted = progress.get('inputTokenCount', 0)
                    completed = progress.get('outputTokenCount', 0)
                    self.console(f"   → Progress: Input tokens: {submitted}, Output tokens: {completed}")
                
                return {
                    'status': status,
                    'progress': progress,
                    'details': details
                }
            
            return {'status': 'Unknown', 'progress': {}, 'details': {}}
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.log(f"ERROR: Failed to monitor job: {error_msg}")
            return {'status': 'Error', 'error': error_msg}

        # Batch configuration
        self.batch_config = {
            'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
            'input_file': 'data/sample_batch_input.jsonl',
            'job_name': f'demo-batch-{int(time.time())}'
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
                f.write("AMAZON BEDROCK BATCH PROCESSING PATTERN - DETAILED LOG\n")
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

    def check_batch_input_file(self) -> int:
        """Check if batch input file exists and return record count."""
        project_root = Path(__file__).parent.parent.parent
        input_file_path = project_root / self.batch_config['input_file']

        self.log(f"Checking batch input file: {input_file_path}")

        if input_file_path.exists():
            # Count records
            with open(input_file_path, "r", encoding="utf-8") as f:
                records = f.readlines()

            record_count = len(records)
            self.log(f"Batch input file found with {record_count} records")
            return record_count
        else:
            self.log(f"ERROR: Batch input file not found: {input_file_path}")
            return 0

    def list_batch_jobs(self) -> List[Dict[str, Any]]:
        """List existing batch inference jobs."""
        self.log("Listing existing batch inference jobs")

        try:
            response = self.bedrock.list_model_invocation_jobs()
            jobs = response.get('invocationJobSummaries', [])

            self.log(f"Found {len(jobs)} batch inference jobs")
            for job in jobs:
                self.log(f"Batch job: {job}")

            return jobs

        except Exception as e:
            self.log(f"ERROR: {sanitize_error_message(str(e))}")
            return []

    def create_s3_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Create S3 bucket for batch processing."""
        try:
            if self.region == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            return {'success': True, 'bucket': bucket_name}
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            return {'success': False, 'error': error_msg}

    def upload_file_to_s3(self, local_file: str, bucket: str, s3_key: str) -> Dict[str, Any]:
        """Upload file to S3."""
        try:
            self.s3.upload_file(local_file, bucket, s3_key)
            return {'success': True, 's3_uri': f's3://{bucket}/{s3_key}'}
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            return {'success': False, 'error': error_msg}

    def create_batch_job(self, input_s3_uri: str, output_s3_uri: str, model_id: str) -> Dict[str, Any]:
        """Create a batch inference job."""
        job_name = f"batch-demo-{int(time.time())}"
        
        try:
            response = self.bedrock.create_model_invocation_job(
                jobName=job_name,
                roleArn=f"arn:aws:iam::{self._get_account_id()}:role/BedrockBatchRole",
                modelId=model_id,
                inputDataConfig={
                    's3InputDataConfig': {
                        's3Uri': input_s3_uri
                    }
                },
                outputDataConfig={
                    's3OutputDataConfig': {
                        's3Uri': output_s3_uri
                    }
                }
            )
            
            return {
                'success': True,
                'job_arn': response['jobArn'],
                'job_name': job_name
            }
            
        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            return {
                'success': False,
                'error': error_msg
            }

    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts = boto3.client('sts', region_name=self.region)
            return sts.get_caller_identity()['Account']
        except:
            return "123456789012"  # Fallback

    def demonstrate_batch_processing(self):
        """Demonstrate complete batch processing workflow with S3 setup."""

        # Pattern Introduction
        self.console("=" * 60)
        self.console("Batch Processing Pattern")
        self.console("=" * 60)
        self.console("Purpose: Process multiple prompts asynchronously for cost savings")
        self.console("How it works: S3 upload → Batch job → Monitor → Download results")
        self.console("Benefits: Up to 50% cost savings, handles large datasets efficiently")
        self.console("")

        self.log("=== Batch Processing Pattern Demonstration ===")
        self.log("Complete workflow: S3 setup → Upload → Job creation → Monitoring")

        # Phase 1: Check Sample Data
        self.console("🔍 Phase 1: Sample Data Preparation...")
        
        sample_file = Path(__file__).parent.parent.parent / "data" / "sample_batch_input.jsonl"
        self.console(f"   → Sample data file: {sample_file.name}")
        
        if not sample_file.exists():
            self.console("❌ Sample JSONL file not found")
            self.console(f"   Create {sample_file} with batch prompts")
            return

        # Read and show sample data
        try:
            with open(sample_file, 'r') as f:
                sample_data = [json.loads(line) for line in f if line.strip()]
            
            self.console(f"   ✅ Sample file contains {len(sample_data)} prompts")
            if sample_data and len(sample_data) >= 2:
                # Show first two prompts
                prompt1 = sample_data[0].get('messages', [{}])[0].get('content', '')
                prompt2 = sample_data[1].get('messages', [{}])[0].get('content', '')
                if prompt1:
                    self.console(f"   → Prompt 1: {prompt1[:50]}...")
                if prompt2:
                    self.console(f"   → Prompt 2: {prompt2[:50]}...")
            elif sample_data:
                # Show just one prompt
                prompt1 = sample_data[0].get('messages', [{}])[0].get('content', '')
                if prompt1:
                    self.console(f"   → Sample prompt: {prompt1[:50]}...")
            
        except Exception as e:
            self.console(f"❌ Error reading sample file: {sanitize_error_message(str(e))}")
            return

        # Phase 2: Create S3 Bucket and Upload
        self.console("")
        self.console("📦 Phase 2: S3 Bucket Setup...")
        
        bucket_name = f"bedrock-batch-demo-{int(time.time())}"
        self.console(f"   → Creating S3 bucket: {bucket_name}")
        
        bucket_result = self.create_s3_bucket(bucket_name)
        
        if bucket_result['success']:
            self.console("   ✅ S3 bucket created successfully")
            
            # Upload sample file
            self.console("   → Uploading sample file to S3...")
            upload_result = self.upload_file_to_s3(
                str(sample_file), 
                bucket_name, 
                "input/sample_batch_input.jsonl"
            )
            
            if upload_result['success']:
                input_s3_uri = upload_result['s3_uri']
                output_s3_uri = f"s3://{bucket_name}/output/"
                
                self.console(f"   ✅ File uploaded: {input_s3_uri}")
                self.console(f"   → Output location: {output_s3_uri}")
                
                # Phase 3: Create Batch Job
                self.console("")
                self.console("🚀 Phase 3: Creating Batch Job...")
                
                # Use latest Nova model that supports batch inference
                model_id = "amazon.nova-lite-v1:0"
                self.console(f"   → Model: {model_id} (latest Nova model with batch support)")
                self.console("   → Creating batch inference job...")
                
                job_result = self.create_batch_job(input_s3_uri, output_s3_uri, model_id)
                
                if job_result['success']:
                    job_arn = job_result['job_arn']
                    job_name = job_result['job_name']
                    
                    self.console(f"   ✅ Batch job created successfully")
                    self.console(f"   → Job Name: {job_name}")
                    
                    # Phase 4: Monitoring and Results
                    self.console("")
                    self.console("📊 Phase 4: Monitoring & Results...")
                    self.console("   → Job submitted and will process asynchronously")
                    self.console("")
                    self.console("   🔄 Batch Job Stages:")
                    self.console("     1. Submitted → Job accepted and queued")
                    self.console("     2. InProgress → Processing prompts from input file")
                    self.console("     3. Completed → Results saved to output S3 location")
                    self.console("     4. Failed → Check job details for error information")
                    self.console("")
                    self.console("   → Monitor progress with:")
                    self.console(f"     aws bedrock get-model-invocation-job --job-identifier {job_arn}")
                    self.console("")
                    self.console("   → When status shows 'Completed', download results with:")
                    self.console(f"     aws s3 cp {output_s3_uri} ./batch-results/ --recursive")
                    self.console("")
                    self.console("   → Review output JSONL files for processed responses")
                    
                else:
                    self.console(f"   ❌ Job creation failed: {job_result['error']}")
                    self.console("   → Ensure IAM role 'BedrockBatchRole' exists with proper permissions")
                
            else:
                self.console(f"   ❌ Upload failed: {upload_result['error']}")
        else:
            self.console(f"   ❌ Bucket creation failed: {bucket_result['error']}")
            bucket_name = None

        # Cleanup Instructions
        self.console("")
        self.console("🧹 Cleanup Instructions (to avoid ongoing costs):")
        if bucket_name:
            self.console(f"   → Delete S3 objects: aws s3 rm s3://{bucket_name} --recursive")
            self.console(f"   → Delete S3 bucket: aws s3 rb s3://{bucket_name}")
        self.console("   → Stop batch job if needed: aws bedrock stop-model-invocation-job --job-identifier <job-arn>")
        self.console("")
        self.console("⚠️  Important: Run cleanup commands to avoid S3 storage charges")

        self.console("")
        self.console("💡 Batch Processing Benefits:")
        self.console("   • Cost savings: Up to 50% less than real-time inference")
        self.console("   • Scalability: Process thousands of prompts efficiently")
        self.console("   • Asynchronous: Submit job and retrieve results later")

        self.log("Batch processing demonstration completed")
        self.console(f"\n📋 Detailed log: {self.log_file.name}")
        self.save_log()

def main():
    """Demonstrate Amazon Bedrock batch processing pattern."""
    client = BatchProcessing()
    client.demonstrate_batch_processing()

if __name__ == "__main__":
    main()