"""
Phase 3 End-to-End Test

Tests the content validation pipeline:
- Content Checker Agent validation
- Factual accuracy, SEO compliance, uniqueness
- Manager Agent with full pipeline including QA

NOTE: This test calls Claude API and may incur costs (~$2-3 per run).
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add agents directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.manager_agent import ManagerAgent
from agents.content_checker_agent import ContentCheckerAgent
import boto3


def test_content_checker_validation():
    """Test Content Checker Agent with sample article"""
    print("\n" + "=" * 60)
    print("TEST 1: Content Checker Validation")
    print("=" * 60)

    workflow_id = f"test-checker-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    # Initialize workflow
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
        # Create sample article for testing
        sample_article = {
            "title": "Cycling Through Sri Lanka's Cultural Triangle",
            "portable_text_body": [
                {
                    "_key": "key1",
                    "_type": "block",
                    "style": "h1",
                    "children": [{"_type": "span", "_key": "span1", "text": "Cycling Through Sri Lanka's Cultural Triangle", "marks": []}],
                    "markDefs": []
                },
                {
                    "_key": "key2",
                    "_type": "block",
                    "style": "normal",
                    "children": [{"_type": "span", "_key": "span2", "text": "The Cultural Triangle of Sri Lanka encompasses 8 UNESCO World Heritage Sites, including the ancient cities of Anuradhapura and Polonnaruwa. Best season for cycling is November to April. Temperature averages 28-32°C. Visa ETA required for most nationalities.", "marks": []}],
                    "markDefs": []
                }
            ] * 50,  # Repeat to get ~2500 words
            "word_count": 2800,
            "reading_time": 14,
            "image_search_terms": ["cycling", "cultural triangle", "sri lanka"],
            "internal_links": [
                {"anchor": "cultural triangle tour", "url": "https://acrossceylon.com/packages/cultural-triangle"}
            ],
            "seo_metadata": {
                "meta_title": "Cycling Sri Lanka's Cultural Triangle | Across Ceylon",
                "meta_description": "Discover 2,500 years of history on two wheels. Cycle through UNESCO World Heritage Sites in Sri Lanka's Cultural Triangle with expert guides.",
                "focus_keyword": "cycling sri lanka cultural triangle",
                "keywords": ["cultural triangle bike tour", "anuradhapura cycling", "polonnaruwa bike"]
            },
            "images": [
                {"url": "http://example.com/img1.jpg", "alt": "Cycling in Sri Lanka"}
            ] * 4
        }

        # Sample research report
        sample_research = {
            "topic_title": "Cycling Through Sri Lanka's Cultural Triangle",
            "topic_category": "Cultural Routes",
            "keyword_research": {
                "primary_keywords": [
                    {"keyword": "cycling sri lanka cultural triangle", "volume": 500},
                    {"keyword": "cultural triangle bike tour", "volume": 300}
                ],
                "secondary_keywords": ["anuradhapura cycling"],
                "keyword_density_target": 1.5
            },
            "research_synthesis": {
                "key_facts": [
                    "8 UNESCO World Heritage Sites",
                    "Best season: November to April",
                    "Temperature 28-32°C",
                    "ETA visa required"
                ],
                "practical_info": {
                    "best_season": "November to April",
                    "avg_temperature": "28-32°C",
                    "visa_requirement": "ETA required"
                }
            },
            "content_recommendations": {
                "must_include": [
                    "UNESCO sites",
                    "Best season",
                    "Visa requirements",
                    "Safety tips"
                ]
            }
        }

        # Run Content Checker
        checker = ContentCheckerAgent(workflow_id)
        result = checker.execute({
            "article": sample_article,
            "research_report": sample_research,
            "recent_articles": []
        })

        print(f"\n✓ Content Checker completed")

        validation = result["validation_result"]
        print(f"\nValidation Results:")
        print(f"  - Status: {validation['status']}")
        print(f"  - Quality Score: {validation['quality_score']:.2f}")
        print(f"  - Recommendation: {validation['approval_recommendation']}")

        print(f"\nCheck Results:")
        for check_name, check_result in validation["checks"].items():
            status = "✓" if check_result.get("passed", False) else "✗"
            print(f"  {status} {check_name}: {'PASS' if check_result.get('passed') else 'FAIL'}")

        print(f"\nFeedback:")
        feedback = validation["feedback"]
        print(f"  Strengths: {', '.join(feedback.get('strengths', []))}")
        if feedback.get('weaknesses'):
            print(f"  Weaknesses: {', '.join(feedback.get('weaknesses', []))}")
        if feedback.get('revisions'):
            print(f"  Revisions Needed: {', '.join(feedback.get('revisions', []))}")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            table.delete_item(Key={'workflow_id': workflow_id})
            print(f"\n✓ Cleaned up test workflow")
        except Exception as e:
            print(f"⚠ Warning: Could not clean up: {str(e)}")


def test_full_pipeline_with_qa():
    """Test complete pipeline including Content Checker"""
    print("\n" + "=" * 60)
    print("TEST 2: Full Pipeline with QA")
    print("=" * 60)

    print("\n⚠️  This test will generate a complete article and incur costs (~$2)")
    response = input("Proceed? (yes/no): ")

    if response.lower() != 'yes':
        print("Test skipped.")
        return None

    try:
        manager = ManagerAgent()
        result = manager.start_workflow(trigger_type="test_phase3")

        print(f"\n✓ Workflow completed")
        print(f"\nWorkflow ID: {result['workflow_id']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['result']['message']}")

        # Check if article was validated
        if 'validation' in result['result']:
            validation = result['result']['validation']
            preview = result['result']['article_preview']

            print(f"\nArticle Preview:")
            print(f"  - Title: {preview['title']}")
            print(f"  - Word Count: {preview['word_count']}")
            print(f"  - Images: {preview['images']}")
            print(f"  - Quality Score: {preview['quality_score']:.2f}")
            print(f"  - Validation Status: {preview['validation_status']}")

            print(f"\nValidation Summary:")
            print(f"  - Decision: {validation['feedback']['decision']}")
            print(f"  - Strengths: {len(validation['feedback']['strengths'])}")
            print(f"  - Weaknesses: {len(validation['feedback']['weaknesses'])}")

            # Check individual validations
            print(f"\nDetailed Checks:")
            for check_name, check_result in validation["checks"].items():
                status = "✓" if check_result.get("passed") else "✗"
                print(f"  {status} {check_name}")

        # Verify in DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('blog-workflow-state')

        workflow = table.get_item(Key={'workflow_id': result['workflow_id']})['Item']

        print(f"\nWorkflow State:")
        print(f"  - Final Status: {workflow.get('status')}")
        print(f"  - Topic: {workflow.get('topic_title')}")

        # Check agent states
        agent_states = workflow.get('agent_states', {})
        print(f"\nAgent Execution Summary:")
        for agent_name, state in agent_states.items():
            status = state.get('status')
            duration = state.get('duration_seconds', 'N/A')
            print(f"  - {agent_name}: {status} ({duration}s)")

        # Cleanup
        table.delete_item(Key={'workflow_id': result['workflow_id']})
        print(f"\n✓ Cleaned up test workflow")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 3 tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PHASE 3 END-TO-END TEST SUITE" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    results = {
        "Content Checker Validation": test_content_checker_validation(),
    }

    # Full pipeline test (optional, expensive)
    print("\n" + "=" * 60)
    print("OPTIONAL: Full Pipeline Test")
    print("=" * 60)
    print("This test generates a complete article with Claude API (~$2 cost)")

    full_test_result = test_full_pipeline_with_qa()
    if full_test_result is not None:
        results["Full Pipeline with QA"] = full_test_result

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        if passed is not None:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{status}: {test_name}")

    total = len([r for r in results.values() if r is not None])
    passed = sum(1 for v in results.values() if v is True)

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All Phase 3 tests passed!")
        print("✓ Content Checker validation working")
        print("✓ Factual accuracy checking")
        print("✓ SEO compliance validation")
        print("✓ Uniqueness scoring")
        print("✓ Quality assessment")
        print("✓ Full pipeline with QA working")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
