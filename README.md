# Copilot Fix Bridge

Automated bridge service that connects JIRA tickets labeled with `copilot-fix` to GitHub PR creation.

## Architecture Overview

```
JIRA Ticket (copilot-fix label)
    ↓ webhook
FastAPI Bridge (/jira-webhook)
    ↓ repository_dispatch
GitHub Actions Workflow
    ↓ creates branch + HTML file + PR
GitHub PR Created
    ↓ webhook
FastAPI Bridge (/github-pr)
    ↓ posts comment
JIRA Ticket (comment with PR link)
```

## Features

- Automatically creates GitHub branches and PRs when JIRA tickets are labeled `copilot-fix`
- Generates HTML files containing ticket information
- Posts PR links back to JIRA as comments
- Built with FastAPI for high performance
- Easy local testing with ngrok
- Production-ready for deployment on Render, Fly.io, or any cloud platform

## Prerequisites

- Python 3.9+
- GitHub account with repository access
- JIRA account with API access
- ngrok account (for local testing)

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to project directory
cd copilot-fix-bridge

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy sample env file
cp .env.sample .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### 3. Validate Configuration (Recommended)

```bash
# Run the setup validation script
python3 test_setup.py
```

This will check:
- Environment variables are set correctly
- GitHub token has proper access
- JIRA credentials are valid
- All required files are present

Fill in the following values in [.env](.env):

```env
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx  # See setup instructions below
GITHUB_REPO=your-username/your-repo-name

# JIRA Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token_here

# Optional
WEBHOOK_SECRET=your-random-secret-string
PORT=8000
```

### 4. Generate GitHub Personal Access Token

1. Go to GitHub Settings: https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Give it a name like "Copilot Fix Bridge"
4. Select scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
5. Click **"Generate token"**
6. Copy the token and paste it as `GITHUB_TOKEN` in [.env](.env)

### 5. Generate JIRA API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Give it a label like "Copilot Fix Bridge"
4. Copy the token and paste it as `JIRA_API_TOKEN` in [.env](.env)

### 6. Run the Service Locally

```bash
# Start FastAPI server
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Test the health endpoint:
```bash
curl http://localhost:8000/health
```

### 7. Setup ngrok for Local Testing

```bash
# Install ngrok (if not already installed)
# Visit: https://ngrok.com/download

# Start ngrok tunnel
ngrok http 8000
```

You'll see output like:
```
Forwarding   https://abc123.ngrok.app -> http://localhost:8000
```

Copy the `https://abc123.ngrok.app` URL - you'll need it for webhook configuration.

## Webhook Configuration

### Configure JIRA Webhook

1. Go to JIRA Settings: `https://your-domain.atlassian.net/plugins/servlet/webhooks`
2. Click **"Create a WebHook"**
3. Configure:
   - **Name**: Copilot Fix Bridge
   - **Status**: Enabled
   - **URL**: `https://your-ngrok-url.ngrok.app/jira-webhook`
   - **Events**:
     - Issue → updated
     - Issue → created
   - **JQL Filter** (optional): `labels = copilot-fix`
4. Click **"Create"**

### Configure GitHub Webhook

1. Go to your GitHub repository settings
2. Navigate to **Settings → Webhooks → Add webhook**
3. Configure:
   - **Payload URL**: `https://your-ngrok-url.ngrok.app/github-pr`
   - **Content type**: `application/json`
   - **Events**: Select "Let me select individual events"
     - Check: **Pull requests**
   - **Active**: ✓
4. Click **"Add webhook"**

### Enable GitHub Actions

Make sure GitHub Actions are enabled in your repository:

1. Go to **Settings → Actions → General**
2. Under "Actions permissions", select **"Allow all actions and reusable workflows"**
3. Under "Workflow permissions", select **"Read and write permissions"**
4. Check **"Allow GitHub Actions to create and approve pull requests"**
5. Click **"Save"**

## Testing the Workflow

### Test 1: JIRA Webhook Test

```bash
# Create a test JIRA issue or use existing one
# Add the label 'copilot-fix' to the issue

# Watch your FastAPI logs for:
# - "Received JIRA webhook"
# - "Successfully triggered GitHub workflow"
```

### Test 2: GitHub Actions Check

1. Go to your GitHub repository
2. Click **"Actions"** tab
3. You should see a workflow run named "Copilot Fix - Auto PR Creation"
4. Click on it to view logs

### Test 3: PR Creation

1. After workflow completes, check **"Pull requests"** tab
2. You should see a new PR with title: `fix: TICKET-123 - Summary`
3. The PR should contain an HTML file named `TICKET-123.html`

