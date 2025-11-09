# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent AWS Lambda system for automated blog content generation for acrossceylon.com. The system uses Claude 3 Sonnet via AWS Bedrock to generate SEO-optimized cycling tourism articles with automated quality validation and email approval workflow.

**Production Status:** Multi-agent workflow is the recommended production system (includes quality validation and automatic rejection of low-quality content).

## Common Commands

### Deployment

```bash
# Deploy all Lambda functions and infrastructure
./deploy.sh

# Deploy creates/updates:
# - 5 Lambda functions (2 single-agent, 2 multi-agent, 1 approval handler)
# - DynamoDB table: blog-workflow-state
# - API Gateway for approval endpoint
# - EventBridge schedule (11:00 Europe/London daily)
# - IAM roles with Bedrock, DynamoDB, SES, Secrets Manager permissions
```

### Testing

```bash
# Trigger multi-agent workflow (recommended - with quality validation)
aws lambda invoke \
  --function-name blog-multiagent-workflow \
  --payload '{}' \
  /tmp/test-multi.json \
  --profile blog-automation \
  --region us-east-1 && cat /tmp/test-multi.json

# Trigger single-agent workflow (faster, no quality validation)
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{}' \
  /tmp/test-single.json \
  --profile blog-automation \
  --region us-east-1 && cat /tmp/test-single.json
```

### Monitoring

```bash
# View multi-agent logs in real-time
aws logs tail /aws/lambda/blog-multiagent-workflow \
  --follow \
  --profile blog-automation \
  --region us-east-1

# View single-agent logs
aws logs tail /aws/lambda/blog-manual-trigger \
  --follow \
  --profile blog-automation \
  --region us-east-1

# Filter logs by workflow ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/blog-multiagent-workflow \
  --filter-pattern "workflow-1234567890" \
  --profile blog-automation \
  --region us-east-1

# Check workflow state in DynamoDB
aws dynamodb scan \
  --table-name blog-workflow-state \
  --profile blog-automation \
  --region us-east-1 \
  --max-items 5

# Get specific workflow details
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"workflow-1234567890"}}' \
  --profile blog-automation \
  --region us-east-1
```

### Updating Lambda Functions

```bash
# Package and update multi-agent functions
zip -q -r multi_agent.zip multi_agent_handler.py agents/
for func in blog-multiagent-workflow blog-multiagent-daily; do
  aws lambda update-function-code \
    --function-name $func \
    --zip-file fileb://multi_agent.zip \
    --profile blog-automation \
    --region us-east-1
done

# Package and update single-agent functions
zip -q blog_agent.zip blog_agent.py
for func in blog-daily-workflow blog-manual-trigger blog-approval-handler; do
  aws lambda update-function-code \
    --function-name $func \
    --zip-file fileb://blog_agent.zip \
    --profile blog-automation \
    --region us-east-1
done
```

## Architecture

### Multi-Agent System (Recommended)

The multi-agent system uses a Manager Agent pattern to coordinate 4 specialized agents:

**Manager Agent** (`agents/manager_agent.py`)
- Orchestrates the entire workflow
- Manages DynamoDB workflow state transitions
- Sends approval emails via SES with quality reports
- Handles error recovery and retries

**Agent Pipeline:**
1. **Topic Discovery Agent** (`agents/topic_discovery_agent.py`)
   - Selects unique topics from 24 predefined SEO-optimized topics
   - Checks against recent DynamoDB articles to avoid duplicates
   - Topics span: Cultural Routes, Geographic Regions, Experience Types, E-Bike Adventures

2. **Research Agent** (`agents/research_agent.py`)
   - Google Keyword Planner API integration for keyword research
   - Claude-powered content strategy generation
   - Produces research report with must-include items

3. **SEO Writer Agent** (`agents/seo_writer_agent.py`)
   - Generates 2,500-3,500 word articles using Claude 3 Sonnet
   - Cloudinary (priority) + Pexels (fallback) image sourcing
   - Outputs Sanity Portable Text JSON format
   - Includes SEO metadata (title, description, keywords)

