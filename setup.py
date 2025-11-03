#!/usr/bin/env python3
"""
Amazon Bedrock Reliability Patterns - Setup Script

White-glove setup experience that gets users running immediately.
Handles virtual environment, dependencies, AWS configuration, and validation.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Security: Input validation and sanitization
def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to prevent information disclosure."""
    # Remove sensitive paths and details
    sanitized = str(error_msg).replace(str(Path.home()), "~")
    # Limit length to prevent log flooding
    return sanitized[:200] + "..." if len(sanitized) > 200 else sanitized

class BedrockSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.resolve()
        self.venv_path = self.project_root / "venv"
        self.requirements_file = self.project_root / "requirements.txt"
        # Security: Get region from environment or default
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        # Validate region format
        if not self.region.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Invalid AWS region format")

    def print_header(self):
        print("=" * 60)
        print(" Amazon Bedrock Reliability Patterns Setup")
        print("=" * 60)
        print("Setting up your environment for immediate use...\n")

    def check_python_version(self):
        print("Checking Python version...")
        if sys.version_info < (3, 8):
            print("Python 3.8+ required. Current:", sys.version)
            sys.exit(1)
        print(f"Python {sys.version.split()[0]} OK")

    def create_virtual_environment(self):
        if self.venv_path.exists():
            print("Virtual environment already exists")
            return

        print("Creating virtual environment...")
        # Secure path validation
        resolved_venv = self.venv_path.resolve()
        resolved_root = self.project_root.resolve()
        if not str(resolved_venv).startswith(str(resolved_root)):
            raise ValueError("Virtual environment path must be in project directory")

        # Secure subprocess call with validated paths
        cmd = [sys.executable, "-m", "venv", str(resolved_venv)]
        # Security Note: May trigger scanner warning for non-static subprocess args,
        # but safe due to: 1) list format prevents shell injection, 2) paths validated above
        subprocess.run(cmd, check=True, cwd=str(resolved_root))
        print("Virtual environment created")

    def get_pip_path(self):
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "pip"
        return self.venv_path / "bin" / "pip"

    def install_dependencies(self):
        print("Installing dependencies...")
        pip_path = self.get_pip_path()

        # Secure path validation
        resolved_pip = pip_path.resolve()
        resolved_venv = self.venv_path.resolve()
        if not str(resolved_pip).startswith(str(resolved_venv)):
            raise ValueError("Pip path must be in virtual environment directory")

        resolved_req = self.requirements_file.resolve()
        resolved_root = self.project_root.resolve()
        if not str(resolved_req).startswith(str(resolved_root)):
            raise ValueError("Requirements file must be in project directory")

        # Secure subprocess calls
        # Security Note: May trigger scanner warnings for non-static subprocess args,
        # but safe due to: 1) list format prevents shell injection, 2) paths validated above
        subprocess.run([str(resolved_pip), "install", "--upgrade", "pip"], 
                      check=True, capture_output=True, cwd=str(resolved_root))
        subprocess.run([str(resolved_pip), "install", "-r", str(resolved_req)], 
                      check=True, capture_output=True, cwd=str(resolved_root))
        print("Dependencies installed")

    def check_aws_credentials(self):
        print("Checking AWS credentials...")
        try:
            import boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                print("AWS credentials not configured")
                self.show_aws_setup_help()
                return False
            # Security: Validate credentials without exposing them
            if not credentials.access_key or not credentials.secret_key:
                print("Invalid AWS credentials")
                return False
            print("AWS credentials found")
            return True
        except Exception as e:
            print(f"AWS setup issue: {sanitize_error_message(str(e))}")
            self.show_aws_setup_help()
            return False

    def show_aws_setup_help(self):
        print("\n AWS Setup Required:")
        print("   Option 1: AWS CLI")
        print("     aws configure")
        print("   Option 2: Environment variables")
        print("     export AWS_ACCESS_KEY_ID=your_key")
        print("     export AWS_SECRET_ACCESS_KEY=your_secret")
        print("     export AWS_DEFAULT_REGION=us-east-1")
        print("   Option 3: IAM roles (for EC2/Lambda)")

    def test_bedrock_access(self):
        print("Testing Bedrock access...")
        try:
            import boto3
            client = boto3.client('bedrock', region_name=self.region)
            client.list_foundation_models()
            print("Bedrock access verified")
            return True
        except Exception as e:
            print(f"Bedrock access issue: {sanitize_error_message(str(e))}")
            print("Note: Some regions may not have Bedrock enabled")
            return False

    def create_directories(self):
        print("Creating required directories...")
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)  # Secure permissions
        print("Directories created")

    def show_activation_instructions(self):
        print("\n" + "=" * 60)
        print(" Setup Complete!")
        print("=" * 60)

        if platform.system() == "Windows":
            activate_cmd = f"venv\\Scripts\\activate"
        else:
            activate_cmd = f"source venv/bin/activate"

        print(f"\n Next Steps:")
        print(f"1. Activate virtual environment:")
        print(f"   {activate_cmd}")
        print(f"\n2. Run patterns:")
        print(f"   python patterns/aws_native/01_cross_region_inference.py")
        print(f"\n3. Or run precheck anytime:")
        print(f"   python precheck.py")
        print(f"\n You're ready to explore Bedrock scaling patterns!")

    def run_setup(self):
        try:
            self.print_header()
            self.check_python_version()
            self.create_virtual_environment()
            self.install_dependencies()
            self.create_directories()

            # Import after installation
            sys.path.insert(0, str(self.venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"))

            aws_ok = self.check_aws_credentials()
            bedrock_ok = self.test_bedrock_access() if aws_ok else False

            self.show_activation_instructions()

            if not aws_ok or not bedrock_ok:
                print("\n Some checks failed - see messages above")
                print(" You can still explore the code and run precheck.py later")

        except subprocess.CalledProcessError as e:
            print(f" Setup failed: {sanitize_error_message(str(e))}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n Setup cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f" Unexpected error: {sanitize_error_message(str(e))}")
            sys.exit(1)

if __name__ == "__main__":
    setup = BedrockSetup()
    setup.run_setup()