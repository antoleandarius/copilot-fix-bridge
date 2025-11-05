"""
Pydantic models for request/response validation and data structures.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentRunStatus(str, Enum):
    """Agent run status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JiraWebhookPayload(BaseModel):
    """JIRA webhook payload structure"""
    webhookEvent: str
    issue: Dict[str, Any]

    @property
    def issue_key(self) -> Optional[str]:
        return self.issue.get("key")

    @property
    def issue_summary(self) -> Optional[str]:
        return self.issue.get("fields", {}).get("summary")

    @property
    def issue_description(self) -> Optional[str]:
        return self.issue.get("fields", {}).get("description")

    @property
    def labels(self) -> List[str]:
        return self.issue.get("fields", {}).get("labels", [])


class AgentRunInput(BaseModel):
    """Input data for creating an agent run"""
    task_type: str = "jira_fix"
    ticket_id: str
    ticket_summary: str
    ticket_description: str
    jira_url: str
    repository: str
    branch_base: str = "main"
    branch_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_type": "jira_fix",
                "ticket_id": "PROJ-123",
                "ticket_summary": "Fix authentication bug",
                "ticket_description": "Users cannot login with SSO",
                "jira_url": "https://example.atlassian.net/browse/PROJ-123",
                "repository": "owner/repo",
                "branch_base": "main",
                "branch_name": "fix/PROJ-123"
            }
        }


class AgentRunRequest(BaseModel):
    """Request to create an agent run"""
    agent_id: str
    input: AgentRunInput
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    """Response from creating an agent run"""
    run_id: str
    status: AgentRunStatus
    ticket_id: str
    ticket_summary: str
    created_at: float
    estimated_duration: Optional[int] = None


class AgentRunStatusResponse(BaseModel):
    """Response from querying agent run status"""
    run_id: str
    status: AgentRunStatus
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    current_step: Optional[str] = None
    updated_at: float
    error_message: Optional[str] = None


class AgentCompletionWebhook(BaseModel):
    """Webhook payload sent by AgentHQ on completion"""
    run_id: str
    status: AgentRunStatus
    ticket_id: str
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    commit_sha: Optional[str] = None
    agent_analysis: Optional[str] = None
    files_changed: Optional[List[str]] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_abc123def456",
                "status": "completed",
                "ticket_id": "PROJ-123",
                "pr_url": "https://github.com/owner/repo/pull/456",
                "pr_number": 456,
                "branch_name": "fix/PROJ-123",
                "commit_sha": "abc123def456789",
                "agent_analysis": "Fixed authentication bug by updating OAuth configuration",
                "files_changed": ["src/auth.py", "tests/test_auth.py"],
                "completed_at": 1699564800.0
            }
        }


class GitHubPRWebhook(BaseModel):
    """GitHub PR webhook payload"""
    action: str
    pull_request: Dict[str, Any]

    @property
    def pr_number(self) -> Optional[int]:
        return self.pull_request.get("number")

    @property
    def pr_url(self) -> Optional[str]:
        return self.pull_request.get("html_url")

    @property
    def branch_name(self) -> Optional[str]:
        return self.pull_request.get("head", {}).get("ref")


class AgentRun(BaseModel):
    """Database model for agent run persistence"""
    run_id: str
    ticket_id: str
    ticket_summary: str
    status: AgentRunStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str
    github_token: str
    jira_token: str
    agenthq_api_key: str
    agenthq_enabled: bool
    agenthq_mock_mode: bool
    timestamp: str
