"""
Phase 1 End-to-End Test

Tests the multi-agent foundation:
- Manager Agent orchestration
- Topic Discovery Agent execution
- DynamoDB state management
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add agents directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.manager_agent import ManagerAgent
from agents.topic_discovery_agent import TopicDiscoveryAgent
import boto3


def test_topic_discovery_standalone():
    """Test Topic Discovery Agent in standalone mode"""
    print("\n" + "=" * 60)
    print("TEST 1: Topic Discovery Agent (Standalone)")
    print("=" * 60)

    workflow_id = f"test-workflow-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    # Initialize workflow in DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('blog-workflow-state')

    workflow_data = {
        "workflow_id": workflow_id,
        "status": "initialized",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "agent_states": {},
        "schema_version": "2.0"
    }

    table.put_item(Item=workflow_data)
    print(f"✓ Created test workflow: {workflow_id}")

    try:
        # Run Topic Discovery Agent
        agent = TopicDiscoveryAgent(workflow_id)
        result = agent.execute({})

        print("\n✓ Topic Discovery Agent completed successfully")
        print(f"\nCleanup Summary:")
        print(f"  - Deleted workflows: {result['cleanup_summary'].get('deleted_workflows', 0)}")

        print(f"\nAnalysis:")
        analysis = result['analysis']
        print(f"  - Total articles: {analysis.get('total_articles', 0)}")
        print(f"  - Categories: {len(analysis.get('category_distribution', {}))}")
        print(f"  - Gap categories: {len(analysis.get('gap_categories', []))}")

        print(f"\nSelected Topic:")
        topic = result['selected_topic']
        print(f"  - Title: {topic['title']}")
        print(f"  - Category: {topic['category']}")
        print(f"  - Uniqueness Score: {topic['uniqueness_score']}")
        print(f"  - Reason: {topic['selection_reason']}")

        # Verify DynamoDB state
        workflow = table.get_item(Key={'workflow_id': workflow_id})['Item']
        agent_state = workflow.get('agent_states', {}).get('topic_discovery', {})

        print(f"\nAgent State in DynamoDB:")
        print(f"  - Status: {agent_state.get('status')}")
        print(f"  - Duration: {agent_state.get('duration_seconds')} seconds")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup test workflow
        try:
            table.delete_item(Key={'workflow_id': workflow_id})
            print(f"\n✓ Cleaned up test workflow")
        except Exception as e:
            print(f"⚠ Warning: Could not clean up test workflow: {str(e)}")


def test_manager_agent_workflow():
    """Test Manager Agent orchestrating full workflow"""
    print("\n" + "=" * 60)
    print("TEST 2: Manager Agent (Full Orchestration)")
    print("=" * 60)

    try:
        manager = ManagerAgent()
        result = manager.start_workflow(trigger_type="test")

        print(f"\n✓ Manager Agent workflow completed")
        print(f"\nWorkflow Result:")
        print(f"  - Workflow ID: {result['workflow_id']}")
        print(f"  - Status: {result['status']}")
        print(f"  - Message: {result['result']['message']}")

        # Verify workflow in DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('blog-workflow-state')

        workflow = table.get_item(Key={'workflow_id': result['workflow_id']})['Item']

        print(f"\nFinal Workflow State:")
        print(f"  - Status: {workflow.get('status')}")
        print(f"  - Schema Version: {workflow.get('schema_version')}")

        # Check agent states
        agent_states = workflow.get('agent_states', {})
        print(f"\nAgent Execution Summary:")
        for agent_name, state in agent_states.items():
            status = state.get('status')
            duration = state.get('duration_seconds', 'N/A')
            print(f"  - {agent_name}: {status} ({duration}s)")

        # Cleanup test workflow
        table.delete_item(Key={'workflow_id': result['workflow_id']})
        print(f"\n✓ Cleaned up test workflow")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamodb_schema():
    """Verify DynamoDB schema v2.0 is properly set up"""
    print("\n" + "=" * 60)
    print("TEST 3: DynamoDB Schema Verification")
    print("=" * 60)

    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('blog-workflow-state')

        # Check for schema v2.0 workflows
        response = table.scan(
            FilterExpression="schema_version = :version",
            ExpressionAttributeValues={':version': '2.0'},
            Limit=5
        )

        workflows = response.get('Items', [])

        print(f"\n✓ Found {len(workflows)} workflows with schema v2.0")

        if workflows:
            sample = workflows[0]
            print(f"\nSample Workflow Schema:")
            print(f"  - workflow_id: {sample.get('workflow_id')}")
            print(f"  - schema_version: {sample.get('schema_version')}")
            print(f"  - agent_states present: {'agent_states' in sample}")
            print(f"  - status: {sample.get('status')}")

        # Check for unmigrated workflows
        response = table.scan(
            FilterExpression="attribute_not_exists(schema_version) OR schema_version <> :version",
            ExpressionAttributeValues={':version': '2.0'},
            Limit=5
        )

        unmigrated = response.get('Items', [])

        if unmigrated:
            print(f"\n⚠ Warning: Found {len(unmigrated)} unmigrated workflows")
            for workflow in unmigrated:
                print(f"  - {workflow.get('workflow_id')}")
            return False
        else:
            print(f"\n✓ All workflows migrated to schema v2.0")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 1 tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PHASE 1 END-TO-END TEST SUITE" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    results = {
        "DynamoDB Schema": test_dynamodb_schema(),
        "Topic Discovery Standalone": test_topic_discovery_standalone(),
        "Manager Agent Orchestration": test_manager_agent_workflow(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All Phase 1 tests passed!")
        print("✓ Agent Base Class working")
        print("✓ Manager Agent orchestration working")
        print("✓ Topic Discovery Agent working")
        print("✓ DynamoDB schema v2.0 working")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
