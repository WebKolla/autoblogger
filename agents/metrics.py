"""
CloudWatch Metrics Module
Tracks agent performance, costs, and quality metrics
"""

import boto3
import time
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and publishes metrics to CloudWatch"""

    def __init__(self, namespace: str = "BlogAutomation"):
        """
        Initialize metrics collector

        Args:
            namespace: CloudWatch namespace for metrics
        """
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        self.namespace = namespace
        self.local_metrics: List[Dict] = []

    def record_agent_execution(self, agent_name: str, duration_seconds: float,
                              success: bool, workflow_id: str):
        """
        Record agent execution metrics

        Args:
            agent_name: Name of the agent (e.g., "TopicDiscoveryAgent")
            duration_seconds: How long the agent took to execute
            success: Whether the execution succeeded
            workflow_id: Unique workflow identifier
        """
        try:
            timestamp = datetime.utcnow()

            # Execution duration metric
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'AgentExecutionTime',
                        'Dimensions': [
                            {'Name': 'AgentName', 'Value': agent_name},
                            {'Name': 'Success', 'Value': str(success)}
                        ],
                        'Value': duration_seconds,
                        'Unit': 'Seconds',
                        'Timestamp': timestamp
                    },
                    {
                        'MetricName': 'AgentExecutionCount',
                        'Dimensions': [
                            {'Name': 'AgentName', 'Value': agent_name},
                            {'Name': 'Success', 'Value': str(success)}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': timestamp
                    }
                ]
            )

            logger.info(f"Recorded metrics for {agent_name}: {duration_seconds:.2f}s, success={success}")

        except Exception as e:
            logger.error(f"Failed to record agent execution metrics: {str(e)}")

    def record_error(self, agent_name: str, error_type: str, workflow_id: str):
        """
        Record agent error

        Args:
            agent_name: Name of the agent that errored
            error_type: Type of error (e.g., "APIError", "ValidationError")
            workflow_id: Unique workflow identifier
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'AgentErrors',
                        'Dimensions': [
                            {'Name': 'AgentName', 'Value': agent_name},
                            {'Name': 'ErrorType', 'Value': error_type}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )

            logger.info(f"Recorded error for {agent_name}: {error_type}")

        except Exception as e:
            logger.error(f"Failed to record error metric: {str(e)}")

    def record_quality_score(self, workflow_id: str, quality_score: float,
                            validation_status: str):
        """
        Record article quality metrics

        Args:
            workflow_id: Unique workflow identifier
            quality_score: Overall quality score (0-1)
            validation_status: APPROVED, NEEDS_REVISION, or REJECTED
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'ArticleQualityScore',
                        'Dimensions': [
                            {'Name': 'ValidationStatus', 'Value': validation_status}
                        ],
                        'Value': quality_score,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    },
                    {
                        'MetricName': 'ArticleValidationCount',
                        'Dimensions': [
                            {'Name': 'Status', 'Value': validation_status}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )

            logger.info(f"Recorded quality score: {quality_score:.2f}, status={validation_status}")

        except Exception as e:
            logger.error(f"Failed to record quality metrics: {str(e)}")

    def record_cost(self, workflow_id: str, agent_name: str, cost_usd: float,
                   operation: str):
        """
        Record cost metrics

        Args:
            workflow_id: Unique workflow identifier
            agent_name: Agent that incurred the cost
            cost_usd: Cost in USD
            operation: Operation type (e.g., "bedrock_call", "api_call")
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'AgentCost',
                        'Dimensions': [
                            {'Name': 'AgentName', 'Value': agent_name},
                            {'Name': 'Operation', 'Value': operation}
                        ],
                        'Value': cost_usd,
                        'Unit': 'None',  # USD
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )

            logger.info(f"Recorded cost for {agent_name}: ${cost_usd:.4f} ({operation})")

        except Exception as e:
            logger.error(f"Failed to record cost metric: {str(e)}")

    def record_workflow_metrics(self, workflow_id: str, total_duration: float,
                               status: str, agent_count: int):
        """
        Record overall workflow metrics

        Args:
            workflow_id: Unique workflow identifier
            total_duration: Total workflow execution time in seconds
            status: Final workflow status
            agent_count: Number of agents executed
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'WorkflowDuration',
                        'Dimensions': [
                            {'Name': 'Status', 'Value': status}
                        ],
                        'Value': total_duration,
                        'Unit': 'Seconds',
                        'Timestamp': datetime.utcnow()
                    },
                    {
                        'MetricName': 'WorkflowCount',
                        'Dimensions': [
                            {'Name': 'Status', 'Value': status}
                        ],
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    },
                    {
                        'MetricName': 'AgentsExecutedPerWorkflow',
                        'Value': agent_count,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )

            logger.info(f"Recorded workflow metrics: {total_duration:.2f}s, {agent_count} agents, status={status}")

        except Exception as e:
            logger.error(f"Failed to record workflow metrics: {str(e)}")


class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(self, operation_name: str):
        """
        Initialize timer

        Args:
            operation_name: Name of the operation being timed
        """
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None

    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer"""
        self.duration = time.time() - self.start_time
        logger.info(f"{self.operation_name} took {self.duration:.2f}s")
        return False  # Don't suppress exceptions


