"""
Multi-Agent Blog Automation Lambda Handler
Production-ready integration with ManagerAgent system
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict

# Import multi-agent system
from agents.manager_agent import ManagerAgent


def multi_agent_workflow_handler(event, context):
    """
    Multi-agent workflow handler - lets ManagerAgent handle everything
    ManagerAgent coordinates: TopicDiscovery -> Research -> SEOWriter -> ContentChecker
    """
    start_time = time.time()

    print("🚀 Starting multi-agent workflow...")
    print(f"Trigger: {event.get('trigger_type', 'manual')}")

    try:
        # Initialize ManagerAgent
        # ManagerAgent will handle:
        # - Workflow creation in DynamoDB
        # - Agent coordination
        # - State management
        # - Error handling
        # - Email sending
        manager = ManagerAgent()

        # Start the workflow
        # This will:
        # 1. Create workflow in DynamoDB with unique ID
        # 2. Run TopicDiscoveryAgent to select topic
        # 3. Run ResearchAgent to gather info
        # 4. Run SEOWriterAgent to generate article
        # 5. Run ContentCheckerAgent to validate quality
        # 6. Send approval email
        # 7. Update workflow status to 'awaiting_approval'
        print("Executing multi-agent workflow...")
        result = manager.start_workflow(trigger_type=event.get('trigger_type', 'manual'))

        # Calculate execution time
        duration = time.time() - start_time

        # Extract workflow details
        workflow_id = result.get("workflow_id")

        # Check if workflow succeeded
        if not workflow_id:
            error_msg = result.get("error", "Unknown error in workflow execution")
            print(f"❌ Workflow failed: {error_msg}")

            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": error_msg,
                    "duration_seconds": duration
                })
            }

        # Success!
        workflow_status = result.get("status", "unknown")
        print(f"✅ Workflow completed: {workflow_id}")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📋 Status: {workflow_status}")

        # Extract metrics from result (already provided by ManagerAgent)
        article_preview = result.get("article_preview", {})
        validation = result.get("validation", {})

        # For REJECTED articles, article_preview is empty but validation has data
        if workflow_status == "rejected":
            topic_title = "Article Rejected"
            quality_score = validation.get("quality_score", 0)
            word_count = 0
            validation_status = validation.get("status", "REJECTED")
        else:
            topic_title = article_preview.get("title", "N/A")
            quality_score = article_preview.get("quality_score", validation.get("quality_score", 0))
            word_count = article_preview.get("word_count", 0)
            validation_status = article_preview.get("validation_status", validation.get("status", "unknown"))

        print(f"📝 Topic: {topic_title}")
        print(f"📊 Quality Score: {quality_score}/100 ({validation_status})")
        if word_count > 0:
            print(f"📏 Word Count: {word_count}")

        # Return success response
        response_body = {
            "success": True,
            "workflow_id": workflow_id,
            "status": workflow_status,
            "quality_score": quality_score,
            "validation_status": validation_status,
            "duration_seconds": round(duration, 2),
            "message": result.get("message", f"Multi-agent workflow completed: {validation_status}")
        }

        # Only include topic and word_count if article wasn't rejected
        if workflow_status != "rejected":
            response_body["topic"] = topic_title
            response_body["word_count"] = word_count

        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)

        print(f"❌ Unexpected error: {error_msg}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": error_msg,
                "duration_seconds": duration
            })
        }


def multi_agent_daily_handler(event, context):
    """Daily automated trigger for multi-agent workflow"""
    event['trigger_type'] = 'daily'
    return multi_agent_workflow_handler(event, context)


# For local testing
if __name__ == "__main__":
    print("Testing multi-agent workflow locally...")
    result = multi_agent_workflow_handler({}, None)
    print("\n" + "="*60)
    print("RESULT:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
