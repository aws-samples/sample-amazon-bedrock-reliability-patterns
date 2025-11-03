#!/usr/bin/env python3
"""
Prompt Caching Pattern

Demonstrates reduced latency and token costs using Amazon Bedrock prompt caching
with cache checkpoints. Cache prompt prefixes with 5-minute TTL for repeated contexts
like document-based chatbots and Q&A applications.

Use prompt caching for applications with repeated contexts, document analysis,
and scenarios where the same context is used multiple times.

For more information:
https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
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

class PromptCaching:
    def __init__(self, region: str = None):
        """Initialize prompt caching demonstration."""
        self.region = region or get_secure_region()
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)

        self.resource_manager = ResourceManager()
        # Setup logging with absolute path
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(mode=0o750, exist_ok=True)
        self.log_file = logs_dir / f"prompt_caching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

        # Supported models with caching (from AWS docs - current as of Nov 2024)
        self.supported_models = {
            'anthropic.claude-3-5-haiku-20241022-v1:0': {'min_tokens': 2048, 'name': 'Claude 3.5 Haiku'},
            'anthropic.claude-3-5-sonnet-20241022-v2:0': {'min_tokens': 1024, 'name': 'Claude 3.5 Sonnet v2'},
            'amazon.nova-micro-v1:0': {'min_tokens': 1024, 'name': 'Amazon Nova Micro'},
            'amazon.nova-lite-v1:0': {'min_tokens': 1024, 'name': 'Amazon Nova Lite'},
            'amazon.nova-pro-v1:0': {'min_tokens': 1024, 'name': 'Amazon Nova Pro'}
        }

    def load_document_content(self) -> str:
        """Load AWS CAF for AI content for caching demonstration."""
        # Try text file first (more reliable)
        txt_file = Path(__file__).parent.parent.parent / "data" / "aws-caf-for-ai.txt"
        pdf_file = Path(__file__).parent.parent.parent / "data" / "aws-caf-for-ai.pdf"
        
        # Prefer text file for reliable extraction
        if txt_file.exists():
            try:
                with open(txt_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.log(f"Text file loaded: {len(content)} chars, {len(content.split())} words")
                    return content
            except Exception as e:
                self.log(f"Error loading text file: {sanitize_error_message(str(e))}")
        
        # Fallback to PDF if text file not available
        if pdf_file.exists():
            try:
                import PyPDF2
                with open(pdf_file, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    content = ""
                    
                    self.log(f"PDF has {len(pdf_reader.pages)} pages")
                    
                    # Read ALL pages
                    for page_num in range(len(pdf_reader.pages)):
                        try:
                            page_text = pdf_reader.pages[page_num].extract_text()
                            if page_text.strip():
                                content += page_text + "\n\n"
                                self.log(f"Page {page_num + 1}: {len(page_text)} chars, {len(page_text.split())} words")
                        except Exception as e:
                            self.log(f"Error reading page {page_num + 1}: {sanitize_error_message(str(e))}")
                            continue
                    
                    self.log(f"Total PDF extracted: {len(content)} chars, {len(content.split())} words")
                    return content if content.strip() else None
                    
            except ImportError:
                self.log("PyPDF2 not available, using fallback content")
            except Exception as e:
                self.log(f"Error loading PDF: {sanitize_error_message(str(e))}")
        
        # Substantial fallback content that meets token requirements
        return """AWS Cloud Adoption Framework for AI (AWS CAF for AI) provides comprehensive guidance for organizations adopting artificial intelligence and machine learning capabilities in the cloud environment.

Key principles include:
1. Start with business outcomes and work backwards to identify AI use cases that deliver measurable value to your organization
2. Build a data-driven culture and capabilities across your entire organization to support AI initiatives
3. Implement responsible AI practices including governance, ethics, bias mitigation, and transparency requirements
4. Establish comprehensive governance and risk management frameworks to ensure AI systems are reliable and trustworthy
5. Invest in talent development and change management to support successful AI adoption across teams
6. Create scalable infrastructure and platform capabilities that can support AI workloads at enterprise scale

The framework covers six perspectives: Business, People, Governance, Platform, Security, and Operations. Each perspective provides specific guidance for AI adoption at scale.

Business Perspective focuses on ensuring AI investments align with business strategy and deliver measurable outcomes. This includes identifying high-value use cases, establishing success metrics, building business cases for AI initiatives, and creating governance structures for AI investments.

People Perspective addresses the human elements of AI adoption including skills development, organizational change management, cultural transformation needed to become an AI-driven organization, and building teams with the right mix of technical and business skills.