class CostTracker:
    """Tracks AWS service costs"""

    # Pricing as of 2025 (approximate)
    BEDROCK_PRICING = {
        'claude-3-sonnet': {
            'input': 0.003,   # Per 1K tokens
            'output': 0.015   # Per 1K tokens
        }
    }

    DYNAMODB_PRICING = {
        'write': 0.00000125,  # Per write request unit
        'read': 0.00000025    # Per read request unit
    }

    @classmethod
    def calculate_bedrock_cost(cls, model: str, input_tokens: int,
                              output_tokens: int) -> float:
        """
        Calculate Bedrock API cost

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = cls.BEDROCK_PRICING.get(model, cls.BEDROCK_PRICING['claude-3-sonnet'])

        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']

        return input_cost + output_cost

    @classmethod
    def calculate_dynamodb_cost(cls, writes: int = 0, reads: int = 0) -> float:
        """
        Calculate DynamoDB cost

        Args:
            writes: Number of write operations
            reads: Number of read operations

        Returns:
            Cost in USD
        """
        write_cost = writes * cls.DYNAMODB_PRICING['write']
        read_cost = reads * cls.DYNAMODB_PRICING['read']

        return write_cost + read_cost

    @classmethod
    def estimate_monthly_cost(cls, articles_per_month: int = 30) -> Dict:
        """
        Estimate monthly costs

        Args:
            articles_per_month: Number of articles generated per month

        Returns:
            Cost breakdown dictionary
        """
        # Estimated tokens per article
        research_tokens = 5000  # Input: 2000, Output: 3000
        writer_tokens = 20000   # Input: 4000, Output: 16000

        # Bedrock costs
        research_cost_per_article = cls.calculate_bedrock_cost(
            'claude-3-sonnet', 2000, 3000
        )
        writer_cost_per_article = cls.calculate_bedrock_cost(
            'claude-3-sonnet', 4000, 16000
        )

        bedrock_monthly = (research_cost_per_article + writer_cost_per_article) * articles_per_month

        # DynamoDB costs (estimated 50 writes, 100 reads per article)
        dynamodb_monthly = cls.calculate_dynamodb_cost(
            writes=50 * articles_per_month,
            reads=100 * articles_per_month
        )

        # Lambda costs (negligible for this workload)
        lambda_monthly = 0.20  # ~$0.20/month

        # SES costs (negligible - free tier covers it)
        ses_monthly = 0.00

        total = bedrock_monthly + dynamodb_monthly + lambda_monthly + ses_monthly

        return {
            'bedrock': round(bedrock_monthly, 2),
            'dynamodb': round(dynamodb_monthly, 2),
            'lambda': lambda_monthly,
            'ses': ses_monthly,
            'total': round(total, 2),
            'per_article': round(total / articles_per_month, 2)
        }
