# Blog Automation System for Across Ceylon

[![Deploy](https://github.com/WebKolla/blog-automation/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR_USERNAME/blog-automation/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

Automated AI-powered blog content generation system for [acrossceylon.com](https://acrossceylon.com) - Sri Lanka's premier cycling tour operator.

## 🎯 What It Does

Generates 2,500+ word SEO-optimized blog articles about cycling tourism in Sri Lanka:
- ✅ AI-powered content writing using Claude 3 Sonnet
- ✅ Real-time keyword research via Google Keyword Planner API
- ✅ Automatic image sourcing from Cloudinary + Pexels
- ✅ Human-in-the-loop approval via email
- ✅ One-click publishing to Sanity CMS
- ✅ **Budget: <$100/month**

## 🏗️ Architecture

```
EventBridge (daily 10am UTC)
    ↓
Lambda: blog-daily-workflow
    ↓
Claude AI (research & write)
    ↓
Cloudinary + Pexels (find images)
    ↓
SES (email preview with approve/decline)
    ↓
API Gateway → Lambda: blog-approval-handler
    ↓
Sanity CMS (publish article)
```

**Stack:** Python 3.12, AWS Lambda, DynamoDB, Bedrock, SES, API Gateway, EventBridge

## 📦 Setup

### Prerequisites

- AWS Account with:
  - Bedrock access (Claude 3 Sonnet)
  - SES verified sender email
- Google Cloud Console project (for Keyword Planner)
- Sanity CMS account
- Cloudinary account (optional)
- Pexels API key

### 1. Configure AWS Secrets

```bash
# Sanity CMS token
aws secretsmanager create-secret \
  --name blog-sanity-token \
  --secret-string '{"token":"YOUR_SANITY_TOKEN"}' \
  --region us-east-1

# Pexels API key
aws secretsmanager create-secret \
  --name blog-pexels-key \
  --secret-string '{"key":"YOUR_PEXELS_KEY"}' \
  --region us-east-1

# Cloudinary (optional)
aws secretsmanager create-secret \
  --name blog-cloudinary-credentials \
  --secret-string '{"cloud_name":"xxx","api_key":"xxx","api_secret":"xxx"}' \
  --region us-east-1

# Google Ads API (for keyword research)
aws secretsmanager create-secret \
  --name blog-google-ads-credentials \
  --secret-string '{"client_id":"xxx","client_secret":"xxx","refresh_token":"xxx","developer_token":"xxx"}' \
  --region us-east-1
```

### 2. Deploy Infrastructure

```bash
export AWS_PROFILE=blog-automation
export AWS_REGION=us-east-1

./deploy.sh
```

This creates:
- 3 Lambda functions (workflow, approval, manual trigger)
- DynamoDB table (workflow state tracking)
- API Gateway (approval endpoint)
- EventBridge rule (daily trigger at 10am UTC)
- IAM role with required permissions

### 3. Configure Sanity

Update `SANITY_PROJECT_ID` in `blog_agent.py`:
```python
SANITY_PROJECT_ID = "your-project-id"
SANITY_DATASET = "blog-production"
```

## 🚀 Usage

### Manual Trigger

Generate an article immediately:
```bash
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{}' \
  /tmp/test.json
```

### Specific Topic

```bash
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{"topic_title":"Cycling Through Sri Lanka'\''s Cultural Triangle"}' \
  /tmp/test.json
```

### Email Approval

1. Receive email with article preview
2. Click **APPROVE** to publish to Sanity CMS
3. Click **DECLINE** to reject

### Automatic Daily

Articles generate automatically every day at 10am UTC.

## 📝 Article Topics

24 SEO-optimized topics covering:
- Cultural routes (Ancient cities, temples, heritage sites)
- Geographic regions (Hill country, coast, mountains)
- Experience types (Family, solo, luxury, budget)
- Unique angles (E-bikes, yoga retreats, wildlife safaris)

Topics are in `TOPIC_BANK` in `blog_agent.py`.

## 🔑 Google Keyword Planner Setup

The system integrates with Google Keyword Planner for real-time keyword research.

### Get OAuth2 Refresh Token

1. Create OAuth 2.0 credentials in Google Cloud Console
2. Add redirect URI: `http://localhost:8080/`
3. Run `get_refresh_token.py`:
   ```bash
   python3 get_refresh_token.py
   ```
4. Authorize in browser and copy refresh token

### Get Developer Token

1. Go to https://ads.google.com/aw/apicenter
2. Copy your Developer Token

### Update Secret

```bash
aws secretsmanager update-secret \
  --secret-id blog-google-ads-credentials \
  --secret-string '{"client_id":"xxx","client_secret":"xxx","refresh_token":"xxx","developer_token":"xxx"}'
```

## 🛠️ Maintenance

### View Logs

```bash
aws logs tail /aws/lambda/blog-manual-trigger --follow
```

### Clean Stale Workflows

```bash
python3 -c "
import boto3
db = boto3.resource('dynamodb', region_name='us-east-1')
table = db.Table('blog-workflow-state')
response = table.scan(FilterExpression='#s = :status', ExpressionAttributeNames={'#s':'status'}, ExpressionAttributeValues={':status':'awaiting_approval'})
for item in response['Items']:
    table.delete_item(Key={'workflow_id': item['workflow_id']})
    print(f'Deleted {item[\"workflow_id\"]}')"
```

### Update Lambda Code

```bash
# After editing blog_agent.py
rm -rf lambda-package blog_agent.zip
./deploy.sh
```

## 📊 Monitoring

Check DynamoDB for workflow status:
```bash
aws dynamodb scan --table-name blog-workflow-state --query "Items[].{id:workflow_id.S,status:status.S,topic:topic_title.S}"
```

View recent articles:
```bash
aws dynamodb scan --table-name blog-workflow-state --filter-expression "attribute_exists(published_date)" --query "Items[?status.S=='published'].{topic:topic_title.S,date:published_date.S}" --output table
```

## 💰 Cost Breakdown

**Monthly estimate (<$100):**
- Lambda executions: ~$5
- Bedrock (Claude): ~$30-40
- DynamoDB: ~$1
- SES: Free (< 62K emails)
- API Gateway: ~$1
- CloudWatch: ~$2
- **Total: ~$40-50/month**

## 🔧 Configuration

### Email Settings

Update sender email in `blog_agent.py`:
```python
Source="your-email@acrossceylon.com"
Destination={"ToAddresses": ["your-email@acrossceylon.com"]}
```

### Article Length

Adjust in prompt:
```python
# Target 2500-3500 words
"max_tokens": 16000
```

### Image Sources

Priority: Cloudinary (your photos) → Pexels (stock)

## 🐛 Troubleshooting

**Lambda timeout:**
- Increase `max_tokens` for longer articles
- Check Bedrock timeout (currently 5 min)

**Duplicate articles:**
- Check for multiple Lambda invocations
- Clean stale workflows in DynamoDB

**No images from Cloudinary:**
- Verify credentials in Secrets Manager
- Check CloudWatch logs for API errors
- Ensure images exist in Cloudinary account

**Email not received:**
- Verify SES sender in AWS console
- Check spam folder
- View Lambda logs for send errors

## 📁 Project Structure

```
blog-automation/
├── blog_agent.py           # Main Lambda function
├── deploy.sh              # Infrastructure deployment
├── get_refresh_token.py   # OAuth helper for Google Ads
└── README.md              # This file
```

## 🔐 Security

- All secrets stored in AWS Secrets Manager
- IAM roles with least-privilege access
- Approval tokens using SHA-256 hashing
- API Gateway with Lambda authorization

## 📄 License

Proprietary - Across Ceylon

## 👤 Author

Chin @ Across Ceylon
https://acrossceylon.com

---

**Last Updated:** October 2025
**System Version:** 2.0 (Google Ads + Cloudinary Integration)
