# 🤖 Blog Automation System

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/)

Intelligent multi-agent system for automated blog content generation for [acrossceylon.com](https://acrossceylon.com) - Sri Lanka's premier cycling tour operator.

---

## 🎯 What It Does

Automatically generates high-quality, SEO-optimized blog articles (2,500-3,500 words) about cycling tourism in Sri Lanka using a sophisticated multi-agent architecture:

- ✅ **Smart Topic Discovery** - Analyzes published content to identify gaps
- ✅ **AI-Powered Research** - Google Keyword Planner API integration
- ✅ **Professional Writing** - Claude 3 Sonnet generates complete articles
- ✅ **Quality Validation** - 5-check automated QA system with scoring
- ✅ **Image Sourcing** - Cloudinary (priority) + Pexels (fallback)
- ✅ **Email Approval** - Quality report with approve/decline workflow
- ✅ **Sanity CMS Integration** - Automatic publishing with approval

---

## 🏗️ Multi-Agent Architecture

The system uses 5 specialized AI agents coordinated by a Manager Agent:

### Agent Responsibilities

| Agent | Purpose | Technologies |
|-------|---------|--------------|
| **Manager** | Orchestrates workflow, manages state, sends emails | DynamoDB, SES, CloudWatch |
| **Topic Discovery** | Finds content gaps, selects topics | Python, DynamoDB |
| **Research** | Keyword research, content strategy | Google Ads API, Claude |
| **SEO Writer** | Generates complete articles | Claude 3 Sonnet, Cloudinary, Pexels |
| **Content Checker** | Quality validation (5 checks, 0-100 score) | Python (no AI) |

### Workflow

```
Manager Agent
    ↓
Topic Discovery → Research → SEO Writer → Content Checker
                                              ↓
                                    [Score 0-100]
                                              ↓
                            ┌─────────────────┼─────────────────┐
                            ↓                 ↓                 ↓
                        APPROVED          NEEDS_REVISION    REJECTED
                        (≥85%)            (70-84%)          (<70%)
                            ↓                 ↓
                      [Send Email]      [Send Email]      [No Email]
                            ↓                 ↓
                        [Approve/Decline from Email]
                            ↓
                    [Publish to Sanity CMS]
```

---

## 🧠 Quality Validation System

Every article receives a quality score (0-100) based on 5 automated checks:

### 1. Factual Accuracy (25% weight)
- Verifies facts against research report
- Requires 70% coverage minimum
- Critical failure if <70%

### 2. SEO Compliance (20% weight)
- Keyword density 1-3%
- Meta title 50-60 chars
- Meta description 140-160 chars
- Internal links 2-5
- Images 3-5

### 3. Research Alignment (20% weight)
- Covers must-include items
- Requires 80% coverage minimum
- Critical failure if <80%

### 4. Uniqueness (20% weight)
- Jaccard similarity with recent 10 articles
- Must be <20% similar
- Critical failure if too similar

### 5. Quality Assessment (15% weight)
- Word count 2,500-3,500
- Flesch readability >60

**Validation Outcomes:**
- **APPROVED** (≥85%): Article approved, email sent
- **NEEDS_REVISION** (70-84%): Minor issues, email sent with warnings
- **REJECTED** (<70%): Quality too low, no email sent

---

## 🚀 Quick Start

### Prerequisites

- AWS Account with Bedrock access (Claude 3 Sonnet model: `anthropic.claude-3-sonnet-20240229-v1:0`)
- Google Cloud Console project (Keyword Planner API)
- Sanity CMS account
- Cloudinary account (optional, for custom images)
- Pexels API key
- SES verified sender email

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/blog-automation.git
cd blog-automation
```

### 2. Configure AWS Secrets

```bash
# Sanity CMS credentials
aws secretsmanager create-secret \
  --name blog-sanity-credentials \
  --secret-string '{"project_id":"xxx","dataset":"production","token":"xxx"}' \
  --region us-east-1

# Cloudinary credentials (optional)
aws secretsmanager create-secret \
  --name blog-cloudinary-credentials \
  --secret-string '{"cloud_name":"xxx","api_key":"xxx","api_secret":"xxx"}' \
  --region us-east-1

# Pexels API key
aws secretsmanager create-secret \
  --name blog-pexels-credentials \
  --secret-string '{"api_key":"xxx"}' \
  --region us-east-1

# Google Keyword Planner credentials
aws secretsmanager create-secret \
  --name blog-google-keywords-credentials \
  --secret-string '{"client_id":"xxx","client_secret":"xxx","refresh_token":"xxx","developer_token":"xxx","customer_id":"xxx"}' \
  --region us-east-1
```

### 3. Deploy Infrastructure

#### Option A: Local Deployment

```bash
export AWS_PROFILE=blog-automation
export AWS_REGION=us-east-1

chmod +x deploy.sh
./deploy.sh
```

#### Option B: GitHub Actions (Automated)

Push to `main` branch or trigger manually via GitHub Actions UI. The workflow will:
1. Package both single-agent and multi-agent systems
2. Deploy all 5 Lambda functions
3. Configure retry settings (MaximumRetryAttempts=0)
4. Verify deployment

**Required GitHub Secrets:**

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key

**Note:** The `deploy.sh` script automatically detects CI/CD environments and skips AWS profile configuration.

**Both options create:**
- ✅ 5 Lambda functions (2 multi-agent workflows, 2 single-agent workflows, 1 approval handler)
- ✅ DynamoDB table `blog-workflow-state`
- ✅ API Gateway approval endpoint
- ✅ EventBridge daily schedule (10 AM UTC)
- ✅ IAM role with CloudWatch, Bedrock, DynamoDB, SES permissions

### 4. Test the Multi-Agent System

```bash
# Trigger multi-agent workflow
aws lambda invoke \
  --function-name blog-multiagent-workflow \
  --payload '{}' \
  /tmp/test.json \
  --profile blog-automation \
  --region us-east-1

# Check DynamoDB for workflow
aws dynamodb scan \
  --table-name blog-workflow-state \
  --profile blog-automation \
  --region us-east-1 \
  --max-items 1
```

### 5. Approve Article from Email

1. **Check your inbox** for approval email with quality score
2. **Click APPROVE** to publish to Sanity CMS
3. **Click DECLINE** to reject the article

---

## 📝 Usage

### Automatic Daily Generation

Articles are generated automatically every day at **10 AM UTC** using the multi-agent workflow.

Current EventBridge configuration:
```bash
# Check which workflow is scheduled
aws events list-targets-by-rule \
  --rule blog-daily-trigger \
  --profile blog-automation \
  --region us-east-1
```

### Manual Trigger

Generate an article immediately:

```bash
# Multi-agent (recommended - includes quality validation)
aws lambda invoke \
  --function-name blog-multiagent-workflow \
  --payload '{}' \
  /tmp/test.json \
  --profile blog-automation

# Single-agent (faster, no quality validation)
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{}' \
  /tmp/test.json \
  --profile blog-automation
```

### Email Approval Workflow

**Multi-Agent Email Includes:**
- Quality score badge (0-100)
- Validation status (APPROVED/NEEDS_REVISION)
- Strengths and areas for improvement
- Article preview
- Metadata (word count, reading time, keywords)
- Up to 3 images preview
- Approve/Decline buttons

**Single-Agent Email Includes:**
- Article preview
- Metadata
- Images preview
- Approve/Decline buttons

### View Workflows

```bash
# Recent workflows
aws dynamodb scan \
  --table-name blog-workflow-state \
  --profile blog-automation \
  --max-items 5 \
  --query 'Items[*].[workflow_id.S, status.S, article_title.S, created_at.S]' \
  --output table
```

---

## 🛠️ Configuration

### Lambda Functions

| Function | Purpose | Memory | Timeout | Retries |
|----------|---------|--------|---------|---------|
| blog-multiagent-workflow | Multi-agent manual trigger | 3008 MB | 900s | 0 |
| blog-multiagent-daily | Multi-agent daily schedule | 3008 MB | 900s | 0 |
| blog-manual-trigger | Single-agent manual trigger | 2048 MB | 900s | 0 |
| blog-daily-workflow | Single-agent daily schedule | 2048 MB | 900s | 0 |
| blog-approval-handler | Approval endpoint | 1024 MB | 900s | 0 |

**Note:** MaximumRetryAttempts is set to 0 to prevent duplicate workflows.

### Environment Variables

All daily workflow functions require:
```bash
API_GATEWAY_URL=https://your-api-gateway-url.amazonaws.com/prod
```

Set via:
```bash
aws lambda update-function-configuration \
  --function-name blog-multiagent-daily \
  --environment "Variables={API_GATEWAY_URL=$API_URL}" \
  --profile blog-automation
```

### Topic Bank

24 SEO-optimized topics in `agents/topic_discovery_agent.py`:

**Categories:**
- Cultural Routes (5 topics)
- Geographic Regions (4 topics)
- Experience Types (5 topics)
- Rural Routes (3 topics)
- E-Bike Adventures (4 topics)
- Unique Experiences (3 topics)

### Article Settings

Word count: 2,500-3,500 words
Images: 3-5 per article
Internal links: 2-3 per article
Keyword density: 1-3%
Format: Sanity Portable Text JSON

---

## 📁 Project Structure

```
blog-automation/
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions deployment
│
├── agents/                          # Multi-agent system
│   ├── base_agent.py               # Base class with Bedrock client
│   ├── manager_agent.py            # Orchestrator + email sending
│   ├── topic_discovery_agent.py    # Topic selection
│   ├── research_agent.py           # Google Ads API + Claude
│   ├── seo_writer_agent.py         # Article generation
│   ├── content_checker_agent.py    # Quality validation (0-100 score)
│   └── metrics.py                  # CloudWatch metrics
│
├── tests/                           # Test suite
│   ├── test_phase1.py              # Foundation tests
│   ├── test_phase2.py              # Research & writing tests
│   ├── test_phase3.py              # Quality control tests
│   └── test_phase4.py              # Monitoring tests
│
├── blog_agent.py                   # Single-agent Lambda handler
├── multi_agent_handler.py          # Multi-agent Lambda handler
├── deploy.sh                       # Infrastructure deployment script
├── install_mcp.sh                  # MCP server installation (optional)
├── requirements.txt                # Python dependencies
│
├── .gitignore                      # Git ignore rules
├── MCP_SETUP.md                    # MCP configuration guide
└── README.md                       # This file
```

---

## 🔍 Monitoring & Debugging

### View Logs

```bash
# Multi-agent logs
aws logs tail /aws/lambda/blog-multiagent-workflow \
  --follow \
  --profile blog-automation \
  --region us-east-1

# Single-agent logs
aws logs tail /aws/lambda/blog-manual-trigger \
  --follow \
  --profile blog-automation \
  --region us-east-1

# Filter by workflow ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/blog-multiagent-workflow \
  --filter-pattern "workflow-1234567890" \
  --profile blog-automation
```

### Check Workflow State

```bash
# Get specific workflow
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"workflow-1234567890"}}' \
  --profile blog-automation \
  --query 'Item.[workflow_id.S, status.S, article_title.S]' \
  --output json

