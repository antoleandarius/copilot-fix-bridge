"""
JIRA-to-GitHub Copilot Fix Bridge
FastAPI service that automates PR creation from JIRA tickets labeled 'copilot-fix'
"""

import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Copilot Fix Bridge", version="1.0.0")

# Environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # format: owner/repo
GITHUB_API_URL = "https://api.github.com"

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")  # e.g., https://your-domain.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "copilot-fix-bridge",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/jira-webhook")
async def jira_webhook(request: Request):
    """
    Handles JIRA webhook events when an issue is labeled with 'copilot-fix'
    Triggers GitHub Actions workflow via repository_dispatch
    """
    try:
        payload = await request.json()
        logger.info(f"Received JIRA webhook: {payload.get('webhookEvent')}")

        # Check if this is an issue update event
        webhook_event = payload.get("webhookEvent")
        if webhook_event not in ["jira:issue_updated", "jira:issue_created"]:
            logger.info(f"Ignoring event: {webhook_event}")
            return {"status": "ignored", "reason": "not an issue update/create event"}

        # Extract issue data
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        issue_fields = issue.get("fields", {})
        issue_summary = issue_fields.get("summary", "No summary")
        issue_description = issue_fields.get("description", "No description provided")
        labels = issue_fields.get("labels", [])

        logger.info(f"Processing issue: {issue_key}")
        logger.info(f"Labels: {labels}")

        # Check if 'copilot-fix' label is present
        if "copilot-fix" not in labels:
            logger.info(f"Issue {issue_key} does not have 'copilot-fix' label")
            return {"status": "ignored", "reason": "copilot-fix label not present"}

        logger.info(f"Triggering GitHub workflow for {issue_key}")

        # Trigger GitHub Actions workflow via repository_dispatch
        dispatch_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/dispatches"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        dispatch_payload = {
            "event_type": "copilot-fix",
            "client_payload": {
                "ticket_id": issue_key,
                "ticket_summary": issue_summary,
                "ticket_description": issue_description,
                "jira_url": f"{JIRA_BASE_URL}/browse/{issue_key}"
            }
        }

        response = requests.post(
            dispatch_url,
            headers=headers,
            json=dispatch_payload,
            timeout=10
        )

        if response.status_code == 204:
            logger.info(f"Successfully triggered GitHub workflow for {issue_key}")
            return {
                "status": "success",
                "message": f"GitHub workflow triggered for {issue_key}",
                "ticket_id": issue_key
            }
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger GitHub workflow: {response.text}"
            )

    except Exception as e:
        logger.error(f"Error processing JIRA webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/github-pr")
async def github_pr_webhook(request: Request):
    """
    Handles GitHub webhook for pull request events
    Posts PR URL back to JIRA issue as a comment
    """
    try:
        payload = await request.json()
        action = payload.get("action")

        logger.info(f"Received GitHub webhook: action={action}")

        # Only process 'opened' PR events
        if action != "opened":
            logger.info(f"Ignoring PR action: {action}")
            return {"status": "ignored", "reason": f"action is {action}, not 'opened'"}

        pull_request = payload.get("pull_request", {})
        pr_url = pull_request.get("html_url")
        pr_title = pull_request.get("title")
        pr_number = pull_request.get("number")
        branch_name = pull_request.get("head", {}).get("ref")

        logger.info(f"PR opened: #{pr_number} - {pr_title}")
        logger.info(f"Branch: {branch_name}")
        logger.info(f"URL: {pr_url}")

        # Extract JIRA ticket ID from branch name (format: fix/TICKET-123)
        if not branch_name or not branch_name.startswith("fix/"):
            logger.warning(f"Branch {branch_name} does not follow fix/TICKET-ID pattern")
            return {"status": "ignored", "reason": "branch name doesn't match pattern"}

        ticket_id = branch_name.replace("fix/", "")
        logger.info(f"Extracted ticket ID: {ticket_id}")

        # Post comment to JIRA
        jira_comment_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_id}/comment"

        auth = (JIRA_EMAIL, JIRA_API_TOKEN)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        comment_body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Pull Request created: ",
                                "marks": [{"type": "strong"}]
                            },
                            {
                                "type": "text",
                                "text": pr_url,
                                "marks": [
                                    {
                                        "type": "link",
                                        "attrs": {"href": pr_url}
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"PR #{pr_number}: {pr_title}"
                            }
                        ]
                    }
                ]
            }
        }

        response = requests.post(
            jira_comment_url,
            auth=auth,
            headers=headers,
            json=comment_body,
            timeout=10
        )

        if response.status_code in [200, 201]:
            logger.info(f"Successfully posted comment to JIRA {ticket_id}")
            return {
                "status": "success",
                "message": f"Comment posted to {ticket_id}",
                "pr_url": pr_url,
                "ticket_id": ticket_id
            }
        else:
            logger.error(f"JIRA API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to post JIRA comment: {response.text}"
            )

    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Detailed health check with configuration validation"""
    config_status = {
        "GITHUB_TOKEN": "configured" if GITHUB_TOKEN else "missing",
        "GITHUB_REPO": GITHUB_REPO if GITHUB_REPO else "missing",
        "JIRA_BASE_URL": JIRA_BASE_URL if JIRA_BASE_URL else "missing",
        "JIRA_EMAIL": "configured" if JIRA_EMAIL else "missing",
        "JIRA_API_TOKEN": "configured" if JIRA_API_TOKEN else "missing"
    }

    all_configured = all(v != "missing" for v in config_status.values())

    return {
        "status": "healthy" if all_configured else "misconfigured",
        "configuration": config_status,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