4. **Content Checker Agent** (`agents/content_checker_agent.py`)
   - **Critical QA Gate** - Pure Python validation (no AI)
   - Generates quality score 0-100 based on 5 checks:
     - Factual Accuracy (25% weight) - verifies facts against research
     - SEO Compliance (20% weight) - keyword density, meta tags, links, images
     - Research Alignment (20% weight) - must-include coverage
     - Uniqueness (20% weight) - Jaccard similarity with recent 10 articles
     - Quality Assessment (15% weight) - word count, readability
   - **Validation Outcomes:**
     - APPROVED (≥85%): Email sent, awaits approval
     - NEEDS_REVISION (70-84%): Email sent with warnings
     - REJECTED (<70%): No email sent, workflow ends

**Key Files:**
- `multi_agent_handler.py` - Lambda handler, invokes ManagerAgent
- `agents/base_agent.py` - Abstract base class with DynamoDB, Bedrock client, logging, metrics
- `agents/metrics.py` - CloudWatch metrics tracking (execution time, costs, errors)

### Single-Agent System (Legacy)

Simpler, faster system in `blog_agent.py` that combines all steps into one agent without quality validation. Still production-ready but lacks automated QA.

### State Management

**DynamoDB Table:** `blog-workflow-state`
- Primary Key: `workflow_id` (e.g., "workflow-1734567890000")
- Schema v2.0 structure:
  ```
  {
    workflow_id: string
    status: string (initialized|discovering_topic|researching|writing|checking|approved|rejected|email_sent|published|declined|failed)
    created_at: ISO timestamp
    updated_at: ISO timestamp
    article_title: string (optional)
    agent_states: {
      topic_discovery: {status, started_at, completed_at, duration_seconds, output, error}
      research: {status, started_at, completed_at, duration_seconds, output, error}
      seo_writer: {status, started_at, completed_at, duration_seconds, output, error}
      content_checker: {status, started_at, completed_at, duration_seconds, output, error}
    }
  }
  ```

**Workflow Status Progression:**
1. `initialized` → Manager creates workflow
2. `discovering_topic` → TopicDiscoveryAgent running
3. `researching` → ResearchAgent running
4. `writing` → SEOWriterAgent running
5. `checking` → ContentCheckerAgent validating
6. `approved` / `needs_revision` / `rejected` → ContentChecker result
7. `email_sent` → Approval email delivered (only for approved/needs_revision)
8. `published` → User clicked APPROVE in email
9. `declined` → User clicked DECLINE in email
10. `failed` → Error occurred

### Approval Workflow

**Email System:**
- Manager Agent sends HTML emails via SES
- Multi-agent emails include: quality score badge, validation details, strengths/weaknesses
- Single-agent emails include: basic article preview
- Approval tokens: SHA-256 hashed, one-time use, stored in DynamoDB

**Approval Handler** (`blog_agent.py:approval_handler`)
- API Gateway endpoint: `GET /approve?workflow_id=xxx&token=xxx&action=approve/decline`
- Validates token against DynamoDB workflow state
- On approve: publishes to Sanity CMS, updates workflow status to "published"
- On decline: updates workflow status to "declined"

### AWS Bedrock Integration

**Model:** `anthropic.claude-3-sonnet-20240229-v1:0`
- **CRITICAL:** Must use this exact model ID (Bedrock format)
- Do NOT use: `us.anthropic.claude-3-5-sonnet-20240620-v1:0` or other formats
- Located in: `agents/base_agent.py:51`

**Configuration:**
- Read timeout: 300s (5 minutes)
- Connect timeout: 60s
- Max retries: 3
- Agents use `safe_invoke_claude()` for automatic retry on transient failures

### Secrets Management

All API credentials stored in AWS Secrets Manager:
- `blog-sanity-credentials` - Sanity CMS project_id, dataset, token
- `blog-cloudinary-credentials` - Cloudinary cloud_name, api_key, api_secret
- `blog-pexels-credentials` - Pexels API key
- `blog-google-keywords-credentials` - Google Ads API credentials

Accessed via `BaseAgent.get_secrets(secret_name)`

## Critical Implementation Details

### Lambda Retry Configuration

**Must have MaximumRetryAttempts=0** to prevent duplicate workflows:
```bash
aws lambda put-function-event-invoke-config \
  --function-name blog-multiagent-workflow \
  --maximum-retry-attempts 0 \
  --region us-east-1
```

Without this, Lambda retries on timeout/error can create 2-3 duplicate workflows. The `deploy.sh` script automatically configures this.

### DynamoDB Float Handling

**Always convert floats to Decimal** before writing to DynamoDB:
```python
def _convert_floats_to_decimal(self, obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    # ... handle dict/list recursively
```

Located in `agents/base_agent.py:111`. DynamoDB does not support Python float type.

