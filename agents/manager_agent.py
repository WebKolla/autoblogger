"""
Manager Agent Module

Orchestrates the multi-agent workflow for blog content generation.
Manages state transitions, agent coordination, and error recovery.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone
import boto3
import json
from enum import Enum
import time
import hashlib
import os


class WorkflowState(Enum):
    """Workflow states"""
    INITIALIZED = "initialized"
    CLEANING = "cleaning"
    DISCOVERING_TOPIC = "discovering_topic"
    TOPIC_SELECTED = "topic_selected"
    RESEARCHING = "researching"
    RESEARCH_COMPLETE = "research_complete"
    WRITING = "writing"
    DRAFT_COMPLETE = "draft_complete"
    CHECKING = "checking"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    EMAIL_SENT = "email_sent"
    PUBLISHED = "published"
    DECLINED = "declined"
    FAILED = "failed"


class ManagerAgent:
    """
    Manager Agent - Orchestrates the entire workflow

    Responsibilities:
    - Initialize workflow in DynamoDB
    - Coordinate agent execution
    - Manage state transitions
    - Handle errors and retries
    - Send approval emails
    """

    def __init__(self):
        """Initialize Manager Agent"""
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.workflow_table = self.dynamodb.Table('blog-workflow-state')
        self.ses = boto3.client('ses', region_name='us-east-1')

        # Metrics tracking
        try:
            from .metrics import MetricsCollector
            self.metrics = MetricsCollector()
        except Exception:
            self.metrics = None  # Metrics collection is optional

    def start_workflow(self, trigger_type: str = "daily") -> Dict:
        """
        Start a new workflow

        Args:
            trigger_type: Type of trigger ("daily" or "manual")

        Returns:
            Dict with workflow_id and status
        """
        workflow_id = f"workflow-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        try:
            # Initialize workflow in DynamoDB
            workflow_data = {
                "workflow_id": workflow_id,
                "status": WorkflowState.INITIALIZED.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "trigger_type": trigger_type,
                "agent_states": {},
                "retry_count": 0,
                "max_retries": 2,
                "schema_version": "2.0"
            }

            self.workflow_table.put_item(Item=workflow_data)

            self.log_event(workflow_id, f"Workflow initialized: {workflow_id}", data={"trigger_type": trigger_type})

            # Start the workflow execution
            result = self._execute_workflow(workflow_id)

            return {
                "workflow_id": workflow_id,
                "status": "success",
                "result": result
            }

        except Exception as e:
            self.log_event(workflow_id, f"Workflow initialization failed: {str(e)}", level="ERROR")
            self._update_workflow_status(workflow_id, WorkflowState.FAILED.value)
            raise

    def _execute_workflow(self, workflow_id: str) -> Dict:
        """
        Execute the complete workflow

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict with final workflow result
        """
        workflow_start_time = time.time()
        agent_count = 0

        try:
            # Step 1: Topic Discovery (includes cleanup)
            self.log_event(workflow_id, "Starting Topic Discovery Agent")
            self._update_workflow_status(workflow_id, WorkflowState.DISCOVERING_TOPIC.value)

            from .topic_discovery_agent import TopicDiscoveryAgent
            topic_agent = TopicDiscoveryAgent(workflow_id)
            topic_result = topic_agent.execute({})
            agent_count += 1

            if topic_result.get("status") != "success":
                raise Exception(f"Topic Discovery failed: {topic_result.get('error', 'Unknown error')}")

            self._update_workflow_status(workflow_id, WorkflowState.TOPIC_SELECTED.value)
            self.log_event(workflow_id, "Topic selected successfully", data={"topic": topic_result.get("selected_topic", {}).get("title")})

            # Step 2: Research Agent
            self.log_event(workflow_id, "Starting Research Agent")
            self._update_workflow_status(workflow_id, WorkflowState.RESEARCHING.value)

            from .research_agent import ResearchAgent
            research_agent = ResearchAgent(workflow_id)
            research_result = research_agent.execute({
                "selected_topic": topic_result["selected_topic"]
            })
            agent_count += 1

            if research_result.get("status") != "success":
                raise Exception(f"Research failed: {research_result.get('error', 'Unknown error')}")

            self._update_workflow_status(workflow_id, WorkflowState.RESEARCH_COMPLETE.value)
            self.log_event(workflow_id, "Research completed successfully")

            # Step 3: SEO Writer Agent
            self.log_event(workflow_id, "Starting SEO Writer Agent")
            self._update_workflow_status(workflow_id, WorkflowState.WRITING.value)

            from .seo_writer_agent import SEOWriterAgent
            writer_agent = SEOWriterAgent(workflow_id)
            writer_result = writer_agent.execute({
                "research_report": research_result["research_report"]
            })
            agent_count += 1

            if writer_result.get("status") != "success":
                raise Exception(f"Writing failed: {writer_result.get('error', 'Unknown error')}")

            self._update_workflow_status(workflow_id, WorkflowState.DRAFT_COMPLETE.value)
            self.log_event(workflow_id, "Article writing completed", data={
                "word_count": writer_result["metadata"]["word_count"],
                "images": writer_result["metadata"]["images_sourced"]
            })

            # Step 4: Content Checker Agent
            self.log_event(workflow_id, "Starting Content Checker Agent")
            self._update_workflow_status(workflow_id, WorkflowState.CHECKING.value)

            # Get recent articles for uniqueness check
            recent_articles = self._get_recent_articles(workflow_id)

            from .content_checker_agent import ContentCheckerAgent
            checker_agent = ContentCheckerAgent(workflow_id)
            checker_result = checker_agent.execute({
                "article": writer_result["article"],
                "research_report": research_result["research_report"],
                "recent_articles": recent_articles
            })
            agent_count += 1

            if checker_result.get("status") != "success":
                raise Exception(f"Content checking failed: {checker_result.get('error', 'Unknown error')}")

            validation_result = checker_result["validation_result"]
            validation_status = validation_result["status"]

            self.log_event(workflow_id, f"Content check complete: {validation_status}", data={
                "quality_score": validation_result["quality_score"],
                "status": validation_status
            })

            # Update workflow status based on validation
            if validation_status == "APPROVED":
                self._update_workflow_status(workflow_id, WorkflowState.APPROVED.value)
            elif validation_status == "NEEDS_REVISION":
                self._update_workflow_status(workflow_id, WorkflowState.NEEDS_REVISION.value)
            else:  # REJECTED
                self._update_workflow_status(workflow_id, WorkflowState.REJECTED.value)
                # Don't send email for rejected articles
                self.log_event(workflow_id, "Article rejected by Content Checker", level="WARNING")
                return {
                    "workflow_id": workflow_id,
                    "status": WorkflowState.REJECTED.value,
                    "message": "Article rejected - quality issues found",
                    "validation": validation_result
                }

            # Step 5: Send approval email
            self.log_event(workflow_id, "Sending approval email")
            email_sent = self._send_approval_email(
                workflow_id=workflow_id,
                article=writer_result["article"],
                images=writer_result["images"],
                validation_result=validation_result
            )

            if email_sent:
                self.log_event(workflow_id, "Approval email sent successfully")
                self._update_workflow_status(workflow_id, WorkflowState.EMAIL_SENT.value)
            else:
                self.log_event(workflow_id, "Failed to send approval email", level="WARNING")
                self._update_workflow_status(workflow_id, WorkflowState.EMAIL_SENT.value)  # Continue anyway

            # Store final article data in workflow
            self._store_article_data(workflow_id, {
                "topic": topic_result["selected_topic"],
                "article": writer_result["article"],
                "images": writer_result["images"]
            })

            # Record workflow metrics
            workflow_duration = time.time() - workflow_start_time
            if self.metrics:
                try:
                    # Record quality score
                    self.metrics.record_quality_score(
                        workflow_id=workflow_id,
                        quality_score=float(validation_result["quality_score"]),
                        validation_status=validation_status
                    )

                    # Record overall workflow metrics
                    self.metrics.record_workflow_metrics(
                        workflow_id=workflow_id,
                        total_duration=workflow_duration,
                        status=WorkflowState.EMAIL_SENT.value,
                        agent_count=agent_count
                    )
                except Exception as e:
                    self.log_event(workflow_id, f"Failed to record workflow metrics: {str(e)}", level="WARNING")

            return {
                "workflow_id": workflow_id,
                "status": WorkflowState.EMAIL_SENT.value,
                "message": f"Phase 3 workflow completed successfully - {validation_status}",
                "article_preview": {
                    "title": writer_result["article"]["title"],
                    "word_count": writer_result["metadata"]["word_count"],
                    "images": writer_result["metadata"]["images_sourced"],
                    "quality_score": validation_result["quality_score"],
                    "validation_status": validation_status
                },
                "validation": validation_result,
                "metrics": {
                    "duration_seconds": round(workflow_duration, 2),
                    "agents_executed": agent_count
                }
            }

        except Exception as e:
            # Record failed workflow metrics
            workflow_duration = time.time() - workflow_start_time
            if self.metrics:
                try:
                    self.metrics.record_workflow_metrics(
                        workflow_id=workflow_id,
                        total_duration=workflow_duration,
                        status=WorkflowState.FAILED.value,
                        agent_count=agent_count
                    )
                except Exception:
                    pass  # Ignore metrics errors during failure handling

            self.log_event(workflow_id, f"Workflow execution failed: {str(e)}", level="ERROR")
            self._update_workflow_status(workflow_id, WorkflowState.FAILED.value)
            raise

    def _update_workflow_status(self, workflow_id: str, status: str, metadata: Optional[Dict] = None) -> None:
        """
        Update workflow status in DynamoDB

        Args:
            workflow_id: Workflow identifier
            status: New workflow status
            metadata: Optional metadata to store
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if metadata:
                update_data["metadata"] = metadata

            # Build update expression dynamically
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {
                ":status": status,
                ":updated_at": update_data["updated_at"]
            }

            if metadata:
                update_expression += ", metadata = :metadata"
                expression_attribute_values[":metadata"] = metadata

            self.workflow_table.update_item(
                Key={'workflow_id': workflow_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            self.log_event(workflow_id, f"Workflow status updated: {status}")

        except Exception as e:
            self.log_event(workflow_id, f"Error updating workflow status: {str(e)}", level="ERROR")
            raise

    def get_workflow_state(self, workflow_id: str) -> Dict:
        """
        Retrieve current workflow state

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict with workflow data
        """
        try:
            response = self.workflow_table.get_item(
                Key={'workflow_id': workflow_id}
            )

            if 'Item' not in response:
                raise ValueError(f"Workflow not found: {workflow_id}")

            return response['Item']

        except Exception as e:
            self.log_event(workflow_id, f"Error retrieving workflow state: {str(e)}", level="ERROR")
            raise

    def handle_agent_error(
        self,
        workflow_id: str,
        agent_name: str,
        error: Exception,
        retry: bool = True
    ) -> bool:
        """
        Handle agent errors and decide whether to retry

        Args:
            workflow_id: Workflow identifier
            agent_name: Name of the failed agent
            error: The exception that occurred
            retry: Whether to attempt retry (default True)

        Returns:
            True if retrying, False if giving up
        """
        try:
            workflow = self.get_workflow_state(workflow_id)
            retry_count = workflow.get("retry_count", 0)
            max_retries = workflow.get("max_retries", 2)

            self.log_event(
                workflow_id,
                f"Agent {agent_name} failed: {str(error)}",
                level="ERROR",
                data={
                    "agent": agent_name,
                    "retry_count": retry_count,
                    "max_retries": max_retries
                }
            )

            if retry and retry_count < max_retries:
                # Increment retry count
                new_retry_count = retry_count + 1
                self.workflow_table.update_item(
                    Key={'workflow_id': workflow_id},
                    UpdateExpression='SET retry_count = :count',
                    ExpressionAttributeValues={':count': new_retry_count}
                )

                self.log_event(
                    workflow_id,
                    f"Retrying workflow (attempt {new_retry_count}/{max_retries})"
                )

                return True  # Will retry

            else:
                # Max retries reached or retry disabled
                self._update_workflow_status(workflow_id, WorkflowState.FAILED.value)
                self.log_event(
                    workflow_id,
                    f"Workflow failed permanently after {retry_count} retries",
                    level="ERROR"
                )

                # TODO: Send alert email to admin
                return False  # Giving up

        except Exception as e:
            self.log_event(
                workflow_id,
                f"Error handling agent error: {str(e)}",
                level="ERROR"
            )
            return False

    def _get_recent_articles(self, workflow_id: str, limit: int = 5) -> list:
        """
        Get recent published articles for uniqueness checking

        Args:
            workflow_id: Current workflow ID
            limit: Number of recent articles to retrieve

        Returns:
            List of recent article data
        """
        try:
            from boto3.dynamodb.conditions import Attr

            # Scan for published articles
            response = self.workflow_table.scan(
                FilterExpression=Attr('status').eq('published'),
                Limit=limit * 2  # Get more to filter out current workflow
            )

            articles = response.get('Items', [])

            # Filter out current workflow and sort by date
            articles = [a for a in articles if a.get('workflow_id') != workflow_id]
            articles.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            return articles[:limit]

        except Exception as e:
            self.log_event(workflow_id, f"Error retrieving recent articles: {str(e)}", level="WARNING")
            return []

    def _store_article_data(self, workflow_id: str, article_data: Dict) -> None:
        """
        Store final article data in DynamoDB

        Args:
            workflow_id: Workflow identifier
            article_data: Complete article data with topic, article, images
        """
        try:
            from decimal import Decimal

            # Convert floats to Decimal for DynamoDB
            def convert_floats(obj):
                if isinstance(obj, float):
                    return Decimal(str(obj))
                elif isinstance(obj, dict):
                    return {k: convert_floats(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_floats(item) for item in obj]
                return obj

            article_data_converted = convert_floats(article_data)

            self.workflow_table.update_item(
                Key={'workflow_id': workflow_id},
                UpdateExpression='SET article_data = :article_data, topic_title = :topic_title, topic_category = :topic_category, article_title = :article_title',
                ExpressionAttributeValues={
                    ':article_data': article_data_converted,
                    ':topic_title': article_data['topic']['title'],
                    ':topic_category': article_data['topic']['category'],
                    ':article_title': article_data['article']['title']
                }
            )

            self.log_event(workflow_id, "Article data stored in DynamoDB")

        except Exception as e:
            self.log_event(workflow_id, f"Error storing article data: {str(e)}", level="ERROR")
            # Don't raise - this is not critical to workflow

    def log_event(
        self,
        workflow_id: str,
        message: str,
        level: str = "INFO",
        data: Optional[Dict] = None
    ) -> None:
        """
        Log event to CloudWatch

        Args:
            workflow_id: Workflow identifier
            message: Log message
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            data: Optional structured data
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "workflow_id": workflow_id,
            "agent": "manager",
            "level": level,
            "message": message
        }

        if data:
            log_entry["data"] = data

        print(json.dumps(log_entry))

    def _generate_token(self, workflow_id: str) -> str:
        """Generate secure approval token"""
        data = f"{workflow_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _send_approval_email(
        self,
        workflow_id: str,
        article: Dict,
        images: list,
        validation_result: Dict
    ) -> bool:
        """
        Send approval email with quality validation details

        Args:
            workflow_id: Workflow identifier
            article: Generated article data
            images: List of sourced images
            validation_result: Quality validation results

        Returns:
            bool: True if email sent successfully
        """
        try:
            approval_token = self._generate_token(workflow_id)

            # Store approval data in workflow
            self.workflow_table.update_item(
                Key={'workflow_id': workflow_id},
                UpdateExpression='SET approval_token = :token, approval_data = :data',
                ExpressionAttributeValues={
                    ':token': approval_token,
                    ':data': {
                        'status': 'awaiting_approval',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                }
            )

            api_url = os.environ.get("API_GATEWAY_URL", "YOUR_API_URL")

            # Extract validation details
            quality_score = int(validation_result.get("quality_score", 0) * 100)
            validation_status = validation_result.get("status", "UNKNOWN")
            feedback = validation_result.get("feedback", {})
            strengths = feedback.get("strengths", [])
            weaknesses = feedback.get("weaknesses", [])

            # Build quality report HTML
            quality_color = "#48bb78" if quality_score >= 85 else "#ed8936" if quality_score >= 70 else "#f56565"
            strengths_html = ''.join([f'<li>✅ {s}</li>' for s in strengths[:3]])
            weaknesses_html = ''.join([f'<li>⚠️ {w}</li>' for w in weaknesses[:3]])

            # Extract content preview
            content = article.get("content", "")
            if not content and "portable_text_body" in article:
                # Extract text from portable text
                blocks = article["portable_text_body"]
                content = " ".join([
                    block.get("children", [{}])[0].get("text", "")
                    for block in blocks if block.get("_type") == "block"
                ])
            preview_text = content[:800] + "..." if len(content) > 800 else content

            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2c5282; color: white; padding: 20px; text-align: center; }}
                    .quality-badge {{ background: {quality_color}; color: white; padding: 10px 20px; border-radius: 25px; font-size: 24px; font-weight: bold; display: inline-block; margin: 10px 0; }}
                    .metadata {{ background: #f7fafc; padding: 15px; margin: 20px 0; border-left: 4px solid #4299e1; }}
                    .quality-section {{ background: #fff5f5; padding: 15px; margin: 20px 0; border-left: 4px solid {quality_color}; }}
                    .quality-section h3 {{ margin-top: 0; color: {quality_color}; }}
                    .quality-section ul {{ margin: 10px 0; padding-left: 20px; }}
                    .content {{ line-height: 1.6; padding: 20px 0; }}
                    .actions {{ text-align: center; margin: 30px 0; }}
                    .btn {{ display: inline-block; padding: 15px 30px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .btn-approve {{ background: #48bb78; color: white; }}
                    .btn-decline {{ background: #f56565; color: white; }}
                    .images {{ margin: 20px 0; }}
                    .images img {{ max-width: 200px; margin: 10px; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📝 New Article Ready for Review</h1>
                    <div class="quality-badge">Quality Score: {quality_score}/100</div>
                    <p style="margin: 5px 0; font-size: 14px;">Status: {validation_status}</p>
                </div>

                <h2>{article.get('title', 'Untitled')}</h2>

                <div class="quality-section">
                    <h3>🔍 Quality Validation Report</h3>
                    <p><strong>Overall Score:</strong> {quality_score}/100 ({validation_status})</p>

                    {f'<p><strong>Strengths:</strong></p><ul>{strengths_html}</ul>' if strengths else ''}
                    {f'<p><strong>Areas for Improvement:</strong></p><ul>{weaknesses_html}</ul>' if weaknesses else ''}

                    <p><strong>Recommendation:</strong> {validation_result.get("approval_recommendation", "Review recommended")}</p>
                </div>

                <div class="metadata">
                    <p><strong>📊 Word Count:</strong> {article.get('word_count', 'N/A')}</p>
                    <p><strong>⏱️ Reading Time:</strong> {article.get('estimated_read_time', article.get('reading_time', 'N/A'))} minutes</p>
                    <p><strong>🔑 Keywords:</strong> {', '.join(article.get('seo_metadata', {}).get('keywords', ['N/A']))}</p>
                    <p><strong>📁 Category:</strong> {article.get('original_topic', {}).get('category', 'N/A')}</p>
                </div>

                <div class="content">
                    <h3>Article Preview:</h3>
                    <p>{preview_text}</p>
                    <p><em>... (full article available in system)</em></p>
                </div>

                <div class="images">
                    <h3>Images ({len(images)}):</h3>
                    {''.join([f'<img src="{img.get("url", "")}" alt="{img.get("alt", "")}">' for img in images[:3]])}
                </div>

                <div class="actions">
                    <a href="{api_url}/approve?token={approval_token}&action=approve" class="btn btn-approve">
                        ✅ APPROVE & PUBLISH
                    </a>
                    <a href="{api_url}/approve?token={approval_token}&action=decline" class="btn btn-decline">
                        ❌ DECLINE
                    </a>
                </div>

                <p style="text-align: center; color: #666; font-size: 12px; margin-top: 40px;">
                    This article was generated by the multi-agent blog automation system.<br>
                    Workflow ID: {workflow_id}<br>
                    Quality validated by ContentCheckerAgent
                </p>
            </body>
            </html>
            """

            response = self.ses.send_email(
                Source="chin@acrossceylon.com",
                Destination={"ToAddresses": ["chin@acrossceylon.com"]},
                Message={
                    "Subject": {"Data": f'[Quality: {quality_score}/100] {article.get("title", "New Article")[:50]}...'},
                    "Body": {"Html": {"Data": html_body}},
                },
            )

            self.log_event(workflow_id, f"Approval email sent: {response['MessageId']}")
            return True

        except Exception as e:
            self.log_event(workflow_id, f"Failed to send email: {str(e)}", level="ERROR")
            return False


def manager_workflow_handler(event: Dict, context: Any) -> Dict:
    """
    Lambda handler for Manager Agent

    This replaces the old daily_workflow_handler and manual_trigger_handler

    Args:
        event: Lambda event (contains trigger_type)
        context: Lambda context

    Returns:
        Dict with workflow result
    """
    try:
        trigger_type = event.get("trigger_type", "manual")

        manager = ManagerAgent()
        result = manager.start_workflow(trigger_type=trigger_type)

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        print(f"[ERROR] Manager workflow handler failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Workflow execution failed"
            })
        }