# Get quality score
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"workflow-1234567890"}}' \
  --profile blog-automation \
  --query 'Item.agent_states.M.content_checker.M.output.M.[quality_score.N, status.S]' \
  --output json
```

### Common Workflow Statuses

- `initialized` - Workflow started
- `discovering_topic` - Finding unique topic
- `researching` - Gathering keyword data
- `writing` - Generating article
- `checking` - Validating quality
- `needs_revision` - Quality 70-84%, email sent
- `approved` - Quality ≥85%, email sent (ContentChecker status)
- `rejected` - Quality <70%, no email
- `email_sent` - Approval email delivered
- `published` - Article published to Sanity CMS
- `declined` - User declined from email

---

## 🐛 Troubleshooting

### Issue: Didn't Receive Email

**Check workflow status:**
```bash
aws dynamodb get-item \
  --table-name blog-workflow-state \
  --key '{"workflow_id":{"S":"YOUR_WORKFLOW_ID"}}' \
  --profile blog-automation \
  --query 'Item.[status.S, agent_states.M.content_checker.M.output.M.status.S]'
```

**If status is `rejected`:** Article quality score was <70%, no email sent (by design)

**If status is `email_sent`:** Check CloudWatch logs for SES message ID:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/blog-multiagent-workflow \
  --filter-pattern "Approval email sent" \
  --profile blog-automation
```

