# Triggering the Blog Automation System

This document explains how to manually trigger the blog automation system and manage the automatic daily scheduling.

## Manual Triggering

### Run Multi-Agent Workflow (Recommended)

The multi-agent workflow includes quality validation and automatic rejection of low-quality articles.

```bash
aws lambda invoke \
  --function-name blog-multiagent-workflow \
  --payload '{}' \
  /tmp/test-multi.json \
  --profile blog-automation \
  --region us-east-1

# View the result
cat /tmp/test-multi.json
```

**Expected Output:**
```json
{
  "statusCode": 200,
  "body": "{\"success\": true, \"workflow_id\": \"workflow-1234567890\", \"status\": \"email_sent\", \"quality_score\": 87, \"validation_status\": \"APPROVED\", \"duration_seconds\": 95.23, \"topic\": \"Your Article Title\", \"word_count\": 2847, \"message\": \"Multi-agent workflow completed: APPROVED\"}"
}
```

### Run Single-Agent Workflow (Legacy)

The single-agent workflow is faster but lacks quality validation.

```bash
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{}' \
  /tmp/test-single.json \
  --profile blog-automation \
  --region us-east-1

# View the result
cat /tmp/test-single.json
```

## Understanding Workflow Results

### Quality Scores

The multi-agent system assigns quality scores from 0-100 based on:
- Factual Accuracy (25% weight)
- SEO Compliance (20% weight)
- Research Alignment (20% weight)
- Uniqueness (20% weight)
- Quality Assessment (15% weight)

### Validation Statuses

| Status | Score | Behavior |
|--------|-------|----------|
| **APPROVED** | ≥85% | Email sent, awaits your approval |
| **NEEDS_REVISION** | 70-84% | Email sent with warnings |
| **REJECTED** | <70% | No email sent, workflow ends |

### Workflow Statuses

After triggering, the workflow progresses through these states:

1. `initialized` - Workflow started
2. `discovering_topic` - Finding unique topic
3. `researching` - Gathering keyword data
4. `writing` - Generating article
5. `checking` - Validating quality
6. **Final states:**
   - `email_sent` - Approval email delivered (for approved/needs_revision)
   - `rejected` - Article quality too low, no email sent
   - `failed` - Error occurred

## Managing Automatic Scheduling

### Check Current Schedule Status

```bash
aws events describe-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation \
  --query '{Name:Name,State:State,ScheduleExpression:ScheduleExpression}' \
  --output json
```

**Output:**
```json
{
    "Name": "blog-multiagent-uk-11am-fallback",
    "State": "ENABLED",  // or "DISABLED"
    "ScheduleExpression": "cron(0 10 * * ? *)"  // 10:00 UTC = 11:00 UK time
}
```

### Disable Automatic Daily Runs

Stop the system from running automatically every day:

```bash
aws events disable-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation
```

Verify it's disabled:
```bash
aws events describe-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation \
  --query 'State' \
  --output text
# Should output: DISABLED
```

### Enable Automatic Daily Runs

Re-enable the daily automatic trigger:

```bash
aws events enable-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation
```

Verify it's enabled:
```bash
aws events describe-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation \
  --query 'State' \
  --output text
# Should output: ENABLED
```

### Permanently Delete the Schedule

If you want to completely remove the automatic schedule:

```bash
# Step 1: Remove the target Lambda function
aws events remove-targets \
  --rule blog-multiagent-uk-11am-fallback \
  --ids 1 \
  --region us-east-1 \
  --profile blog-automation

# Step 2: Delete the rule
aws events delete-rule \
  --name blog-multiagent-uk-11am-fallback \
  --region us-east-1 \
  --profile blog-automation
```

**Note:** The `./deploy.sh` script will recreate this schedule if you re-deploy.

## Monitoring Workflows

### View Recent Workflows

```bash
# List recent workflows
aws dynamodb scan \
  --table-name blog-workflow-state \
  --profile blog-automation \
  --region us-east-1 \
  --max-items 5 \
  --query 'Items[*].[workflow_id.S, status.S, article_title.S, created_at.S]' \
  --output table
```

