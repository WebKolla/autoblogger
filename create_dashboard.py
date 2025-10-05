#!/usr/bin/env python3
"""
Create CloudWatch Dashboard for Blog Automation System
"""

import boto3
import json
import os

def create_cloudwatch_dashboard():
    """Create CloudWatch dashboard with key metrics"""

    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

    dashboard_body = {
        "widgets": [
            # Agent Execution Times
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentExecutionTime", {"stat": "Average", "label": "Avg Execution Time"}],
                        ["...", {"stat": "Maximum", "label": "Max Execution Time"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Agent Execution Times (All Agents)",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Seconds"
                        }
                    }
                }
            },

            # Agent Execution Times by Agent
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentExecutionTime", "AgentName", "topic_discovery", {"stat": "Average"}],
                        ["BlogAutomation", "AgentExecutionTime", "AgentName", "research", {"stat": "Average"}],
                        ["BlogAutomation", "AgentExecutionTime", "AgentName", "seo_writer", {"stat": "Average"}],
                        ["BlogAutomation", "AgentExecutionTime", "AgentName", "content_checker", {"stat": "Average"}],
                        ["BlogAutomation", "AgentExecutionTime", "AgentName", "manager", {"stat": "Average"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Execution Time by Agent",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Seconds"
                        }
                    }
                }
            },

            # Agent Execution Success Rate
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentExecutionCount", "Success", "True", {"stat": "Sum", "label": "Success", "color": "#2ca02c"}],
                        ["BlogAutomation", "AgentExecutionCount", "Success", "False", {"stat": "Sum", "label": "Failure", "color": "#d62728"}]
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": "us-east-1",
                    "title": "Agent Execution Success/Failure",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },

            # Agent Error Rates
            {
                "type": "metric",
                "x": 12,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentErrors", {"stat": "Sum", "label": "Total Errors"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Agent Errors Over Time",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Error Count"
                        }
                    }
                }
            },

            # Quality Scores
            {
                "type": "metric",
                "x": 0,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "ArticleQualityScore", {"stat": "Average", "label": "Avg Quality Score"}],
                        ["...", {"stat": "Minimum", "label": "Min Quality Score"}],
                        ["...", {"stat": "Maximum", "label": "Max Quality Score"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Article Quality Scores",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Score (0-1)",
                            "min": 0,
                            "max": 1
                        }
                    }
                }
            },

            # Validation Status Distribution
            {
                "type": "metric",
                "x": 12,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "ArticleValidationCount", "Status", "APPROVED", {"stat": "Sum", "label": "Approved", "color": "#2ca02c"}],
                        ["BlogAutomation", "ArticleValidationCount", "Status", "NEEDS_REVISION", {"stat": "Sum", "label": "Needs Revision", "color": "#ff7f0e"}],
                        ["BlogAutomation", "ArticleValidationCount", "Status", "REJECTED", {"stat": "Sum", "label": "Rejected", "color": "#d62728"}]
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": "us-east-1",
                    "title": "Article Validation Status",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },

            # Cost Tracking
            {
                "type": "metric",
                "x": 0,
                "y": 18,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentCost", {"stat": "Sum", "label": "Total Cost"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Cumulative Cost (USD)",
                    "period": 86400,  # Daily
                    "yAxis": {
                        "left": {
                            "label": "USD"
                        }
                    }
                }
            },

            # Cost by Agent
            {
                "type": "metric",
                "x": 12,
                "y": 18,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "AgentCost", "AgentName", "research", {"stat": "Sum", "label": "Research Agent"}],
                        ["BlogAutomation", "AgentCost", "AgentName", "seo_writer", {"stat": "Sum", "label": "Writer Agent"}]
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": "us-east-1",
                    "title": "Cost by Agent (USD)",
                    "period": 86400,  # Daily
                    "yAxis": {
                        "left": {
                            "label": "USD"
                        }
                    }
                }
            },

            # Workflow Duration
            {
                "type": "metric",
                "x": 0,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "WorkflowDuration", {"stat": "Average", "label": "Avg Duration"}],
                        ["...", {"stat": "Maximum", "label": "Max Duration"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Workflow Duration",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Seconds"
                        }
                    }
                }
            },

            # Workflow Success Rate
            {
                "type": "metric",
                "x": 12,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["BlogAutomation", "WorkflowCount", {"stat": "Sum", "label": "Total Workflows"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Workflow Count",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            }
        ]
    }

    try:
        # Create or update dashboard
        cloudwatch.put_dashboard(
            DashboardName='BlogAutomation-Dashboard',
            DashboardBody=json.dumps(dashboard_body)
        )
        print("✅ CloudWatch dashboard created successfully!")
        print("\nView at: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=BlogAutomation-Dashboard")

        # Create alarms
        create_alarms(cloudwatch)

    except Exception as e:
        print(f"❌ Error creating dashboard: {str(e)}")
        raise


def create_alarms(cloudwatch):
    """Create CloudWatch alarms for critical metrics"""

    alarms = [
        {
            'AlarmName': 'BlogAutomation-HighErrorRate',
            'MetricName': 'AgentErrors',
            'Namespace': 'BlogAutomation',
            'Statistic': 'Sum',
            'Period': 300,  # 5 minutes
            'EvaluationPeriods': 1,
            'Threshold': 5.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'AlarmDescription': 'Alert when agent error count exceeds 5 in 5 minutes',
            'TreatMissingData': 'notBreaching'
        },
        {
            'AlarmName': 'BlogAutomation-LowQualityScore',
            'MetricName': 'ArticleQualityScore',
            'Namespace': 'BlogAutomation',
            'Statistic': 'Average',
            'Period': 3600,  # 1 hour
            'EvaluationPeriods': 1,
            'Threshold': 0.5,
            'ComparisonOperator': 'LessThanThreshold',
            'AlarmDescription': 'Alert when average quality score drops below 0.5',
            'TreatMissingData': 'notBreaching'
        },
        {
            'AlarmName': 'BlogAutomation-HighCost',
            'MetricName': 'AgentCost',
            'Namespace': 'BlogAutomation',
            'Statistic': 'Sum',
            'Period': 86400,  # 1 day
            'EvaluationPeriods': 1,
            'Threshold': 5.0,  # $5/day = $150/month
            'ComparisonOperator': 'GreaterThanThreshold',
            'AlarmDescription': 'Alert when daily cost exceeds $5',
            'TreatMissingData': 'notBreaching'
        },
        {
            'AlarmName': 'BlogAutomation-SlowWorkflow',
            'MetricName': 'WorkflowDuration',
            'Namespace': 'BlogAutomation',
            'Statistic': 'Average',
            'Period': 3600,
            'EvaluationPeriods': 1,
            'Threshold': 600.0,  # 10 minutes
            'ComparisonOperator': 'GreaterThanThreshold',
            'AlarmDescription': 'Alert when workflow takes longer than 10 minutes',
            'TreatMissingData': 'notBreaching'
        }
    ]

    for alarm in alarms:
        try:
            cloudwatch.put_metric_alarm(**alarm)
            print(f"✅ Created alarm: {alarm['AlarmName']}")
        except Exception as e:
            print(f"⚠️  Failed to create alarm {alarm['AlarmName']}: {str(e)}")


if __name__ == "__main__":
    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'blog-automation'

    print("🚀 Creating CloudWatch Dashboard and Alarms...")
    print("")

    create_cloudwatch_dashboard()

    print("")
    print("📊 Dashboard Features:")
    print("  ✅ Agent execution times (overall and by agent)")
    print("  ✅ Success/failure rates")
    print("  ✅ Error tracking")
    print("  ✅ Quality score trends")
    print("  ✅ Validation status distribution")
    print("  ✅ Cost tracking (total and by agent)")
    print("  ✅ Workflow duration and count")
    print("")
    print("🔔 Alarms Created:")
    print("  ✅ High error rate (>5 errors in 5 min)")
    print("  ✅ Low quality score (<0.5 average)")
    print("  ✅ High cost (>$5/day)")
    print("  ✅ Slow workflow (>10 minutes)")
    print("")