### Test 4: JIRA Comment

1. Go back to your JIRA issue
2. You should see a new comment with the PR link

## Deployment Options

### Option 1: Deploy to Render

1. Create account at https://render.com
2. Click **"New +" → "Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: copilot-fix-bridge
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. Add environment variables from [.env](.env)
6. Click **"Create Web Service"**
7. Copy the deployment URL (e.g., `https://copilot-fix-bridge.onrender.com`)
8. Update JIRA and GitHub webhooks with new URL

### Option 2: Deploy to Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
flyctl auth login

# Launch app
flyctl launch

# Set secrets
flyctl secrets set GITHUB_TOKEN=your_token
flyctl secrets set GITHUB_REPO=your_repo
flyctl secrets set JIRA_BASE_URL=your_jira_url
flyctl secrets set JIRA_EMAIL=your_email
flyctl secrets set JIRA_API_TOKEN=your_token

# Deploy
flyctl deploy
```

### Option 3: Docker Deployment

```bash
# Build Docker image
docker build -t copilot-fix-bridge .

# Run container
docker run -d \
  --name copilot-fix-bridge \
  -p 8000:8000 \
  --env-file .env \
  copilot-fix-bridge
```

## Project Structure

```
/copilot-fix-bridge
├── main.py                        # FastAPI application
├── requirements.txt               # Python dependencies
├── .env.sample                    # Environment template
├── .env                          # Your secrets (git-ignored)
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
└── .github/
    └── workflows/
        └── agent-pr.yml          # GitHub Actions workflow
```

## API Endpoints

### `GET /`
Health check endpoint
```bash
curl http://localhost:8000/
```

### `GET /health`
Detailed health check with configuration status
```bash
curl http://localhost:8000/health
```

### `POST /jira-webhook`
Receives JIRA webhook events
- Triggered when issue is updated/created
- Checks for `copilot-fix` label
- Triggers GitHub Actions via `repository_dispatch`

### `POST /github-pr`
Receives GitHub webhook events
- Triggered when PR is opened
- Extracts JIRA ticket ID from branch name
- Posts PR link as comment to JIRA

## Troubleshooting

### Issue: "Failed to trigger GitHub workflow"

**Solution**:
- Verify `GITHUB_TOKEN` has `repo` and `workflow` scopes
- Check `GITHUB_REPO` format is `owner/repo`
- Ensure repository has Actions enabled

### Issue: "Failed to post JIRA comment"

**Solution**:
- Verify `JIRA_API_TOKEN` is valid
- Check `JIRA_EMAIL` matches token owner
- Confirm `JIRA_BASE_URL` format (no trailing slash)
- Ensure JIRA ticket ID exists

### Issue: "Branch already exists"

**Solution**:
- Delete the existing branch in GitHub
- Or use a different ticket ID
- Workflow will fail if branch exists

### Issue: ngrok tunnel expired

**Solution**:
```bash
# Restart ngrok
ngrok http 8000

# Update webhooks with new URL in JIRA and GitHub
```

### Issue: GitHub Actions workflow not triggering

**Solution**:
- Check repository permissions in Settings → Actions
- Verify workflow file is in `.github/workflows/` directory
- Check Actions tab for error messages
- Ensure `repository_dispatch` event type matches (`copilot-fix`)

## Logs and Debugging

### View FastAPI logs
```bash
# Logs are printed to console when running locally
python main.py
```

### View GitHub Actions logs
1. Go to repository → Actions tab
2. Click on workflow run
3. View logs for each step

### Enable verbose logging
Edit [main.py](main.py:14) and change:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Security Best Practices

1. Never commit `.env` file to git
2. Rotate tokens regularly
3. Use webhook secrets for production
4. Implement rate limiting for production
5. Use HTTPS only (ngrok provides this automatically)

## Customization

### Modify HTML Template
Edit the HTML generation section in [.github/workflows/agent-pr.yml](.github/workflows/agent-pr.yml:46) to customize the output.

### Add More JIRA Fields
Modify [main.py](main.py:49) to extract additional fields from JIRA payload.

### Change Branch Naming
Update branch name pattern in [.github/workflows/agent-pr.yml](.github/workflows/agent-pr.yml:34) and [main.py](main.py:167).

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use this in your projects.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review FastAPI logs
- Check GitHub Actions workflow logs
- Verify webhook delivery in JIRA/GitHub settings

---

Built with FastAPI, GitHub Actions, and JIRA REST API
