# AgentHQ Integration Testing Guide

Complete guide for testing the AgentHQ integration locally before deployment.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Test Scenarios](#test-scenarios)
4. [Running Tests](#running-tests)
5. [Manual Testing](#manual-testing)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy sample environment file
cp .env.sample .env

# Edit .env with your credentials
# For initial testing, use mock mode:
# AGENTHQ_MOCK_MODE=true
# ENABLE_AGENTHQ=true
```

### 3. Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_agenthq_client.py -v
```

### 4. Test with Mock Server

```bash
# Terminal 1: Start mock AgentHQ server
python mock_agenthq_server.py

# Terminal 2: Start FastAPI bridge
export AGENTHQ_MOCK_MODE=false
export AGENTHQ_BASE_URL=http://localhost:8001
export AGENTHQ_WEBHOOK_URL=http://localhost:8000/agenthq-webhook
python main.py

# Terminal 3: Send test webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

---

## Prerequisites

### Required

- **Python 3.9+**
- **Virtual environment** (recommended)
- **Git** (for repository operations)

### Optional (for different test scenarios)

- **ngrok** - For testing webhooks from external services
- **Docker** - For containerized testing
- **curl** or **Postman** - For manual API testing

### Environment Variables

Minimum required for testing:

```bash
# For mock mode testing (no real APIs needed)
AGENTHQ_MOCK_MODE=true
ENABLE_AGENTHQ=true

# Still needed for fallback testing
GITHUB_TOKEN=your_token
GITHUB_REPO=owner/repo
JIRA_BASE_URL=https://domain.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_token
```

---

## Test Scenarios

### Scenario 1: Unit Tests (Fastest)

**Purpose**: Verify individual components work correctly

**Duration**: < 5 seconds

**Command**:
```bash
pytest tests/test_agenthq_client.py -v
```

**What it tests**:
- AgentHQ client initialization
- Mock mode operations
- Request/response handling
- Error handling

**Expected result**: All tests pass

---

### Scenario 2: Mock AgentHQ Integration

**Purpose**: Test full workflow with simulated AgentHQ API

**Duration**: ~1 minute (includes simulated agent execution time)

**Setup**:

Terminal 1 - Mock AgentHQ Server:
```bash
python mock_agenthq_server.py
```

Terminal 2 - Setup ngrok (for webhook callback):
```bash
ngrok http 8000
# Note the HTTPS URL: https://abc123.ngrok.io
```

Terminal 3 - FastAPI Bridge:
```bash
export AGENTHQ_MOCK_MODE=false
export AGENTHQ_BASE_URL=http://localhost:8001
export AGENTHQ_WEBHOOK_URL=https://abc123.ngrok.io/agenthq-webhook
export AGENTHQ_API_KEY=any_value_works_for_mock
python main.py
```

Terminal 4 - Trigger Test:
```bash
# Send JIRA webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Expected response:
# {"status": "agent_started", "run_id": "run_..."}
```

**Watch the logs**:

Mock Server Terminal:
```
[run_abc123] Starting agent execution for PROJ-123
[run_abc123] Analyzing JIRA ticket (progress: 15%)
[run_abc123] Searching codebase for related files (progress: 30%)
...
[run_abc123] Creating pull request (progress: 100%)
[run_abc123] Webhook sent: 200
```

Bridge Terminal:
```
INFO: Received AgentHQ webhook: completed
INFO: Successfully posted comment to JIRA PROJ-123
```

**Verification**:
- [ ] Run created successfully
- [ ] Mock server executed all steps
- [ ] Webhook received by bridge
- [ ] JIRA comment posted (check logs)

---

### Scenario 3: Mock Mode (No External Server)

**Purpose**: Test AgentHQ client without running mock server

**Duration**: < 1 second

**Setup**:
```bash
export AGENTHQ_MOCK_MODE=true
export ENABLE_AGENTHQ=true
python main.py
```

**Test**:
```bash
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Expected response:
# {
#   "status": "agent_started",
#   "run_id": "run_...",
#   "ticket_id": "PROJ-123"
# }
```

**Note**: In this mode, no actual agent execution happens. The client immediately returns a mock response. Good for quick testing of webhook handling logic.

---

### Scenario 4: Fallback to GitHub Actions

**Purpose**: Verify fallback works when AgentHQ fails

**Setup**:
```bash
# Intentionally break AgentHQ
export AGENTHQ_API_KEY=invalid_key
export AGENTHQ_MOCK_MODE=false
export FALLBACK_TO_GITHUB_ACTIONS=true
python main.py
```

**Test**:
```bash
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

**Expected logs**:
```
WARNING: AgentHQ error: API key invalid
INFO: Falling back to GitHub Actions
INFO: Successfully triggered GitHub workflow
```

**Verification**:
- [ ] AgentHQ fails gracefully
- [ ] Fallback triggered automatically
- [ ] GitHub Actions workflow dispatched
- [ ] No errors returned to webhook caller

---

### Scenario 5: Real AgentHQ API (When Available)

**Purpose**: Test integration with real AgentHQ service

**Prerequisites**:
- AgentHQ API key
- AgentHQ agent configured
- Public webhook URL

**Setup**:
```bash
# .env configuration
AGENTHQ_API_KEY=your_real_api_key
AGENTHQ_AGENT_ID=your_agent_id
AGENTHQ_BASE_URL=https://api.agenthq.dev
AGENTHQ_WEBHOOK_URL=https://your-domain.com/agenthq-webhook
AGENTHQ_MOCK_MODE=false
ENABLE_AGENTHQ=true

# Deploy bridge to server or use ngrok
ngrok http 8000
```

**Test**:
```bash
curl -X POST https://your-domain.com/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

**Monitor**:
1. AgentHQ dashboard for run status
2. Bridge logs for webhook receipt
3. GitHub for PR creation
4. JIRA for comment

**Verification**:
- [ ] AgentHQ run created
- [ ] Agent executes and analyzes code
- [ ] PR created on GitHub with actual fix
- [ ] JIRA comment posted with PR link

---

## Running Tests

### Unit Tests

```bash
# All unit tests
pytest tests/test_agenthq_client.py -v

# Specific test
pytest tests/test_agenthq_client.py::TestAgentHQClientMockMode::test_create_agent_run_mock -v

# With output
pytest tests/test_agenthq_client.py -v -s
```

### Integration Tests

```bash
# Mark tests as integration
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Continuous Testing

```bash
# Install pytest-watch
pip install pytest-watch

# Auto-run tests on file changes
ptw
```

---

## Manual Testing

### Health Check

```bash
# Check service health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "github_token": "configured",
  "jira_token": "configured",
  "agenthq_api_key": "configured",
  "agenthq_enabled": true,
  "agenthq_mock_mode": true
}
```

### Test Webhooks

#### JIRA Webhook (with copilot-fix label)
```bash
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

#### JIRA Webhook (without label - should be ignored)
```bash
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook_no_label.json

# Expected: {"status": "ignored", "reason": "..."}
```

#### AgentHQ Completion Webhook
```bash
curl -X POST http://localhost:8000/agenthq-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/agenthq_completion.json
```

#### AgentHQ Failure Webhook
```bash
curl -X POST http://localhost:8000/agenthq-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/agenthq_failure.json
```

### Mock Server Tests

```bash
# Check mock server status
curl http://localhost:8001/

# Create agent run
curl -X POST http://localhost:8001/v1/agents/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test_agent",
    "input": {
      "task_type": "jira_fix",
      "ticket_id": "TEST-123",
      "ticket_summary": "Test bug",
      "ticket_description": "Test description",
      "jira_url": "https://example.atlassian.net/browse/TEST-123",
      "repository": "owner/repo",
      "branch_base": "main",
      "branch_name": "fix/TEST-123"
    },
    "webhook_url": "http://localhost:8000/agenthq-webhook"
  }'

# Get run status
curl http://localhost:8001/v1/agents/runs/run_abc123

# List all runs
curl http://localhost:8001/v1/agents/runs

# Cancel run
curl -X POST http://localhost:8001/v1/agents/runs/run_abc123/cancel
```

---

## Troubleshooting

### Tests Fail with Import Errors

**Problem**: `ModuleNotFoundError: No module named 'config'`

**Solution**:
```bash
# Ensure you're in the project root
pwd  # Should show /path/to/copilot-fix-bridge

# Ensure dependencies are installed
pip install -r requirements.txt

# Run tests from project root
pytest
```

---

### Mock Server Webhook Not Received

**Problem**: Mock server completes but bridge doesn't receive webhook

**Diagnostics**:
```bash
# Check if ngrok is running
curl https://your-ngrok-url.ngrok.io/health

# Check ngrok web interface
open http://127.0.0.1:4040  # View recent requests

# Verify webhook URL in environment
echo $AGENTHQ_WEBHOOK_URL
```

**Solution**:
- Ensure ngrok is running
- Verify AGENTHQ_WEBHOOK_URL uses ngrok HTTPS URL
- Check firewall/network settings

---

### AgentHQ Client Timeout

**Problem**: `AgentHQTimeoutError: Request timed out after 30s`

**Solution**:
```bash
# Increase timeout
export AGENTHQ_TIMEOUT=60

# Or in .env
AGENTHQ_TIMEOUT=60
```

---

### JIRA Comment Not Posted

**Problem**: Webhook received but no JIRA comment

**Diagnostics**:
```bash
# Test JIRA API directly
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-123"

# Check if ticket exists
# Check if API token has permission to comment
```

**Solution**:
- Verify JIRA credentials
- Ensure ticket exists
- Check API token permissions
- Verify JIRA_BASE_URL format (no trailing slash)

---

### GitHub Actions Not Triggered (Fallback)

**Problem**: Fallback doesn't trigger GitHub Actions

**Diagnostics**:
```bash
# Test GitHub API directly
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user

# Check if token has repo dispatch permission
```

**Solution**:
- Verify GITHUB_TOKEN has `repo` scope
- Ensure GITHUB_REPO format is `owner/repo`
- Check if repository_dispatch workflow exists

---

### Pytest Can't Find Tests

**Problem**: `pytest` runs but finds 0 tests

**Solution**:
```bash
# Ensure test files start with test_
ls tests/test_*.py

# Run with verbose discovery
pytest --collect-only

# Specify test directory
pytest tests/
```

---

## Next Steps

After successful local testing:

1. **Deploy to staging** - Test with real JIRA webhooks
2. **Configure AGENTS.md** - Define agent behavior
3. **Monitor logs** - Watch for errors in production
4. **Gradual rollout** - Start with specific JIRA projects
5. **Gather feedback** - Track PR quality and success rate

---

## Additional Resources

- [AGENTHQ_INTEGRATION_GUIDE.md](AGENTHQ_INTEGRATION_GUIDE.md) - Complete integration documentation
- [README.md](README.md) - Main project documentation
- [AgentHQ Documentation](https://docs.agenthq.dev) - Official AgentHQ docs (when available)

---

## Test Checklist

Before considering integration complete, verify:

- [ ] All unit tests pass
- [ ] Mock server integration works
- [ ] Webhook callbacks received correctly
- [ ] JIRA comments posted successfully
- [ ] Fallback to GitHub Actions works
- [ ] Error handling graceful
- [ ] Logging comprehensive
- [ ] Configuration validated
- [ ] Security measures in place
- [ ] Documentation up to date
