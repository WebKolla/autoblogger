#!/bin/bash
set -e

# Set AWS region (always needed)
export AWS_REGION=${AWS_REGION:-us-east-1}

# Only set AWS_PROFILE if not in CI/CD environment
if [ -z "$CI" ] && [ -z "$GITHUB_ACTIONS" ]; then
    export AWS_PROFILE=${AWS_PROFILE:-blog-automation}
    echo "🔧 Using AWS Profile: $AWS_PROFILE"
else
    echo "🔧 Running in CI/CD - using environment credentials"
fi

echo "🚀 Deploying Blog Automation System..."
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# 1. Create DynamoDB Table
echo ""
echo "📊 Creating DynamoDB table..."
aws dynamodb create-table \
    --table-name blog-workflow-state \
    --attribute-definitions AttributeName=workflow_id,AttributeType=S \
    --key-schema AttributeName=workflow_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION 2>/dev/null || echo "Table already exists"

# 2. Create IAM Role
echo ""
echo "🔐 Creating IAM role..."

cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
    --role-name blog-automation-lambda-role \
    --assume-role-policy-document file:///tmp/trust-policy.json 2>/dev/null || echo "Role exists"

aws iam attach-role-policy \
    --role-name blog-automation-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

cat > /tmp/lambda-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:*"],
      "Resource": "arn:aws:dynamodb:*:*:table/blog-workflow-state"
    },
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:blog-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name blog-automation-lambda-role \
    --policy-name BlogLambdaPolicy \
    --policy-document file:///tmp/lambda-policy.json

echo "Waiting for role to propagate..."
sleep 10

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/blog-automation-lambda-role"

# 3. Package Lambda (Single-agent)
echo ""
echo "📦 Packaging Single-Agent Lambda..."
mkdir -p lambda-package
cp blog_agent.py lambda-package/
cd lambda-package
pip3 install -q -t . requests 2>/dev/null || true
zip -q -r ../blog_agent.zip .
cd ..

# 3b. Package Multi-Agent Lambda
echo ""
echo "📦 Packaging Multi-Agent Lambda..."
mkdir -p lambda-package-multiagent
cp multi_agent_handler.py lambda-package-multiagent/
cp -r agents lambda-package-multiagent/
cd lambda-package-multiagent
pip3 install -q -t . requests 2>/dev/null || true
zip -q -r ../multi_agent.zip .
cd ..

# 4. Create Lambda Functions (Single-Agent)
echo ""
echo "⚡ Creating Single-Agent Lambda functions..."

for FUNC in "blog-daily-workflow:daily_workflow_handler:2048" \
            "blog-approval-handler:approval_handler:1024" \
            "blog-manual-trigger:manual_trigger_handler:2048"
do
    IFS=':' read -r NAME HANDLER MEMORY <<< "$FUNC"

    aws lambda create-function \
        --function-name $NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler blog_agent.$HANDLER \
        --zip-file fileb://blog_agent.zip \
        --timeout 900 \
        --memory-size $MEMORY \
        --region $AWS_REGION 2>/dev/null && echo "Created $NAME" || \
    aws lambda update-function-code \
        --function-name $NAME \
        --zip-file fileb://blog_agent.zip \
        --region $AWS_REGION >/dev/null && echo "Updated $NAME"
done

# 4b. Create Multi-Agent Lambda Functions
echo ""
echo "⚡ Creating Multi-Agent Lambda functions..."

for FUNC in "blog-multiagent-workflow:multi_agent_workflow_handler:3008" \
            "blog-multiagent-daily:multi_agent_daily_handler:3008"