Governance Perspective establishes frameworks for responsible AI including ethics guidelines, bias detection and mitigation strategies, model governance processes, regulatory compliance requirements, and risk management frameworks.

Platform Perspective covers the technical infrastructure needed to support AI workloads including data platforms, machine learning operations, model deployment pipelines, integration with existing systems, and cloud infrastructure optimization.

Security Perspective addresses unique security considerations for AI systems including data protection strategies, model security requirements, threat detection specific to AI workloads, and privacy preservation techniques.

Operations Perspective focuses on the operational aspects of running AI systems in production including monitoring and observability, maintenance procedures, performance optimization strategies, incident response plans, and continuous improvement processes.

The framework emphasizes the importance of starting with clear business objectives and working backwards to identify the most valuable AI use cases. Organizations should focus on building foundational capabilities in data management, infrastructure, and governance before pursuing advanced AI applications.

Successful AI adoption requires a holistic approach that addresses technical, organizational, and cultural challenges. The framework provides practical guidance for navigating these challenges and building sustainable AI capabilities that can evolve with changing business needs and technological advances.

Organizations implementing the AWS CAF for AI should begin by assessing their current state across all six perspectives, identifying gaps and opportunities for improvement. This assessment should inform the development of a comprehensive AI adoption roadmap that prioritizes initiatives based on business value and organizational readiness.

The Business perspective emphasizes the critical importance of executive sponsorship and clear governance structures for AI initiatives. Organizations must establish clear roles and responsibilities for AI decision-making, create processes for evaluating and prioritizing AI use cases, and develop metrics for measuring the success of AI investments.

From a People perspective, organizations must invest heavily in developing AI literacy across all levels of the organization. This includes technical training for data scientists and engineers, business training for executives and managers, and change management support for all employees affected by AI implementations.

The Governance perspective requires organizations to establish comprehensive frameworks for responsible AI development and deployment. This includes creating ethics committees, developing bias testing procedures, establishing model validation processes, and ensuring compliance with relevant regulations and industry standards.

Platform capabilities must be designed to support the full AI lifecycle from data ingestion and preparation through model training, validation, deployment, and monitoring. Organizations should leverage cloud-native services where possible to reduce operational overhead and accelerate time to value.

Security considerations for AI systems extend beyond traditional cybersecurity to include unique challenges such as adversarial attacks on models, data poisoning, and privacy-preserving techniques for sensitive data. Organizations must develop comprehensive security strategies that address these AI-specific risks.

