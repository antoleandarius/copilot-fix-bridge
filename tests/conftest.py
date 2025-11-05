"""
Pytest configuration and shared fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_jira_webhook():
    """Sample JIRA webhook payload with copilot-fix label"""
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-123",
            "fields": {
                "summary": "Fix authentication bug",
                "description": "Users cannot login with SSO",
                "labels": ["copilot-fix", "backend"]
            }
        }
    }


@pytest.fixture
def sample_jira_webhook_no_label():
    """Sample JIRA webhook without copilot-fix label"""
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-456",
            "fields": {
                "summary": "Documentation update",
                "description": "Update README",
                "labels": ["documentation"]
            }
        }
    }


@pytest.fixture
def sample_agenthq_completion():
    """Sample AgentHQ completion webhook payload"""
    return {
        "run_id": "run_abc123def456",
        "status": "completed",
        "ticket_id": "TEST-123",
        "pr_url": "https://github.com/owner/repo/pull/456",
        "pr_number": 456,
        "branch_name": "fix/TEST-123",
        "commit_sha": "abc123def456789",
        "agent_analysis": "Fixed authentication bug by updating OAuth configuration",
        "files_changed": ["src/auth.py", "tests/test_auth.py"],
        "completed_at": 1699564800.0
    }


@pytest.fixture
def sample_github_pr_webhook():
    """Sample GitHub PR webhook payload"""
    return {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "html_url": "https://github.com/owner/repo/pull/123",
            "title": "fix: TEST-123 - Fix authentication bug",
            "head": {
                "ref": "fix/TEST-123"
            }
        }
    }


@pytest.fixture
def mock_agenthq_client():
    """Mock AgentHQ client for testing"""
    from agenthq_client import AgentHQClient
    return AgentHQClient(mock_mode=True)


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for external API calls"""
    mock = MagicMock()
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {"success": True}
    return mock


@pytest.fixture
def mock_github_dispatch_success(mock_requests_post):
    """Mock successful GitHub Actions dispatch"""
    mock_requests_post.return_value.status_code = 204
    return mock_requests_post


@pytest.fixture
def mock_jira_comment_success(mock_requests_post):
    """Mock successful JIRA comment creation"""
    mock_requests_post.return_value.status_code = 201
    return mock_requests_post