### Quality Score Thresholds

Defined in `agents/content_checker_agent.py:28-38`:
- Word count: 2,500-3,500
- Keyword density: 1-3%
- Meta title: 50-60 chars
- Meta description: 140-160 chars
- Internal links: 2-5
- Images: 3-5
- Flesch readability: ≥60
- Article similarity: <20% with recent articles
- Must-include coverage: ≥80% (critical failure if lower)
- Factual coverage: ≥70% (critical failure if lower)

### Agent Communication Pattern

Agents communicate via input/output dictionaries:
```python
# TopicDiscoveryAgent output → ResearchAgent input
{
  "selected_topic": "...",
  "focus_keywords": [...],
  "target_audience": "..."
}

# ResearchAgent output → SEOWriterAgent input
{
  "research_report": {...},
  "keyword_data": {...}
}

# SEOWriterAgent output → ContentCheckerAgent input
{
  "article": {...},  # Sanity Portable Text JSON
  "title": "...",
  "meta_description": "...",
  "primary_keyword": "...",
  "images": [...]
}

# ContentCheckerAgent output → ManagerAgent
{
  "status": "APPROVED|NEEDS_REVISION|REJECTED",
  "quality_score": 85,
  "validation_details": {...}
}
```

Manager Agent retrieves full workflow context from DynamoDB to pass between agents.

### Error Handling & Retries

**BaseAgent provides:**
- `retry_with_backoff()` - Exponential backoff with jitter (default: 3 retries, base 1s, max 60s)
- `is_transient_error()` - Detects timeout, connection, throttling errors
- `safe_invoke_claude()` - Automatic retry wrapper for Bedrock calls
- `handle_error()` - Updates agent_state to "failed", logs to CloudWatch

**Manager Agent:**
- Catches agent failures, updates workflow status to "failed"
- Does NOT retry failed agents automatically (retry_count tracked but not used)

### Logging & Metrics

**Structured Logging:**
- All agents log JSON to CloudWatch via `log_event(message, level, data)`
- Format: `{timestamp, workflow_id, agent, level, message, data?}`

**CloudWatch Metrics** (`agents/metrics.py`):
- Agent execution time + success/failure
- Bedrock API costs (calculated from token usage)
- Error counts by type
- Namespace: `BlogAutomation/MultiAgent`

## Testing

Run phased tests:
```bash
python3 tests/test_phase1.py  # Foundation tests (DynamoDB, Bedrock access)
python3 tests/test_phase2.py  # Research & writing tests
python3 tests/test_phase3.py  # Quality control tests
python3 tests/test_phase4.py  # Monitoring tests
```

Tests require AWS credentials and may invoke Bedrock (costs incurred).

## Environment Variables

**Required for daily workflow functions:**
- `API_GATEWAY_URL` - Approval endpoint URL (set by deploy.sh)

**Optional for local development:**
- `AWS_PROFILE` - AWS profile name (default: blog-automation)
- `AWS_REGION` - AWS region (default: us-east-1)

## GitHub Actions

**Workflow:** `.github/workflows/deploy.yml`
- Triggers: Push to `main` or manual dispatch
- Steps: Checkout → Setup Python 3.12 → Configure AWS → Deploy → Verify → Set retry config
- **Required Secrets:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## Topic Bank

24 predefined topics in `agents/topic_discovery_agent.py`:
- Cultural Routes: Temple trails, spice gardens, colonial heritage
- Geographic Regions: Hill country, coastal routes, central highlands
- Experience Types: Wildlife cycling, tea plantation tours
- E-Bike Adventures: Accessible routes for all fitness levels
- Unique Experiences: Festival cycling, night rides

TopicDiscoveryAgent randomly selects and verifies uniqueness against recent DynamoDB articles.

## Important Notes

1. **Never commit secrets** - All credentials in AWS Secrets Manager
2. **Always test multi-agent locally first** - Bedrock calls cost money
3. **Monitor DynamoDB costs** - PAY_PER_REQUEST billing mode
4. **SES sender verification required** - `chin@acrossceylon.com` must be verified
5. **Lambda memory sizing matters** - Multi-agent needs 3008 MB, single-agent 2048 MB
6. **Sanity CMS dataset** - Production dataset: "production"
7. **EventBridge timezone** - Schedule uses Europe/London (DST-aware)
8. **Quality validation is automatic** - ContentChecker rejects <70% articles without human intervention
