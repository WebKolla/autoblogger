# Contributing to Blog Automation System

Thank you for considering contributing to this project! This document provides guidelines for contributing.

## 🤝 How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- CloudWatch logs (sanitize any secrets!)
- AWS region and Python version

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When suggesting:

- Use a clear and descriptive title
- Provide detailed description of the enhancement
- Explain why it would be useful
- Consider cost implications (we aim for <$100/month)

### Pull Requests

1. Fork the repo and create your branch from `main`
2. Update documentation for any changes
3. Test your changes thoroughly
4. Ensure no secrets are committed
5. Follow the existing code style

## 🔧 Development Setup

### Local Development

```bash
# Clone the repo
git clone https://github.com/acrossceylon/blog-automation.git
cd blog-automation

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Configure AWS CLI
aws configure --profile blog-automation
```

### Testing Changes

```bash
# Test Lambda function locally
python3 -c "
from blog_agent import BlogAgent
agent = BlogAgent()
topic = agent.select_next_topic()
print(f'Selected topic: {topic[\"title\"]}')
"

# Deploy to AWS
./deploy.sh

# Test manual trigger
aws lambda invoke \
  --function-name blog-manual-trigger \
  --payload '{}' \
  /tmp/test.json
```

## 📝 Code Style

- Follow PEP 8 for Python code
- Use descriptive variable names
- Add comments for complex logic
- Keep functions focused and small
- Document all public functions

### Example:

```python
def _get_recent_articles(self) -> List[str]:
    """Get summaries of recently published articles to avoid repetition

    Returns:
        List[str]: Article summaries in format "Title: preview..."
    """
    # Implementation
```

## 🔐 Security Guidelines

**NEVER commit:**
- API keys, tokens, or passwords
- AWS credentials
- `.env` files with real values
- Database connection strings

**ALWAYS:**
- Use AWS Secrets Manager for credentials
- Sanitize logs before sharing
- Review `.gitignore` before committing
- Test with dummy data first

## 🧪 Testing Checklist

Before submitting a PR:

- [ ] Code runs without errors
- [ ] All secrets are in Secrets Manager
- [ ] Documentation is updated
- [ ] `.gitignore` excludes sensitive files
- [ ] Lambda deployment succeeds
- [ ] Manual trigger test works
- [ ] CloudWatch logs are clean
- [ ] No breaking changes to existing workflows

## 📚 Documentation

Update these when making changes:

- `README.md` - Main documentation
- `CONTRIBUTING.md` - This file
- Inline code comments
- AWS resource descriptions in `deploy.sh`

## 💡 Feature Ideas

Current roadmap items:

- [ ] A/B testing for article titles
- [ ] Automatic image optimization
- [ ] Multi-language support
- [ ] Social media auto-posting
- [ ] Analytics dashboard
- [ ] Custom tone/style configurations

## ❓ Questions?

- Open an issue for questions
- Tag with `question` label
- Check existing issues first

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Across Ceylon's blog automation!** 🚴‍♂️
