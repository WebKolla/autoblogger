"""
Base Agent Module

Provides common functionality for all agents in the multi-agent system.
"""

from typing import Dict, Optional, Any, Callable
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
import json
import time
import random


class BaseAgent(ABC):
    """
    Abstract base class for all agents

    Provides common functionality:
    - DynamoDB integration
    - Bedrock (Claude) client
    - Logging utilities
    - Error handling
    - State management

    All concrete agents must implement the execute() method.
    """

    def __init__(self, workflow_id: str, agent_name: str):
        """
        Initialize base agent

        Args:
            workflow_id: Unique identifier for the workflow
            agent_name: Name of the agent (e.g., "topic_discovery", "research")
        """
        self.workflow_id = workflow_id
        self.agent_name = agent_name
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._execution_start_time = time.time()

        # AWS clients
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.workflow_table = self.dynamodb.Table('blog-workflow-state')
        self.bedrock = self._init_bedrock_client()

        # Configuration
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

        # Metrics tracking
        try:
            from .metrics import MetricsCollector
            self.metrics = MetricsCollector()
        except Exception:
            self.metrics = None  # Metrics collection is optional

        self.log_event(f"Agent initialized: {agent_name}")

    def _init_bedrock_client(self):
        """Initialize Bedrock client with custom timeout configuration"""
        from botocore.config import Config

        bedrock_config = Config(
            read_timeout=300,  # 5 minutes
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
        return boto3.client("bedrock-runtime", region_name="us-east-1", config=bedrock_config)

    @abstractmethod
    def execute(self, input_data: Dict) -> Dict:
        """
        Main execution method - must be implemented by concrete agents

        Args:
            input_data: Input from previous agent or Manager

        Returns:
            Dict with results for next agent

        Raises:
            Exception: If execution fails
        """
        pass

    def get_workflow_context(self) -> Dict:
        """
        Retrieve workflow context from DynamoDB

        Returns:
            Complete workflow data including all agent states
        """
        try:
            response = self.workflow_table.get_item(
                Key={'workflow_id': self.workflow_id}
            )

            if 'Item' not in response:
                self.log_event(f"No workflow found with ID: {self.workflow_id}", level="WARNING")
                return {}

            return response['Item']

        except Exception as e:
            self.log_event(f"Error retrieving workflow context: {str(e)}", level="ERROR")
            raise

    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Recursively convert Python floats to Decimal for DynamoDB compatibility

        Args:
            obj: Object to convert (can be dict, list, or primitive)

        Returns:
            Converted object with Decimals instead of floats
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        else:
            return obj

    def update_agent_state(
        self,
        status: str,
        output: Optional[Dict] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Update this agent's state in DynamoDB

        Args:
            status: Agent status (e.g., "running", "completed", "failed")
            output: Agent output data (optional)
            error: Error message if failed (optional)
            metadata: Additional metadata (optional)
        """
        try:
            completed_at = None
            duration_seconds = None

            if status in ["completed", "failed"]:
                completed_at = datetime.now(timezone.utc).isoformat()
                start_time = datetime.fromisoformat(self.started_at)
                end_time = datetime.fromisoformat(completed_at)
                duration_seconds = int((end_time - start_time).total_seconds())

                # Record metrics
                if self.metrics:
                    try:
                        self.metrics.record_agent_execution(
                            agent_name=self.agent_name,
                            duration_seconds=float(duration_seconds),
                            success=(status == "completed"),
                            workflow_id=self.workflow_id
                        )

                        # Record error if failed
                        if status == "failed" and error:
                            error_type = error.split(':')[0] if ':' in error else "UnknownError"
                            self.metrics.record_error(
                                agent_name=self.agent_name,
                                error_type=error_type,
                                workflow_id=self.workflow_id
                            )
                    except Exception as e:
                        self.log_event(f"Failed to record metrics: {str(e)}", level="WARNING")

            agent_state = {
                "status": status,
                "started_at": self.started_at,
            }

            if completed_at:
                agent_state["completed_at"] = completed_at
            if duration_seconds is not None:
                agent_state["duration_seconds"] = duration_seconds
            if output:
                # Convert floats to Decimal for DynamoDB
                agent_state["output"] = self._convert_floats_to_decimal(output)
            if error:
                agent_state["error"] = error
            if metadata:
                agent_state["metadata"] = self._convert_floats_to_decimal(metadata)

            # Update workflow with agent state
            self.workflow_table.update_item(
                Key={'workflow_id': self.workflow_id},
                UpdateExpression='SET agent_states.#agent_name = :agent_state, updated_at = :updated_at',
                ExpressionAttributeNames={
                    '#agent_name': self.agent_name
                },
                ExpressionAttributeValues={
                    ':agent_state': agent_state,
                    ':updated_at': datetime.now(timezone.utc).isoformat()
                }
            )

            self.log_event(f"Agent state updated: {status}")

        except Exception as e:
            self.log_event(f"Error updating agent state: {str(e)}", level="ERROR")
            raise

    def invoke_claude(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> str:
        """
        Invoke Claude via Bedrock

        Args:
            prompt: User prompt for Claude
            max_tokens: Maximum tokens in response (default 4096)
            temperature: Response temperature 0-1 (default 0.7)
            system: Optional system prompt

        Returns:
            Claude's response text

        Raises:
            Exception: If API call fails
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system:
                body["system"] = system

            self.log_event(f"Invoking Claude (max_tokens={max_tokens}, temp={temperature})")

            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            response_body = json.loads(response["body"].read())
            response_text = response_body["content"][0]["text"]

            tokens_used = response_body.get("usage", {})
            input_tokens = tokens_used.get('input_tokens', 0)
            output_tokens = tokens_used.get('output_tokens', 0)

            self.log_event(f"Claude response received (input_tokens={input_tokens}, output_tokens={output_tokens})")

            # Record cost metrics
            if self.metrics:
                try:
                    from .metrics import CostTracker
                    cost = CostTracker.calculate_bedrock_cost(
                        model='claude-3-sonnet',
                        input_tokens=input_tokens,
                        output_tokens=output_tokens
                    )
                    self.metrics.record_cost(
                        workflow_id=self.workflow_id,
                        agent_name=self.agent_name,
                        cost_usd=cost,
                        operation='bedrock_call'
                    )
                except Exception as e:
                    self.log_event(f"Failed to record cost metrics: {str(e)}", level="WARNING")

            return response_text

        except Exception as e:
            self.log_event(f"Error invoking Claude: {str(e)}", level="ERROR")
            raise

    def log_event(self, message: str, level: str = "INFO", data: Optional[Dict] = None) -> None:
        """
        Log event to CloudWatch (via print)

        Args:
            message: Log message
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            data: Optional structured data to log
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "workflow_id": self.workflow_id,
            "agent": self.agent_name,
            "level": level,
            "message": message
        }

        if data:
            log_entry["data"] = data

        # Print as JSON for CloudWatch structured logging
        print(json.dumps(log_entry))

    def handle_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Handle and log errors

        Args:
            error: The exception that occurred
            context: Optional context about where the error occurred
        """
        error_message = str(error)
        error_type = type(error).__name__

        log_message = f"{error_type}: {error_message}"
        if context:
            log_message = f"{context} - {log_message}"

        self.log_event(log_message, level="ERROR", data={
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        })

        # Update agent state with error
        self.update_agent_state(
            status="failed",
            error=log_message
        )

    def validate_input(self, input_data: Dict, required_fields: list) -> bool:
        """
        Validate that input data contains required fields

        Args:
            input_data: Input data to validate
            required_fields: List of required field names

        Returns:
            True if valid, raises ValueError if invalid

        Raises:
            ValueError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in input_data]

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            self.log_event(error_msg, level="ERROR")
            raise ValueError(error_msg)

        return True

    def get_secrets(self, secret_name: str) -> Dict:
        """
        Retrieve secrets from AWS Secrets Manager

        Args:
            secret_name: Name of the secret

        Returns:
            Dict with secret values
        """
        try:
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])

        except Exception as e:
            self.log_event(f"Error retrieving secret {secret_name}: {str(e)}", level="ERROR")
            raise

    def retry_with_backoff(
        self,
        operation: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ) -> Any:
        """
        Retry an operation with exponential backoff

        Args:
            operation: Callable to retry
            max_retries: Maximum number of retries (default 3)
            base_delay: Initial delay in seconds (default 1.0)
            max_delay: Maximum delay in seconds (default 60.0)
            exponential_base: Base for exponential backoff (default 2.0)
            jitter: Add random jitter to prevent thundering herd (default True)

        Returns:
            Result from operation

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return operation()

            except Exception as e:
                last_exception = e

                # Don't retry on last attempt
                if attempt == max_retries:
                    self.log_event(
                        f"Operation failed after {max_retries} retries",
                        level="ERROR",
                        data={"error": str(e)}
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base ** attempt), max_delay)

                # Add jitter (±25% random variation)
                if jitter:
                    jitter_range = delay * 0.25
                    delay = delay + random.uniform(-jitter_range, jitter_range)

                self.log_event(
                    f"Operation failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.2f}s",
                    level="WARNING",
                    data={"error": str(e), "delay": delay}
                )

                time.sleep(delay)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    def is_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient and should be retried

        Args:
            error: The exception to check

        Returns:
            True if error is transient, False otherwise
        """
        error_message = str(error).lower()
        error_type = type(error).__name__

        # Network/connection errors
        transient_patterns = [
            'timeout',
            'connection',
            'throttl',
            'rate limit',
            'service unavailable',
            'internal server error',
            '500',
            '502',
            '503',
            '504',
            'temporar'
        ]

        # Check error message for transient patterns
        for pattern in transient_patterns:
            if pattern in error_message:
                return True

        # Check error types
        transient_types = [
            'TimeoutError',
            'ConnectionError',
            'BrokenPipeError',
            'IncompleteRead'
        ]

        if error_type in transient_types:
            return True

        return False

    def safe_invoke_claude(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        Invoke Claude with automatic retries on transient failures

        Args:
            prompt: User prompt for Claude
            max_tokens: Maximum tokens in response
            temperature: Response temperature 0-1
            system: Optional system prompt
            max_retries: Maximum retry attempts (default 3)

        Returns:
            Claude's response text

        Raises:
            Exception: If all retries fail
        """
        def _invoke():
            return self.invoke_claude(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system
            )

        try:
            return self.retry_with_backoff(
                operation=_invoke,
                max_retries=max_retries,
                base_delay=2.0,  # Start with 2s delay for API calls
                max_delay=30.0   # Cap at 30s for API calls
            )
        except Exception as e:
            # Only retry if it's a transient error
            if self.is_transient_error(e):
                self.log_event(
                    "Transient error detected, already retried",
                    level="ERROR",
                    data={"error": str(e)}
                )
            raise