### Get Specific Workflow Details

```bash
# Replace with your actual workflow_id
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"workflow-1234567890"}}' \
  --profile blog-automation \
  --region us-east-1
```

### View Live Logs

```bash
# Follow logs in real-time
aws logs tail /aws/lambda/blog-multiagent-workflow \
  --follow \
  --profile blog-automation \
  --region us-east-1
```

### Filter Logs by Workflow ID

```bash
# Replace with your actual workflow_id
aws logs filter-log-events \
  --log-group-name /aws/lambda/blog-multiagent-workflow \
  --filter-pattern "workflow-1234567890" \
  --profile blog-automation \
  --region us-east-1
```

## Approval Process

After a successful run with quality score ≥70%, you'll receive an email with:

1. **Quality Score Badge** - Visual indicator of article quality
2. **Validation Details** - Strengths and areas for improvement
3. **Article Preview** - First few paragraphs
4. **Metadata** - Word count, reading time, keywords, images
5. **Action Buttons:**
   - **APPROVE** - Publishes to Sanity CMS
   - **DECLINE** - Rejects the article

Click the appropriate button in the email to approve or decline the article.

## Troubleshooting

### No Email Received

**Check workflow status:**
```bash
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"YOUR_WORKFLOW_ID"}}' \
  --profile blog-automation \
  --region us-east-1 \
  --query 'Item.[status.S, agent_states.M.content_checker.M.output.M.status.S, agent_states.M.content_checker.M.output.M.quality_score.N]' \
  --output json
```

**Possible reasons:**
- Article quality score was <70% (status: `rejected`) - by design, no email sent
- Workflow still running (check logs)
- SES sender email not verified
- Error occurred (status: `failed`)

### Workflow Failed

**View error details:**
```bash
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"YOUR_WORKFLOW_ID"}}' \
  --profile blog-automation \
  --region us-east-1 \
  --query 'Item.agent_states.M.*.M.[status.S, error.S]' \
  --output json
```

**Check Lambda logs:**
```bash
aws logs tail /aws/lambda/blog-multiagent-workflow \
  --profile blog-automation \
  --region us-east-1 \
  --since 30m
```

### Multiple Workflows Created

If multiple workflows are created from a single trigger, check Lambda retry configuration:

```bash
# Verify MaximumRetryAttempts is 0
aws lambda get-function-event-invoke-config \
  --function-name blog-multiagent-workflow \
  --profile blog-automation \
  --region us-east-1 \
  --query 'MaximumRetryAttempts'
# Should output: 0

# Fix if needed
aws lambda put-function-event-invoke-config \
  --function-name blog-multiagent-workflow \
  --maximum-retry-attempts 0 \
  --profile blog-automation \
  --region us-east-1
```

## Quick Reference

| Task | Command |
|------|---------|
| Run manually | `aws lambda invoke --function-name blog-multiagent-workflow --payload '{}' /tmp/test.json --profile blog-automation --region us-east-1` |
| Disable daily runs | `aws events disable-rule --name blog-multiagent-uk-11am-fallback --region us-east-1 --profile blog-automation` |
| Enable daily runs | `aws events enable-rule --name blog-multiagent-uk-11am-fallback --region us-east-1 --profile blog-automation` |
| Check schedule status | `aws events describe-rule --name blog-multiagent-uk-11am-fallback --region us-east-1 --profile blog-automation` |
| View recent workflows | `aws dynamodb scan --table-name blog-workflow-state --profile blog-automation --region us-east-1 --max-items 5` |
| View live logs | `aws logs tail /aws/lambda/blog-multiagent-workflow --follow --profile blog-automation --region us-east-1` |

## Current Status

- **Daily Schedule:** DISABLED (as of current configuration)
- **Manual Trigger:** AVAILABLE
- **Recommended Usage:** Run manually as needed

---

**Last Updated:** 2025-11-09