Operations teams must develop new capabilities for monitoring AI systems in production, including model performance monitoring, drift detection, and automated retraining processes. This requires close collaboration between data science teams and traditional IT operations teams."""

    def invoke_with_cache_checkpoint(self, document_content: str, question: str, model_id: str) -> Dict[str, Any]:
        """Invoke model with real AWS Bedrock cache checkpoint."""
        
        # Security: Validate inputs
        prompt = sanitize_prompt(question)
        if not validate_model_id(model_id):
            raise ValueError("Invalid model ID")

        self.logger.info(f"Cache checkpoint request for model: {model_id}")
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()

        def _invoke():
            with timeout_context(self.config['timeout']):
                # Use real AWS Bedrock cache checkpoint syntax
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": document_content
                            },
                            {
                                "cachePoint": {
                                    "type": "default"
                                }
                            },
                            {
                                "text": f"\n\nBased on the document above, {prompt}"
                            }
                        ]
                    }
                ]

                response = self.bedrock_runtime.converse(
                    modelId=model_id,
                    messages=messages,
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

            # Log cache-related metrics if available
            cache_read_tokens = usage.get('cacheReadInputTokens', 0)
            cache_write_tokens = usage.get('cacheWriteInputTokens', 0)
            
            self.log(f"Cache checkpoint request completed")
            self.log(f"Model: {model_id}")
            self.log(f"Input tokens: {usage.get('inputTokens', 0)}")
            self.log(f"Output tokens: {usage.get('outputTokens', 0)}")
            self.log(f"Cache read tokens: {cache_read_tokens}")
            self.log(f"Cache write tokens: {cache_write_tokens}")
            self.log(f"Response time: {response_time:.3f}s")

            return {
                'success': True,
                'content': content,
                'response_time': response_time,
                'usage': usage,
                'cache_read_tokens': cache_read_tokens,
                'cache_write_tokens': cache_write_tokens
            }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.logger.error(f"Cache checkpoint invocation failed: {error_msg}")

            return {
                'success': False,
                'error': error_msg,
                'response_time': 0
            }

    def invoke_without_cache(self, document_content: str, question: str, model_id: str) -> Dict[str, Any]:
        """Invoke model without cache checkpoint for comparison."""
        
        # Security: Validate inputs
        prompt = sanitize_prompt(question)
        if not validate_model_id(model_id):
            raise ValueError("Invalid model ID")

        self.logger.info(f"Non-cached request for model: {model_id}")
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()

        def _invoke():
            with timeout_context(self.config['timeout']):
                # Regular message without cache checkpoint
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": f"{document_content}\n\nBased on the document above, {prompt}"
                            }
                        ]
                    }
                ]

                response = self.bedrock_runtime.converse(
                    modelId=model_id,
                    messages=messages,
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

            self.log(f"Non-cached request completed")
            self.log(f"Model: {model_id}")
            self.log(f"Input tokens: {usage.get('inputTokens', 0)}")
            self.log(f"Output tokens: {usage.get('outputTokens', 0)}")
            self.log(f"Response time: {response_time:.3f}s")

            return {
                'success': True,
                'content': content,
                'response_time': response_time,
                'usage': usage
            }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            self.logger.error(f"Non-cached invocation failed: {error_msg}")

            return {
                'success': False,
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
            # Security: Create file with restricted permissions
            self.log_file.touch(mode=0o640)
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=== PROMPT CACHING LOG ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Region: {self.region}\n")
                f.write("=" * 50 + "\n\n")
                # Security: Sanitize log entries
                for entry in self.log_entries:
                    sanitized_entry = entry.replace(str(Path.home()), "~")
                    f.write(sanitized_entry + "\n")
        except Exception as e:
            self.console(f"Warning: Could not save log file: {sanitize_error_message(str(e))}")

    def demonstrate_prompt_caching(self):
        """Demonstrate prompt caching with enhanced error handling."""

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
                self.logger.info("Prompt caching demonstration completed")

    def _run_demonstration(self):
        """Internal demonstration logic with AWS documentation-based explanations."""

        # Pattern Introduction (AWS Official)
        self.console("=" * 60)
        self.console("Prompt Caching Pattern")
        self.console("=" * 60)
        self.console("Purpose: Reduce inference latency and input token costs (AWS Official)")
        self.console("How it works: Cache prompt prefixes with cache checkpoints and 5-minute TTL (AWS Official)")
        self.console("Benefits (AWS Official):")
        self.console("  • Reduced rate for tokens read from cache")
        self.console("  • Lower response latencies for repeated contexts")
        self.console("  • Ideal for document-based Q&A applications")
        self.console("")

        # When to Use (AWS Official)
        self.console("📍 When to Use Prompt Caching:")
        self.console("   • Applications with repeated document contexts")
        self.console("   • Document-based chatbots and Q&A systems")
        self.console("   • Long prompts with static prefixes (1024+ tokens)")
        self.console("   • Cost-sensitive workloads with repeated contexts")
        self.console("")

        # Supported Models (AWS Official)
        self.console("🎯 Supported Models (AWS Official):")
        for model_id, info in self.supported_models.items():
            self.console(f"   • {info['name']}: {model_id} (min: {info['min_tokens']} tokens)")
        self.console("")

        # Log the same information
        self.log("=== Prompt Caching Pattern Demonstration ===")
        self.log("AWS Official Purpose: Reduce inference latency and input token costs")
        self.log("Mechanism: Cache checkpoints with 5-minute TTL")
        self.log("Key Benefits: Reduced cache token rates, lower latency, document Q&A optimization")

        self.logger.info("Starting prompt caching demonstration")

        # Phase 1: Load Document
        self.console("🔍 Phase 1: Loading Document Content...")
        self.log("Phase 1: Document Loading")
        
        document_content = self.load_document_content()
        if not document_content:
            self.console("❌ AWS CAF for AI document not found")
            self.log("ERROR: Document not found, using fallback")
            # Use substantial fallback content
            document_content = """AWS Cloud Adoption Framework for AI (AWS CAF for AI) provides comprehensive guidance for organizations adopting artificial intelligence and machine learning capabilities in the cloud environment.

Key principles include:
1. Start with business outcomes and work backwards to identify AI use cases that deliver measurable value to your organization
2. Build a data-driven culture and capabilities across your entire organization to support AI initiatives
3. Implement responsible AI practices including governance, ethics, bias mitigation, and transparency requirements
4. Establish comprehensive governance and risk management frameworks to ensure AI systems are reliable and trustworthy
5. Invest in talent development and change management to support successful AI adoption across teams
6. Create scalable infrastructure and platform capabilities that can support AI workloads at enterprise scale

The framework covers six perspectives: Business, People, Governance, Platform, Security, and Operations. Each perspective provides specific guidance for AI adoption at scale.

