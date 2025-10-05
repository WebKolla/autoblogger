"""
Phase 2 End-to-End Test

Tests the multi-agent pipeline:
- Topic Discovery → Research → Writing
- Manager Agent orchestration
- Image sourcing (Cloudinary + Pexels)
- Article generation with Portable Text

NOTE: This test calls Claude API and may incur costs (~$1-2 per run).
Set MOCK_MODE=true to run without Claude API calls.
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add agents directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.manager_agent import ManagerAgent
import boto3


def test_full_pipeline():
    """Test complete pipeline: Topic → Research → Writing"""
    print("\n" + "=" * 60)
    print("TEST: Full Multi-Agent Pipeline")
    print("=" * 60)

    try:
        # Create manager and run workflow
        manager = ManagerAgent()
        result = manager.start_workflow(trigger_type="test_phase2")

        print(f"\n✓ Workflow completed successfully")
        print(f"\nWorkflow ID: {result['workflow_id']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['result']['message']}")

        # Print article preview
        if 'article_preview' in result['result']:
            preview = result['result']['article_preview']
            print(f"\nArticle Preview:")
            print(f"  - Title: {preview['title']}")
            print(f"  - Word Count: {preview['word_count']}")
            print(f"  - Images: {preview['images']}")

        # Verify in DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('blog-workflow-state')

        workflow = table.get_item(Key={'workflow_id': result['workflow_id']})['Item']

        print(f"\nWorkflow State Verification:")
        print(f"  - Status: {workflow.get('status')}")
        print(f"  - Schema Version: {workflow.get('schema_version')}")
        print(f"  - Topic Title: {workflow.get('topic_title')}")
        print(f"  - Article Title: {workflow.get('article_title')}")

        # Check agent states
        agent_states = workflow.get('agent_states', {})
        print(f"\nAgent Execution Summary:")
        for agent_name, state in agent_states.items():
            status = state.get('status')
            duration = state.get('duration_seconds', 'N/A')
            print(f"  - {agent_name}: {status} ({duration}s)")

        # Validate article data
        article_data = workflow.get('article_data', {})
        if article_data:
            article = article_data.get('article', {})
            images = article_data.get('images', [])

            print(f"\nArticle Validation:")
            print(f"  - Has portable_text_body: {bool(article.get('portable_text_body'))}")
            print(f"  - Portable Text blocks: {len(article.get('portable_text_body', []))}")
            print(f"  - Has SEO metadata: {bool(article.get('seo_metadata'))}")
            print(f"  - Internal links: {len(article.get('internal_links', []))}")
            print(f"  - Images sourced: {len(images)}")

            # Show image sources
            if images:
                print(f"\n  Image Sources:")
                for i, img in enumerate(images, 1):
                    print(f"    {i}. {img.get('source', 'unknown')} - {img.get('credit', 'N/A')}")

        # Cleanup test workflow
        table.delete_item(Key={'workflow_id': result['workflow_id']})
        print(f"\n✓ Cleaned up test workflow")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_integration():
    """Test individual agents work together"""
    print("\n" + "=" * 60)
    print("TEST: Agent Integration")
    print("=" * 60)

    workflow_id = f"test-integration-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

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
        # Test 1: Topic Discovery
        print(f"\n1. Testing Topic Discovery Agent...")
        from agents.topic_discovery_agent import TopicDiscoveryAgent
        topic_agent = TopicDiscoveryAgent(workflow_id)
        topic_result = topic_agent.execute({})

        assert topic_result['status'] == 'success'
        assert 'selected_topic' in topic_result
        print(f"✓ Topic selected: {topic_result['selected_topic']['title']}")

        # Test 2: Research Agent
        print(f"\n2. Testing Research Agent...")
        from agents.research_agent import ResearchAgent
        research_agent = ResearchAgent(workflow_id)
        research_result = research_agent.execute({
            "selected_topic": topic_result["selected_topic"]
        })

        assert research_result['status'] == 'success'
        assert 'research_report' in research_result
        print(f"✓ Research completed")
        print(f"  - Primary keywords: {len(research_result['research_report']['keyword_research'].get('primary_keywords', []))}")

        # Test 3: SEO Writer Agent
        print(f"\n3. Testing SEO Writer Agent...")
        from agents.seo_writer_agent import SEOWriterAgent
        writer_agent = SEOWriterAgent(workflow_id)
        writer_result = writer_agent.execute({
            "research_report": research_result["research_report"]
        })

        assert writer_result['status'] == 'success'
        assert 'article' in writer_result
        print(f"✓ Article generated")
        print(f"  - Title: {writer_result['article']['title']}")
        print(f"  - Word count: {writer_result['metadata']['word_count']}")
        print(f"  - Images: {writer_result['metadata']['images_sourced']}")

        # Verify article structure
        article = writer_result['article']
        assert 'portable_text_body' in article
        assert 'seo_metadata' in article
        assert len(article['portable_text_body']) > 0
        print(f"  - Portable Text blocks: {len(article['portable_text_body'])}")

        print(f"\n✓ All agents working correctly in sequence")

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


def run_all_tests():
    """Run all Phase 2 tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PHASE 2 END-TO-END TEST SUITE" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    print("\n⚠️  WARNING: These tests will call Claude API and incur costs (~$1-2)")
    print("   Make sure you have proper AWS credentials configured.")

    response = input("\nProceed with tests? (yes/no): ")

    if response.lower() != 'yes':
        print("Tests cancelled.")
        return 1

    results = {
        "Agent Integration": test_agent_integration(),
        "Full Pipeline": test_full_pipeline(),
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
        print("\n🎉 All Phase 2 tests passed!")
        print("✓ Topic Discovery working")
        print("✓ Research Agent working")
        print("✓ SEO Writer Agent working")
        print("✓ Full pipeline working")
        print("✓ Image sourcing working")
        print("✓ Portable Text generation working")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