**Verify SES sender:** Ensure `chin@acrossceylon.com` is verified in SES

### Issue: Approval Click Gives Error

**Error: "the JSON object must be str, bytes or bytearray, not dict"**
- Fixed in latest version - redeploy: `./deploy.sh`

**Error: "'original_topic'"**
- Fixed in latest version - approval handler now supports both single-agent and multi-agent formats

**Redeploy approval handler:**
```bash
zip -q blog_agent.zip blog_agent.py
aws lambda update-function-code \
  --function-name blog-approval-handler \
  --zip-file fileb://blog_agent.zip \
  --profile blog-automation
```

### Issue: Duplicate Workflows

**Symptom:** 3 workflows created for 1 trigger

**Solution:** Lambda retries are disabled (MaximumRetryAttempts=0)

**Verify:**
```bash
aws lambda get-function-event-invoke-config \
  --function-name blog-multiagent-workflow \
  --profile blog-automation \
  --query 'MaximumRetryAttempts'
```

**Should return:** `0`

**If not, fix with:**
```bash
aws lambda put-function-event-invoke-config \
  --function-name blog-multiagent-workflow \
  --maximum-retry-attempts 0 \
  --profile blog-automation
```

### Issue: Model Access Error

**Error:** "AccessDeniedException: You don't have access to the model"

