# AgentHQ Integration Quick Start

Get your AgentHQ integration running in 5 minutes.

## 1. Install Dependencies (30 seconds)

```bash
cd /path/to/copilot-fix-bridge
pip install -r requirements.txt
```

## 2. Configure Environment (1 minute)

```bash
# Copy sample config
cp .env.sample .env

# Edit .env - for quick testing, just set:
# AGENTHQ_MOCK_MODE=true
# ENABLE_AGENTHQ=true

# Keep your existing GitHub/JIRA credentials as-is
```

## 3. Run Unit Tests (10 seconds)

```bash
pytest tests/test_agenthq_client.py -v
```

**Expected**: All tests pass ✅

## 4. Test Mock Mode (30 seconds)

```bash
# Terminal 1: Start bridge
python main.py

# Terminal 2: Send test webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

**Expected**: Response with `run_id` ✅

## 5. Test with Mock Server (3 minutes)

```bash
# Terminal 1: Mock AgentHQ server
python mock_agenthq_server.py

# Terminal 2: ngrok (for webhook callback)
ngrok http 8000
# Copy the HTTPS URL shown (e.g., https://abc123.ngrok.io)

# Terminal 3: Bridge with mock server
export AGENTHQ_MOCK_MODE=false
export AGENTHQ_BASE_URL=http://localhost:8001
export AGENTHQ_WEBHOOK_URL=https://abc123.ngrok.io/agenthq-webhook
export AGENTHQ_API_KEY=test
python main.py

# Terminal 4: Trigger
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

**Watch the logs**:
- Terminal 1 (Mock Server): Simulates agent execution steps
- Terminal 3 (Bridge): Receives completion webhook and posts to JIRA

**Expected**:
- Run created ✅
- Mock server executes steps ✅
- Webhook received ✅
- JIRA comment logged ✅

---

## Next Steps

### For Production Use

See [AGENTHQ_INTEGRATION_GUIDE.md](AGENTHQ_INTEGRATION_GUIDE.md) for:
- Real API integration
- Production deployment
- Security hardening
- Monitoring setup

### For Testing

See [TESTING.md](TESTING.md) for:
- All test scenarios
- Troubleshooting guide
- Manual testing commands
- Coverage reports

---

## Common Issues

### Import errors
```bash
# Ensure you're in project root
pwd

# Reinstall dependencies
pip install -r requirements.txt
```

### Webhook not received
- Check ngrok is running: `curl https://your-url.ngrok.io/health`
- Verify `AGENTHQ_WEBHOOK_URL` uses ngrok HTTPS URL

### Tests fail
```bash
# Run from project root
cd /path/to/copilot-fix-bridge
pytest -v
```

---

## What You've Tested

✅ AgentHQ client initialization
✅ Mock mode operations
✅ Webhook handling
✅ Mock server integration
✅ Complete flow: JIRA → AgentHQ → GitHub → JIRA

**You're ready to integrate with real AgentHQ API when it becomes available!**