Business Perspective focuses on ensuring AI investments align with business strategy and deliver measurable outcomes. This includes identifying high-value use cases, establishing success metrics, building business cases for AI initiatives, and creating governance structures for AI investments.

People Perspective addresses the human elements of AI adoption including skills development, organizational change management, cultural transformation needed to become an AI-driven organization, and building teams with the right mix of technical and business skills.

Governance Perspective establishes frameworks for responsible AI including ethics guidelines, bias detection and mitigation strategies, model governance processes, regulatory compliance requirements, and risk management frameworks.

Platform Perspective covers the technical infrastructure needed to support AI workloads including data platforms, machine learning operations, model deployment pipelines, integration with existing systems, and cloud infrastructure optimization.

Security Perspective addresses unique security considerations for AI systems including data protection strategies, model security requirements, threat detection specific to AI workloads, and privacy preservation techniques.

Operations Perspective focuses on the operational aspects of running AI systems in production including monitoring and observability, maintenance procedures, performance optimization strategies, incident response plans, and continuous improvement processes.

The framework emphasizes the importance of starting with clear business objectives and working backwards to identify the most valuable AI use cases. Organizations should focus on building foundational capabilities in data management, infrastructure, and governance before pursuing advanced AI applications.

Successful AI adoption requires a holistic approach that addresses technical, organizational, and cultural challenges. The framework provides practical guidance for navigating these challenges and building sustainable AI capabilities that can evolve with changing business needs and technological advances.""" * 2

        # Document Statistics
        word_count = len(document_content.split())
        estimated_tokens = int(word_count * 1.3)
        
        self.console(f"   → Document: data/aws-caf-for-ai.txt")
        self.console(f"   → Content: {word_count} words, ~{estimated_tokens} tokens")
        self.console(f"   → Size: {len(document_content)} characters")
        
        if estimated_tokens >= 1024:
            self.console(f"   ✅ Meets minimum token requirement ({estimated_tokens} >= 1024)")
        else:
            self.console(f"   ❌ Below minimum token requirement ({estimated_tokens} < 1024)")

        self.log(f"Document: {word_count} words, {estimated_tokens} tokens, {len(document_content)} chars")

        # Phase 2: Baseline Test (No Cache)
        self.console("")
        self.console("🚀 Phase 2: Baseline Test (No Cache)...")
        self.log("Phase 2: Baseline Test")
        
        model_id = 'amazon.nova-lite-v1:0'
        question = "What are the key principles of the AWS Cloud Adoption Framework for AI?"
        
        self.console(f"   → Model: {self.supported_models.get(model_id, {}).get('name', 'Amazon Nova Lite')}")
        self.console(f"   → Question: {question}")
        
        baseline_result = self.invoke_without_cache(document_content, question, model_id)
        
        if baseline_result['success']:
            self.console(f"   ✅ Response: {baseline_result['response_time']:.2f}s")
            self.console(f"   → Input tokens: {baseline_result['usage'].get('inputTokens', 0)}")
            self.console(f"   → Output tokens: {baseline_result['usage'].get('outputTokens', 0)}")
        else:
            self.console(f"   ❌ Failed: {baseline_result['error']}")
            return

        # Phase 3: Cache Write (First Request)
        self.console("")
        self.console("📦 Phase 3: Cache Write (First Request)...")
        self.log("Phase 3: Cache Write")
        
        self.console("   → Using cache checkpoint after document content")
        
        first_cached_result = self.invoke_with_cache_checkpoint(document_content, question, model_id)
        
        if first_cached_result['success']:
            self.console(f"   ✅ Response: {first_cached_result['response_time']:.2f}s")
            self.console(f"   → Input tokens: {first_cached_result['usage'].get('inputTokens', 0)}")
            self.console(f"   → Output tokens: {first_cached_result['usage'].get('outputTokens', 0)}")
            self.console(f"   → Cache write tokens: {first_cached_result.get('cache_write_tokens', 0)}")
            if first_cached_result.get('cache_write_tokens', 0) > 0:
                self.console(f"   ✅ Cache: Document written to cache")
            else:
                self.console(f"   ⚠️  Cache: No cache write detected")
        else:
            self.console(f"   ❌ Failed: {first_cached_result['error']}")
            return

        # Phase 4: Cache Hit (Second Request)
        self.console("")
        self.console("⚡ Phase 4: Cache Hit (Second Request)...")
        self.log("Phase 4: Cache Hit")
        
        question2 = "How does the framework address AI governance and compliance?"
        self.console(f"   → New question: {question2}")
        self.console("   → Same document context (should hit cache)")
        
        cached_result = self.invoke_with_cache_checkpoint(document_content, question2, model_id)
        
        if cached_result['success']:
            self.console(f"   ✅ Response: {cached_result['response_time']:.2f}s")
            self.console(f"   → Input tokens: {cached_result['usage'].get('inputTokens', 0)}")
            self.console(f"   → Output tokens: {cached_result['usage'].get('outputTokens', 0)}")
            self.console(f"   → Cache read tokens: {cached_result.get('cache_read_tokens', 0)}")
            
            # Cache effectiveness validation
            cache_read_tokens = cached_result.get('cache_read_tokens', 0)
            input_tokens = cached_result['usage'].get('inputTokens', 0)
            
            if cache_read_tokens > 0:
                cache_hit_ratio = (cache_read_tokens / (cache_read_tokens + input_tokens)) * 100 if (cache_read_tokens + input_tokens) > 0 else 0
                self.console(f"   ✅ Cache: {cache_read_tokens} tokens read from cache ({cache_hit_ratio:.1f}% hit rate)")
                
                # Token reduction analysis (key insight from conversation summary)
                baseline_tokens = baseline_result['usage'].get('inputTokens', 0)
                if input_tokens < baseline_tokens:
                    reduction = ((baseline_tokens - input_tokens) / baseline_tokens) * 100
                    self.console(f"   🎯 Token efficiency: {reduction:.1f}% reduction in processed tokens")
            else:
                self.console(f"   ❌ Cache: No cache hit detected (cache miss)")
            
            # Performance comparison
            if baseline_result['success']:
                if cached_result['response_time'] < baseline_result['response_time']:
                    improvement = ((baseline_result['response_time'] - cached_result['response_time']) / baseline_result['response_time']) * 100
                    self.console(f"   → Performance: {improvement:.1f}% faster than baseline")
                else:
                    slowdown = ((cached_result['response_time'] - baseline_result['response_time']) / baseline_result['response_time']) * 100
                    self.console(f"   → Performance: {slowdown:.1f}% slower than baseline")
        else:
            self.console(f"   ❌ Failed: {cached_result['error']}")

        # Results Summary
        self.console("")
        self.console("📊 Results Summary:")
        if baseline_result['success'] and cached_result['success']:
            baseline_tokens = baseline_result['usage'].get('inputTokens', 0)
            cached_tokens = cached_result['usage'].get('inputTokens', 0)
            cache_read_tokens = cached_result.get('cache_read_tokens', 0)
            
            self.console(f"   Baseline (no cache): {baseline_result['response_time']:.2f}s, {baseline_tokens} input tokens")
            self.console(f"   Cache hit (2nd request): {cached_result['response_time']:.2f}s, {cached_tokens} input tokens")
            
            if cache_read_tokens > 0:
                self.console(f"   ✅ Cache Success: {cache_read_tokens} tokens read from cache")
                token_reduction = baseline_tokens - cached_tokens
                if token_reduction > 0:
                    reduction_pct = (token_reduction / baseline_tokens) * 100
                    self.console(f"   🎯 Token Savings: {token_reduction} tokens ({reduction_pct:.1f}% reduction)")
                    self.console(f"   💰 Cost Impact: 90% discount on cached tokens, 25% premium on cache writes")
            else:
                self.console(f"   ❌ Cache Miss: No tokens read from cache")
                
            if estimated_tokens >= 1024:
                self.console("   📏 Token Requirements: ✅ Document meets minimum (1024+ tokens)")
            else:
                self.console("   📏 Token Requirements: ❌ Document below minimum (1024+ tokens)")
        
        self.console("")
        self.console("🎯 Production Usage (AWS Official):")
        self.console("   • Use for applications with repeated document contexts")
        self.console("   • Ensure prompt prefixes are static between requests")
        self.console("   • Meet minimum token requirements per model (1024+ for Nova)")
        self.console("   • Monitor CacheReadInputTokens and CacheWriteInputTokens metrics")
        self.console("   • 5-minute TTL resets with each cache hit")
        self.console("   • Cache writes cost 25% premium, cache reads get 90% discount")
        self.console("")
        self.console("💡 Key Insight: Dramatic token reduction indicates successful caching")
        self.console("   When cache hits occur, only new content gets processed as input tokens")

        self.log("=== Demonstration Summary ===")
        self.log("Prompt caching demonstration completed")
        
        self.console(f"\n📋 Detailed log: {self.log_file.name}")
        self.save_log()

def main():
    """Main execution function with error handling."""
    try:
        caching = PromptCaching()
        caching.demonstrate_prompt_caching()
    except KeyboardInterrupt:
        print("\nPrompt caching demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Prompt caching demonstration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()