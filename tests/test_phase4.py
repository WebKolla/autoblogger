#!/usr/bin/env python3
"""
Phase 4 Test Suite - Monitoring & Optimization

Tests:
1. Metrics Collection
2. CloudWatch Integration
3. Retry Logic
4. Cost Tracking
5. Performance Monitoring
"""

import os
import sys
import time
import boto3
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.metrics import MetricsCollector, CostTracker, PerformanceTimer
from agents.base_agent import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing"""

    def __init__(self, workflow_id: str):
        super().__init__(workflow_id, "test_agent")

    def execute(self, input_data: dict) -> dict:
        return {"status": "success", "test": True}


def test_metrics_collection():
    """Test 1: Metrics Collection"""
    print("\n" + "=" * 60)
    print("TEST 1: METRICS COLLECTION")
    print("=" * 60)

    try:
        metrics = MetricsCollector(namespace="BlogAutomationTest")

        # Test agent execution metrics
        print("\n✓ Recording agent execution metric...")
        metrics.record_agent_execution(
            agent_name="test_agent",
            duration_seconds=5.5,
            success=True,
            workflow_id="test-workflow-001"
        )

        # Test error metrics
        print("✓ Recording error metric...")
        metrics.record_error(
            agent_name="test_agent",
            error_type="TestError",
            workflow_id="test-workflow-001"
        )

        # Test quality metrics
        print("✓ Recording quality score...")
        metrics.record_quality_score(
            workflow_id="test-workflow-001",
            quality_score=0.85,
            validation_status="APPROVED"
        )

        # Test cost metrics
        print("✓ Recording cost metric...")
        metrics.record_cost(
            workflow_id="test-workflow-001",
            agent_name="test_agent",
            cost_usd=0.50,
            operation="bedrock_call"
        )

        # Test workflow metrics
        print("✓ Recording workflow metrics...")
        metrics.record_workflow_metrics(
            workflow_id="test-workflow-001",
            total_duration=120.5,
            status="completed",
            agent_count=4
        )

        print("\n✅ TEST 1 PASSED: All metrics recorded successfully")
        print("\nNote: Check CloudWatch console to verify metrics:")
        print("https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2:graph=~();namespace=BlogAutomationTest")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_cost_tracking():
    """Test 2: Cost Tracking"""
    print("\n" + "=" * 60)
    print("TEST 2: COST TRACKING")
    print("=" * 60)

    try:
        # Test Bedrock cost calculation
        print("\n✓ Testing Bedrock cost calculation...")
        bedrock_cost = CostTracker.calculate_bedrock_cost(
            model='claude-3-sonnet',
            input_tokens=2000,
            output_tokens=3000
        )
        print(f"  Bedrock cost (2K input, 3K output): ${bedrock_cost:.4f}")
        assert bedrock_cost > 0, "Bedrock cost should be positive"

        # Test DynamoDB cost calculation
        print("✓ Testing DynamoDB cost calculation...")
        dynamodb_cost = CostTracker.calculate_dynamodb_cost(
            writes=50,
            reads=100
        )
        print(f"  DynamoDB cost (50 writes, 100 reads): ${dynamodb_cost:.6f}")
        assert dynamodb_cost > 0, "DynamoDB cost should be positive"

        # Test monthly cost estimation
        print("✓ Testing monthly cost estimation...")
        monthly_costs = CostTracker.estimate_monthly_cost(articles_per_month=30)
        print(f"\n  Monthly Cost Breakdown (30 articles):")
        print(f"    Bedrock: ${monthly_costs['bedrock']:.2f}")
        print(f"    DynamoDB: ${monthly_costs['dynamodb']:.2f}")
        print(f"    Lambda: ${monthly_costs['lambda']:.2f}")
        print(f"    SES: ${monthly_costs['ses']:.2f}")
        print(f"    TOTAL: ${monthly_costs['total']:.2f}")
        print(f"    Per Article: ${monthly_costs['per_article']:.2f}")

        assert monthly_costs['total'] < 100, "Monthly cost should be under $100"
        assert monthly_costs['total'] > 0, "Monthly cost should be positive"

        print("\n✅ TEST 2 PASSED: Cost tracking working correctly")
        print(f"\n💰 Estimated monthly cost: ${monthly_costs['total']:.2f} (well under $100 budget)")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_timer():
    """Test 3: Performance Timer"""
    print("\n" + "=" * 60)
    print("TEST 3: PERFORMANCE TIMER")
    print("=" * 60)

    try:
        print("\n✓ Testing performance timer (sleeping 1 second)...")

        with PerformanceTimer("test_operation") as timer:
            time.sleep(1.0)

        assert timer.duration is not None, "Duration should be set"
        assert 0.9 < timer.duration < 1.2, f"Duration should be ~1s, got {timer.duration:.2f}s"

        print(f"  Measured duration: {timer.duration:.2f}s")
        print("\n✅ TEST 3 PASSED: Performance timer working correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_retry_logic():
    """Test 4: Retry Logic with Exponential Backoff"""
    print("\n" + "=" * 60)
    print("TEST 4: RETRY LOGIC")
    print("=" * 60)

    try:
        workflow_id = f"test-retry-{int(time.time())}"
        agent = MockAgent(workflow_id)

        # Test 1: Successful operation (no retries needed)
        print("\n✓ Testing successful operation (no retries)...")
        call_count = 0

        def success_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = agent.retry_with_backoff(success_operation, max_retries=3)
        assert result == "success", "Should return success"
        assert call_count == 1, f"Should only call once, called {call_count} times"
        print(f"  ✓ Operation succeeded on first attempt")

        # Test 2: Transient failure then success
        print("\n✓ Testing transient failure with retry...")
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary connection error")
            return "success after retries"

        start_time = time.time()
        result = agent.retry_with_backoff(fail_then_succeed, max_retries=3, base_delay=0.5)
        duration = time.time() - start_time

        assert result == "success after retries", "Should eventually succeed"
        assert call_count == 3, f"Should call 3 times, called {call_count} times"
        assert duration > 1.0, "Should have delays between retries"
        print(f"  ✓ Operation succeeded after {call_count - 1} retries in {duration:.2f}s")

        # Test 3: Permanent failure (exhausts retries)
        print("\n✓ Testing permanent failure (exhausts retries)...")
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        try:
            agent.retry_with_backoff(always_fail, max_retries=2, base_delay=0.1)
            assert False, "Should have raised exception"
        except ValueError as e:
            assert call_count == 3, f"Should call 3 times (1 + 2 retries), called {call_count} times"
            print(f"  ✓ Correctly exhausted retries after {call_count} attempts")

        # Test 4: Transient error detection
        print("\n✓ Testing transient error detection...")
        transient_errors = [
            ConnectionError("Connection timeout"),
            TimeoutError("Request timeout"),
            Exception("Throttling limit exceeded"),
            Exception("503 Service Unavailable")
        ]

        for error in transient_errors:
            assert agent.is_transient_error(error), f"{type(error).__name__} should be transient"

        non_transient_errors = [
            ValueError("Invalid input"),
            KeyError("Missing key"),
            Exception("Validation failed")
        ]

        for error in non_transient_errors:
            assert not agent.is_transient_error(error), f"{type(error).__name__} should not be transient"

        print(f"  ✓ Correctly identified transient vs non-transient errors")

        print("\n✅ TEST 4 PASSED: Retry logic working correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_base_agent_metrics():
    """Test 5: BaseAgent Metrics Integration"""
    print("\n" + "=" * 60)
    print("TEST 5: BASE AGENT METRICS INTEGRATION")
    print("=" * 60)

    try:
        workflow_id = f"test-agent-metrics-{int(time.time())}"

        print("\n✓ Creating mock agent...")
        agent = MockAgent(workflow_id)

        # Initialize workflow first
        print("✓ Initializing workflow in DynamoDB...")
        from datetime import datetime, timezone
        agent.workflow_table.put_item(Item={
            "workflow_id": workflow_id,
            "status": "initialized",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agent_states": {},
            "schema_version": "2.0"
        })

        # Test agent state with metrics
        print("✓ Testing agent state update (should record metrics)...")
        agent.update_agent_state(
            status="running",
            metadata={"test": "data"}
        )

        # Wait a moment then complete
        time.sleep(0.5)
        agent.update_agent_state(
            status="completed",
            output={"result": "success"},
            metadata={"score": 0.95}
        )

        # Verify workflow state in DynamoDB
        print("✓ Verifying workflow state in DynamoDB...")
        response = agent.workflow_table.get_item(Key={'workflow_id': workflow_id})

        assert 'Item' in response, "Workflow should exist in DynamoDB"
        item = response['Item']

        assert 'agent_states' in item, "Should have agent_states"
        assert 'test_agent' in item['agent_states'], "Should have test_agent state"

        agent_state = item['agent_states']['test_agent']
        assert agent_state['status'] == 'completed', "Agent should be completed"
        assert 'duration_seconds' in agent_state, "Should have duration"

        print(f"  ✓ Agent execution time: {agent_state['duration_seconds']}s")

        # Test with errors
        print("\n✓ Testing agent error handling (should record error metrics)...")
        error_workflow_id = f"test-agent-error-{int(time.time())}"
        error_agent = MockAgent(error_workflow_id)

        # Initialize error workflow
        error_agent.workflow_table.put_item(Item={
            "workflow_id": error_workflow_id,
            "status": "initialized",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agent_states": {},
            "schema_version": "2.0"
        })

        error_agent.update_agent_state(
            status="failed",
            error="TestError: Simulated failure"
        )

        print("  ✓ Error recorded successfully")

        print("\n✅ TEST 5 PASSED: BaseAgent metrics integration working")
        return True

    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 4 tests"""
    print("\n" + "=" * 60)
    print("PHASE 4 TEST SUITE - MONITORING & OPTIMIZATION")
    print("=" * 60)
    print("\nTesting:")
    print("  1. Metrics Collection")
    print("  2. Cost Tracking")
    print("  3. Performance Timer")
    print("  4. Retry Logic")
    print("  5. BaseAgent Metrics Integration")

    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'blog-automation'

    results = []

    # Run all tests
    results.append(("Metrics Collection", test_metrics_collection()))
    results.append(("Cost Tracking", test_cost_tracking()))
    results.append(("Performance Timer", test_performance_timer()))
    results.append(("Retry Logic", test_retry_logic()))
    results.append(("BaseAgent Metrics", test_base_agent_metrics()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 ALL PHASE 4 TESTS PASSED!")
        print("\n✅ Phase 4 Complete:")
        print("  • CloudWatch metrics collection")
        print("  • Cost tracking and estimation")
        print("  • Performance monitoring")
        print("  • Retry logic with exponential backoff")
        print("  • Error detection and handling")
        print("\n📊 Next Steps:")
        print("  1. Run create_dashboard.py to set up CloudWatch dashboard")
        print("  2. Deploy updated code with ./deploy.sh")
        print("  3. Monitor metrics in CloudWatch console")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