do
    IFS=':' read -r NAME HANDLER MEMORY <<< "$FUNC"

    aws lambda create-function \
        --function-name $NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler multi_agent_handler.$HANDLER \
        --zip-file fileb://multi_agent.zip \
        --timeout 900 \
        --memory-size $MEMORY \
        --region $AWS_REGION 2>/dev/null && echo "Created $NAME" || \
    aws lambda update-function-code \
        --function-name $NAME \
        --zip-file fileb://multi_agent.zip \
        --region $AWS_REGION 2>/dev/null && echo "Updated $NAME" || echo "Skipped $NAME (will retry)"

    # Set retry configuration
    aws lambda put-function-event-invoke-config \
        --function-name $NAME \
        --maximum-retry-attempts 0 \
        --region $AWS_REGION 2>/dev/null || \
    aws lambda update-function-event-invoke-config \
        --function-name $NAME \
        --maximum-retry-attempts 0 \
        --region $AWS_REGION 2>/dev/null || true
done

# 5. Create API Gateway
echo ""
echo "🌐 Creating API Gateway..."

API_ID=$(aws apigatewayv2 get-apis --region $AWS_REGION \
    --query "Items[?Name=='blog-automation-api'].ApiId" --output text)

if [ -z "$API_ID" ]; then
    API_ID=$(aws apigatewayv2 create-api \
        --name blog-automation-api \
        --protocol-type HTTP \
        --region $AWS_REGION \
        --query 'ApiId' --output text)
fi

LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:blog-approval-handler"

INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $LAMBDA_ARN \
    --payload-format-version 2.0 \
    --region $AWS_REGION \
    --query 'IntegrationId' --output text 2>/dev/null || \
    aws apigatewayv2 get-integrations --api-id $API_ID --region $AWS_REGION \
    --query 'Items[0].IntegrationId' --output text)

aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key 'GET /approve' \
    --target integrations/$INTEGRATION_ID \
    --region $AWS_REGION 2>/dev/null || true

aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name prod \
    --auto-deploy \
    --region $AWS_REGION 2>/dev/null || true

aws lambda add-permission \
    --function-name blog-approval-handler \
    --statement-id apigateway \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*" \
    --region $AWS_REGION 2>/dev/null || true

API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"

aws lambda update-function-configuration \
    --function-name blog-daily-workflow \
    --environment "Variables={API_GATEWAY_URL=$API_URL}" \
    --region $AWS_REGION >/dev/null

# 6. Create Schedule
echo ""
echo "⏰ Creating daily schedule..."

aws events put-rule \
    --name blog-daily-trigger \
    --schedule-expression "cron(0 10 * * ? *)" \
    --state ENABLED \
    --region $AWS_REGION >/dev/null

aws events put-targets \
    --rule blog-daily-trigger \
    --targets "Id=1,Arn=arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:blog-daily-workflow" \
    --region $AWS_REGION >/dev/null

aws lambda add-permission \
    --function-name blog-daily-workflow \
    --statement-id eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/blog-daily-trigger" \
    --region $AWS_REGION 2>/dev/null || true

echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Resources Created:"
echo "  ✅ DynamoDB: blog-workflow-state"
echo ""
echo "  Single-Agent System (Simple & Fast):"
echo "  ✅ Lambda: blog-daily-workflow"
echo "  ✅ Lambda: blog-approval-handler"
echo "  ✅ Lambda: blog-manual-trigger"
echo ""
echo "  Multi-Agent System (Quality Validated):"
echo "  ✅ Lambda: blog-multiagent-workflow"
echo "  ✅ Lambda: blog-multiagent-daily"
echo ""
echo "  ✅ API Gateway: $API_URL"
echo "  ✅ EventBridge: Daily at 10 AM UTC"
echo ""
echo "🧪 Test Single-Agent (Fast):"
echo "aws lambda invoke --function-name blog-manual-trigger --payload '{}' /tmp/test-single.json --profile blog-automation && cat /tmp/test-single.json"
echo ""
echo "🧪 Test Multi-Agent (Quality Validated):"
echo "aws lambda invoke --function-name blog-multiagent-workflow --payload '{}' /tmp/test-multi.json --profile blog-automation && cat /tmp/test-multi.json"
echo ""