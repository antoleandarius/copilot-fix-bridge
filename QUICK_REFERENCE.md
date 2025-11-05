# Quick Reference Card

## Setup (One-time)

```bash
# 1. Configure environment
cp .env.sample .env
nano .env  # Fill in your credentials

# 2. Validate setup
python3 test_setup.py

# 3. Start service
./start.sh
```

## Daily Usage

```bash
# Start local development
./start.sh

# Run with ngrok (separate terminal)
ngrok http 8000
```

## Key URLs

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Health Check | `http://localhost:8000/health` | Verify service status |
| JIRA Webhook | `https://your-url/jira-webhook` | Receives JIRA events |
| GitHub Webhook | `https://your-url/github-pr` | Receives PR events |
| ngrok Inspector | `http://127.0.0.1:4040` | View webhook traffic |

## Required Credentials

### GitHub
- **Token**: https://github.com/settings/tokens
- **Scopes**: `repo`, `workflow`
- **Format**: `ghp_xxxxxxxxxxxxx`

### JIRA
- **Token**: https://id.atlassian.com/manage-profile/security/api-tokens
- **Email**: Your JIRA account email
- **Format**: `your-domain.atlassian.net`

## Webhook Configuration

### JIRA Webhook
```
URL: https://your-url/jira-webhook
Events: Issue Created, Issue Updated
JQL: labels = copilot-fix (optional)
```

### GitHub Webhook
```
URL: https://your-url/github-pr
Events: Pull requests
Content-Type: application/json
```

## Testing Flow

1. **Add label to JIRA ticket**: `copilot-fix`
2. **Check FastAPI logs**: Should see "Successfully triggered GitHub workflow"
3. **Check GitHub Actions**: Repository → Actions tab
4. **Verify PR created**: Repository → Pull requests tab
5. **Check JIRA comment**: Should have PR link

## Common Commands

```bash
# Test health endpoint
curl http://localhost:8000/health | jq

# View logs
tail -f logs/app.log

# Stop service
Ctrl+C

# Update dependencies
pip install -r requirements.txt --upgrade

# Run validation
python3 test_setup.py
```

## Troubleshooting One-Liners

```bash
# Check environment variables
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓' if os.getenv('GITHUB_TOKEN') else '✗ GITHUB_TOKEN missing')"

# Test GitHub API
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user

# Test JIRA API
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_BASE_URL/rest/api/3/myself"

# Check if port 8000 is in use
lsof -i :8000

# View ngrok tunnels
curl http://127.0.0.1:4040/api/tunnels | jq
```

## GitHub Actions Status

| Status | Meaning |
|--------|---------|
| Queued | Waiting to start |
| In Progress | Running workflow |
| Success | PR created successfully |
| Failed | Check logs for errors |

## File Locations

```
Configuration:  .env
FastAPI App:    main.py
Workflow:       .github/workflows/agent-pr.yml
Logs:           Console output
Test Script:    test_setup.py
```

## Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `GITHUB_TOKEN` | Yes | `ghp_abc123...` |
| `GITHUB_REPO` | Yes | `user/repo` |
| `JIRA_BASE_URL` | Yes | `https://domain.atlassian.net` |
| `JIRA_EMAIL` | Yes | `user@example.com` |
| `JIRA_API_TOKEN` | Yes | `token123...` |
| `WEBHOOK_SECRET` | No | `random-secret` |
| `PORT` | No | `8000` |

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 204 | Success (no content) |
| 400 | Bad request |
| 401 | Unauthorized |
| 404 | Not found |
| 500 | Server error |

## Branch Naming Pattern

Format: `fix/<TICKET-ID>`

Examples:
- `fix/PROJ-123`
- `fix/BUG-456`
- `fix/TASK-789`

## Generated HTML File

Location: `<TICKET-ID>.html`

Contains:
- Ticket ID in `<h1>`
- Ticket description in `<p>`
- JIRA link
- Timestamp
- Styled layout

## Deployment Checklist

- [ ] Update .env with production values
- [ ] Test locally with ngrok
- [ ] Deploy to hosting platform
- [ ] Update JIRA webhook URL
- [ ] Update GitHub webhook URL
- [ ] Test end-to-end flow
- [ ] Monitor logs for errors

## Support Resources

- **README.md**: Complete setup guide
- **PROJECT_SUMMARY.md**: Architecture details
- **test_setup.py**: Validation script
- **GitHub Actions Logs**: Workflow debugging
- **FastAPI Logs**: Service debugging

## Quick Fixes

### Service won't start
```bash
# Check port availability
lsof -i :8000
# Kill existing process if needed
kill -9 $(lsof -t -i:8000)
```

### Webhook not received
```bash
# Check ngrok status
curl http://127.0.0.1:4040/api/tunnels
# Restart ngrok
ngrok http 8000
```

### GitHub workflow not triggering
```bash
# Verify repository_dispatch permissions
# Settings → Actions → General → Workflow permissions
# Enable: "Read and write permissions"
```

## Production URLs

Once deployed, update webhooks to production URL:

**Replace**: `https://abc123.ngrok.app`
**With**: `https://your-service.onrender.com` or `https://your-app.fly.dev`

---

Keep this reference handy for quick access to commands and configurations!
