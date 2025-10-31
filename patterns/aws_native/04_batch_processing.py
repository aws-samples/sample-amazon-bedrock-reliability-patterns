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

    def demonstrate_batch_processing(self):
        """Demonstrate batch processing with clean console output."""

        # Initialize pattern demonstration
        self.console("Batch Processing Pattern")
        self.console("Asynchronous batch inference processing")

        # Detailed logging
        self.log("Starting BATCH PROCESSING demonstration")
        self.log("Initializing batch processing demonstration")
        self.log(f"Source region: {self.region}")
        self.log(f"Batch configuration: {json.dumps(self.batch_config, indent=2)}")

        # Check input file
        self.console("Checking batch input file...")
        self.log("Validating batch input file")

        record_count = self.check_batch_input_file()
        if record_count == 0:
            self.console("Batch input file not found")
            self.console(f"\nResults: Input validation failed")
            self.save_log()
            return

        self.console(f"Sample batch input file ready ({record_count} records)")

        # Check existing jobs
        self.console("Checking batch job history...")
        self.log("Checking existing batch inference jobs")

        jobs = self.list_batch_jobs()

        if jobs:
            recent_jobs = [j for j in jobs if j.get('submitTime', datetime.min).date() == datetime.now().date()]
            self.console(f"Found {len(jobs)} total jobs, {len(recent_jobs)} today")

            # Show recent job status
            if recent_jobs:
                latest_job = max(recent_jobs, key=lambda x: x.get('submitTime', datetime.min))
                status = latest_job.get('status', 'Unknown')
                self.console(f"Latest job status: {status}")
                self.log(f"Latest job details: {latest_job}")
        else:
            self.console("No previous batch jobs found")

        # Batch processing benefits
        self.console("\nBatch Processing Benefits:")
        self.console("• Up to 50% cost savings vs real-time inference")
        self.console("• Asynchronous processing for large datasets")
        self.console("• S3 integration for input/output management")

        # Usage guidance
        self.console("\nTo submit a batch job:")
        self.console("1. Upload JSONL file to S3")
        self.console("2. Create batch inference job via AWS CLI/SDK")
        self.console("3. Monitor job progress and retrieve results")

        # Results summary
        if jobs:
            self.console(f"\nResults: Batch infrastructure verified")
        else:
            self.console(f"\nResults: Ready for first batch job")

        # Save detailed log
        self.log("Completed BATCH PROCESSING demonstration")
        self.save_log()
        self.console(f"\nDetailed log: {self.log_file.name}")

def main():
    """Demonstrate Amazon Bedrock batch processing pattern."""
    client = BatchProcessing()
    client.demonstrate_batch_processing()

if __name__ == "__main__":
    main()