**Cause:** Using wrong model ID

**Solution:** Ensure `agents/base_agent.py` uses:
```python
self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
```

NOT:
```python
self.model_id = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"  # ❌ Wrong
```

---

## 🔐 Security

- **Secrets Management:** All API keys in AWS Secrets Manager
- **IAM Roles:** Least-privilege access per Lambda
- **Approval Tokens:** SHA-256 hashed, one-time use
- **API Gateway:** Lambda authorizer for approval endpoint
- **No Hardcoded Credentials:** Zero secrets in code
- **Lambda Retries Disabled:** Prevents duplicate workflows

---

## 📊 System Comparison

| Feature | Single-Agent | Multi-Agent |
|---------|-------------|-------------|
| Speed | 60-90s | 90-120s |
| Quality Validation | ❌ None | ✅ 5 checks + 0-100 score |
| Email Quality Report | ❌ Basic | ✅ Detailed with score |
| Automatic Rejection | ❌ No | ✅ Articles <70% |
| Memory | 2048 MB | 3008 MB |
| Status | Production | **Production** ⭐ |

**Recommendation:** Use multi-agent for quality validation and automatic rejection of low-quality articles.

---

## 📄 License

MIT License

---

## 👤 Author

**Chin @ Across Ceylon**
https://acrossceylon.com

Cycling tour company specializing in custom bicycle tours across Sri Lanka.

---

**Last Updated:** October 5, 2025
**System Version:** Multi-Agent Production
**Status:** ✅ Production Ready
