# AgentHQ Integration Guide for JIRA-GitHub Bridge

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Integration Design](#integration-design)
3. [Implementation Roadmap](#implementation-roadmap)
4. [AgentHQ API Client](#agenthq-api-client)
5. [Mock Implementation](#mock-implementation)
6. [Testing Strategy](#testing-strategy)
7. [Error Handling & Retries](#error-handling--retries)
8. [Observability & Monitoring](#observability--monitoring)
9. [Configuration & Deployment](#configuration--deployment)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Local Testing Instructions](#local-testing-instructions)

---

## Architecture Overview

### Current Flow (Without AgentHQ)
```
JIRA Ticket (copilot-fix label)
  → FastAPI Bridge (/jira-webhook)
  → GitHub Actions Dispatch (repository_dispatch)
  → GitHub Actions Workflow (agent-pr.yml)
    - Creates branch
    - Generates HTML file
    - Creates PR
  → FastAPI Bridge (/github-pr)
  → JIRA Comment (PR link)
```

### Proposed Flow (With AgentHQ)
```
JIRA Ticket (copilot-fix label)
  → FastAPI Bridge (/jira-webhook)
  → AgentHQ Task Creation (async)
  ┌─────────────────────────────────┐
  │ AgentHQ Agent Execution         │
  │ - Analyzes ticket description   │
  │ - Searches codebase             │
  │ - Generates fix code            │
  │ - Creates branch & commits      │
  │ - Opens PR on GitHub            │
  └─────────────────────────────────┘
  → FastAPI Bridge (/agenthq-status webhook)
  → JIRA Comment (PR link + AI analysis)
```

### Key Differences
1. **Intelligence**: AI-driven code analysis and fix generation vs. static HTML generation
2. **Async Processing**: Long-running agent tasks require webhook callbacks
3. **Stateful**: Need to track agent run status between JIRA trigger and PR creation
4. **Complex Output**: PR contains actual code changes, not just HTML files

---

## Integration Design

### Design Principles

1. **Backward Compatibility**: Keep existing workflow as fallback
2. **Progressive Enhancement**: Add AgentHQ alongside current system
3. **Mock-First Development**: Build and test with mock API before real integration
4. **Observability**: Comprehensive logging and status tracking
5. **Resilience**: Retry logic, timeout handling, graceful degradation

### Integration Points

#### Point 1: JIRA Webhook Handler (Primary)
**Location**: [main.py:78-117](main.py#L78-L117)

**Current Code**:
```python
# Trigger GitHub Actions workflow
dispatch_url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
dispatch_payload = {
    "event_type": "copilot-fix",
    "client_payload": {...}
}
response = requests.post(dispatch_url, headers=headers, json=dispatch_payload)
```

**AgentHQ Replacement**:
```python
# Trigger AgentHQ agent run
from agenthq_client import AgentHQClient, AgentHQError
client = AgentHQClient(mock_mode=AGENTHQ_MOCK_MODE)

try:
    agent_run = client.create_agent_run(
        ticket_id=issue_key,
        ticket_summary=issue_summary,
        ticket_description=issue_description,
        jira_url=f"{JIRA_BASE_URL}/browse/{issue_key}",
        github_repo=GITHUB_REPO
    )

    # Store run_id for status tracking
    logger.info(f"AgentHQ run created: {agent_run['run_id']}")
    return {"status": "agent_started", "run_id": agent_run['run_id']}

except AgentHQError as e:
    logger.error(f"AgentHQ error: {e}")
    # Fallback to GitHub Actions
    response = requests.post(dispatch_url, ...)
```

#### Point 2: AgentHQ Status Webhook (New)
**New Endpoint**: `POST /agenthq-webhook`

**Purpose**: Receive completion/failure notifications from AgentHQ

**Expected Payload**:
```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "ticket_id": "PROJ-123",
  "pr_url": "https://github.com/owner/repo/pull/456",
  "pr_number": 456,
  "branch_name": "fix/PROJ-123",
  "commit_sha": "abc123def456",
  "agent_analysis": "Analysis summary text",
  "files_changed": ["src/main.py", "tests/test_main.py"]
}
```

#### Point 3: Status Tracking (New)
**Requirement**: Persist agent run state between webhook calls

**Options**:
- **Option A**: In-memory dict (simple, not persistent)
- **Option B**: SQLite database (persistent, queryable)
- **Option C**: Redis (scalable, distributed-ready)

**Recommended for MVP**: SQLite with simple schema

---

## Implementation Roadmap

### Phase 1: Foundation Setup (Week 1)
**Goal**: Prepare codebase for AgentHQ integration without breaking existing functionality

#### Tasks:
1. ✅ **Refactor Configuration**
   - Extract env vars to `config.py` using `pydantic-settings`
   - Add AgentHQ-specific variables
   - Support mock mode toggle

2. ✅ **Add Dependencies**
   ```bash
   pip install httpx pydantic-settings pytest pytest-asyncio pytest-mock
   ```

3. ✅ **Create Module Structure**
   ```
   /copilot-fix-bridge
   ├── main.py                 # Existing FastAPI app
   ├── config.py               # NEW: Configuration management
   ├── agenthq_client.py       # NEW: AgentHQ API client
   ├── models.py               # NEW: Pydantic models
   ├── storage.py              # NEW: Run state persistence
   ├── tests/
   │   ├── __init__.py
   │   ├── conftest.py         # Pytest fixtures
   │   ├── test_webhooks.py    # Existing webhook tests
   │   ├── test_agenthq.py     # AgentHQ client tests
   │   └── mock_responses.py   # Mock data
   └── .env.sample             # Updated with AgentHQ vars
   ```

4. ✅ **Create Base Test Suite**
   - Setup pytest configuration
   - Create fixtures for FastAPI test client
   - Mock JIRA/GitHub API responses

### Phase 2: Mock Implementation (Week 1-2)
**Goal**: Build complete AgentHQ integration using mock API

#### Tasks:
1. ✅ **Implement Mock AgentHQ Client**
   - Simulate agent run creation (instant response)
   - Simulate async agent execution (delayed webhook)
   - Generate realistic payloads

2. ✅ **Add AgentHQ Webhook Endpoint**
   - `POST /agenthq-webhook`
   - Verify webhook signature (if provided)
   - Update run state
   - Post JIRA comment with results

3. ✅ **Implement State Storage**
   - SQLite schema for agent runs
   - CRUD operations
   - Status transitions validation

4. ✅ **Test End-to-End Flow with Mocks**
   - JIRA webhook → AgentHQ creation
   - Mock AgentHQ completion → JIRA comment
   - Verify all logs and state updates

### Phase 3: Real API Integration (Week 2-3)
**Goal**: Connect to actual AgentHQ API

#### Tasks:
1. 🔲 **Update AgentHQ Client for Real API**
   - Replace mock with real API calls
   - Handle authentication (API key, OAuth)
   - Implement rate limiting

2. 🔲 **Configure Agent Definition**
   - Create `AGENTS.md` or equivalent
   - Define agent capabilities and instructions
   - Link to GitHub repository

3. 🔲 **Test with Real API (Staging)**
   - Use test JIRA ticket
   - Verify agent execution
   - Confirm PR creation

4. 🔲 **Implement Webhook Receiver**
   - Setup ngrok for local testing
   - Configure AgentHQ webhook URL
   - Verify signature validation

### Phase 4: Production Hardening (Week 3-4)
**Goal**: Make integration production-ready

#### Tasks:
1. 🔲 **Add Retry Logic**
   - Exponential backoff for API calls
   - Max retry limits
   - Dead letter queue for permanent failures

2. 🔲 **Enhance Observability**
   - Structured logging (JSON format)
   - Add metrics endpoints
   - Create status dashboard

3. 🔲 **Security Hardening**
   - Enforce webhook signature validation
   - Add rate limiting to endpoints
   - Sanitize sensitive data in logs

4. 🔲 **Performance Optimization**
   - Use async endpoints where possible
   - Implement connection pooling
   - Add caching for repeated lookups

5. 🔲 **Documentation**
   - Update README with AgentHQ setup
   - Create runbook for operations
   - Document common issues

---

## AgentHQ API Client

### Client Design

```python
# agenthq_client.py
import httpx
import time
import logging
from typing import Dict, Optional, Any
from config import settings

logger = logging.getLogger(__name__)

class AgentHQError(Exception):
    """Base exception for AgentHQ client errors"""
    pass

class AgentHQAPIError(AgentHQError):
    """API returned error response"""
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"AgentHQ API Error {status_code}: {message}")

class AgentHQTimeoutError(AgentHQError):
    """Request to AgentHQ timed out"""
    pass

class AgentHQClient:
    """
    Client for interacting with AgentHQ API.
    Supports both real API and mock mode for testing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_mode: bool = False,
        timeout: int = 30
    ):
        self.api_key = api_key or settings.AGENTHQ_API_KEY
        self.base_url = base_url or settings.AGENTHQ_BASE_URL
        self.mock_mode = mock_mode or settings.AGENTHQ_MOCK_MODE
        self.timeout = timeout

        if not self.mock_mode and not self.api_key:
            raise AgentHQError("API key required when not in mock mode")

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )

        logger.info(f"AgentHQ client initialized (mock_mode={self.mock_mode})")

    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "copilot-fix-bridge/1.0"
        }

        if not self.mock_mode and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def create_agent_run(
        self,
        ticket_id: str,
        ticket_summary: str,
        ticket_description: str,
        jira_url: str,
        github_repo: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new agent run to fix a JIRA ticket.

        Args:
            ticket_id: JIRA ticket identifier (e.g., "PROJ-123")
            ticket_summary: Brief description of the issue
            ticket_description: Full issue description
            jira_url: Full URL to JIRA ticket
            github_repo: Target repository (owner/repo)
            agent_id: Optional specific agent to use

        Returns:
            Dict with run_id and status

        Raises:
            AgentHQAPIError: If API returns error
            AgentHQTimeoutError: If request times out
        """
        if self.mock_mode:
            return self._mock_create_agent_run(ticket_id, ticket_summary)

        payload = {
            "agent_id": agent_id or settings.AGENTHQ_AGENT_ID,
            "input": {
                "task_type": "jira_fix",
                "ticket_id": ticket_id,
                "ticket_summary": ticket_summary,
                "ticket_description": ticket_description,
                "jira_url": jira_url,
                "repository": github_repo,
                "branch_base": "main",
                "branch_name": f"fix/{ticket_id}"
            },
            "webhook_url": settings.AGENTHQ_WEBHOOK_URL,
            "metadata": {
                "source": "jira_webhook",
                "bridge_version": "1.0.0"
            }
        }

        try:
            logger.info(f"Creating AgentHQ run for {ticket_id}")
            response = self.client.post("/v1/agents/runs", json=payload)

            if response.status_code == 201:
                data = response.json()
                logger.info(f"AgentHQ run created: {data.get('run_id')}")
                return data
            else:
                error_msg = response.json().get("error", response.text)
                raise AgentHQAPIError(
                    response.status_code,
                    error_msg,
                    response.json() if response.text else None
                )

        except httpx.TimeoutException as e:
            logger.error(f"Timeout creating AgentHQ run: {e}")
            raise AgentHQTimeoutError(f"Request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise AgentHQError(f"Failed to connect to AgentHQ: {e}")

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the current status of an agent run.

        Args:
            run_id: The agent run identifier

        Returns:
            Dict with current run status and details
        """
        if self.mock_mode:
            return self._mock_get_run_status(run_id)

        try:
            response = self.client.get(f"/v1/agents/runs/{run_id}")

            if response.status_code == 200:
                return response.json()
            else:
                raise AgentHQAPIError(
                    response.status_code,
                    f"Failed to get run status",
                    response.json() if response.text else None
                )

        except httpx.TimeoutException:
            raise AgentHQTimeoutError(f"Status check timed out for {run_id}")
        except httpx.RequestError as e:
            raise AgentHQError(f"Failed to check run status: {e}")

    def cancel_run(self, run_id: str) -> bool:
        """
        Cancel a running agent execution.

        Args:
            run_id: The agent run identifier

        Returns:
            True if cancelled successfully
        """
        if self.mock_mode:
            logger.info(f"Mock: Cancelled run {run_id}")
            return True

        try:
            response = self.client.post(f"/v1/agents/runs/{run_id}/cancel")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
            return False

    # Mock implementations for testing
    def _mock_create_agent_run(self, ticket_id: str, ticket_summary: str) -> Dict[str, Any]:
        """Mock agent run creation"""
        import uuid
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        logger.info(f"[MOCK] Created agent run: {run_id} for {ticket_id}")

        return {
            "run_id": run_id,
            "status": "running",
            "ticket_id": ticket_id,
            "ticket_summary": ticket_summary,
            "created_at": time.time(),
            "estimated_duration": 120  # 2 minutes
        }

    def _mock_get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Mock status check"""
        return {
            "run_id": run_id,
            "status": "running",
            "progress": 0.5,
            "current_step": "Analyzing codebase",
            "updated_at": time.time()
        }

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

### Usage Example

```python
from agenthq_client import AgentHQClient, AgentHQError

# In webhook handler
try:
    with AgentHQClient(mock_mode=True) as client:
        result = client.create_agent_run(
            ticket_id="PROJ-123",
            ticket_summary="Fix login bug",
            ticket_description="Users cannot login with SSO",
            jira_url="https://example.atlassian.net/browse/PROJ-123",
            github_repo="owner/repo"
        )

        run_id = result["run_id"]
        # Store run_id for tracking

except AgentHQError as e:
    logger.error(f"AgentHQ failed: {e}")
    # Fallback to GitHub Actions
```

---

## Mock Implementation

### Mock Server Design

For comprehensive local testing, create a mock AgentHQ server that simulates async agent execution.

```python
# mock_agenthq_server.py
"""
Mock AgentHQ server for local testing.
Simulates agent runs with realistic timing and webhook callbacks.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import asyncio
import httpx
import time

app = FastAPI(title="Mock AgentHQ Server")

# In-memory storage for runs
mock_runs: Dict[str, Dict[str, Any]] = {}

class AgentRunRequest(BaseModel):
    agent_id: str
    input: Dict[str, Any]
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    ticket_id: str
    ticket_summary: str
    created_at: float
    estimated_duration: int

@app.post("/v1/agents/runs", response_model=AgentRunResponse)
async def create_run(request: AgentRunRequest, background_tasks: BackgroundTasks):
    """Create a new agent run (simulated)"""
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    ticket_id = request.input.get("ticket_id")
    ticket_summary = request.input.get("ticket_summary")

    run_data = {
        "run_id": run_id,
        "status": "running",
        "ticket_id": ticket_id,
        "ticket_summary": ticket_summary,
        "created_at": time.time(),
        "estimated_duration": 120,
        "webhook_url": request.webhook_url,
        "input": request.input
    }

    mock_runs[run_id] = run_data

    # Simulate async agent execution
    if request.webhook_url:
        background_tasks.add_task(simulate_agent_execution, run_id)

    return AgentRunResponse(**run_data)

@app.get("/v1/agents/runs/{run_id}")
async def get_run_status(run_id: str):
    """Get run status"""
    if run_id not in mock_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    return mock_runs[run_id]

@app.post("/v1/agents/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a run"""
    if run_id not in mock_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    mock_runs[run_id]["status"] = "cancelled"
    return {"status": "cancelled"}

async def simulate_agent_execution(run_id: str):
    """
    Simulate agent execution with realistic steps and timing.
    Sends webhook when complete.
    """
    run = mock_runs[run_id]
    ticket_id = run["ticket_id"]

    steps = [
        ("Analyzing ticket", 5),
        ("Searching codebase", 10),
        ("Generating fix", 15),
        ("Creating branch", 5),
        ("Committing changes", 5),
        ("Opening PR", 5)
    ]

    for step_name, duration in steps:
        await asyncio.sleep(duration)
        run["current_step"] = step_name
        print(f"[{run_id}] {step_name}...")

    # Mark as completed
    run["status"] = "completed"
    run["completed_at"] = time.time()
    run["pr_number"] = 123  # Mock PR number
    run["pr_url"] = f"https://github.com/mock/repo/pull/123"
    run["branch_name"] = f"fix/{ticket_id}"

    # Send webhook callback
    if run["webhook_url"]:
        await send_completion_webhook(run)

async def send_completion_webhook(run: Dict[str, Any]):
    """Send webhook notification to bridge"""
    webhook_payload = {
        "run_id": run["run_id"],
        "status": "completed",
        "ticket_id": run["ticket_id"],
        "pr_url": run["pr_url"],
        "pr_number": run["pr_number"],
        "branch_name": run["branch_name"],
        "commit_sha": "abc123def456789",
        "agent_analysis": f"Fixed issue in {run['ticket_id']}: {run['ticket_summary']}",
        "files_changed": ["src/main.py", "tests/test_main.py"],
        "completed_at": run["completed_at"]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                run["webhook_url"],
                json=webhook_payload,
                timeout=10
            )
            print(f"[{run['run_id']}] Webhook sent: {response.status_code}")
    except Exception as e:
        print(f"[{run['run_id']}] Webhook failed: {e}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Mock AgentHQ Server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Running Mock Server

```bash
# Terminal 1: Run mock AgentHQ server
python mock_agenthq_server.py

# Terminal 2: Run your FastAPI bridge with mock mode
AGENTHQ_MOCK_MODE=false AGENTHQ_BASE_URL=http://localhost:8001 python main.py

# Terminal 3: Trigger webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json
```

---

## Testing Strategy

### Testing Pyramid

```
           ┌─────────────────────┐
           │   E2E Tests (5%)    │  Full flow with real/mock services
           ├─────────────────────┤
           │ Integration (25%)   │  Multiple components together
           ├─────────────────────┤
           │  Unit Tests (70%)   │  Individual functions/classes
           └─────────────────────┘
```

### Test Suite Structure

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app
from agenthq_client import AgentHQClient

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def mock_agenthq_client():
    """Mock AgentHQ client"""
    return AgentHQClient(mock_mode=True)

@pytest.fixture
def sample_jira_webhook():
    """Sample JIRA webhook payload"""
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-123",
            "fields": {
                "summary": "Fix authentication bug",
                "description": "Users cannot login",
                "labels": ["copilot-fix"]
            }
        }
    }

# tests/test_agenthq_client.py
import pytest
from agenthq_client import AgentHQClient, AgentHQError, AgentHQAPIError

def test_client_initialization_mock_mode():
    """Test client can initialize in mock mode without API key"""
    client = AgentHQClient(mock_mode=True)
    assert client.mock_mode is True
    client.close()

def test_client_initialization_requires_api_key():
    """Test client requires API key in real mode"""
    with pytest.raises(AgentHQError):
        AgentHQClient(mock_mode=False, api_key=None)

def test_create_agent_run_mock(mock_agenthq_client):
    """Test creating agent run in mock mode"""
    result = mock_agenthq_client.create_agent_run(
        ticket_id="TEST-123",
        ticket_summary="Fix bug",
        ticket_description="Description",
        jira_url="https://example.atlassian.net/browse/TEST-123",
        github_repo="owner/repo"
    )

    assert "run_id" in result
    assert result["status"] == "running"
    assert result["ticket_id"] == "TEST-123"

def test_get_run_status_mock(mock_agenthq_client):
    """Test getting run status in mock mode"""
    status = mock_agenthq_client.get_run_status("run_test123")

    assert "run_id" in status
    assert "status" in status

# tests/test_webhooks_agenthq.py
import pytest
from unittest.mock import patch, MagicMock

def test_jira_webhook_triggers_agenthq(client, sample_jira_webhook):
    """Test JIRA webhook triggers AgentHQ run"""
    with patch("main.AgentHQClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.create_agent_run.return_value = {
            "run_id": "run_abc123",
            "status": "running"
        }
        mock_client.return_value.__enter__.return_value = mock_instance

        response = client.post("/jira-webhook", json=sample_jira_webhook)

        assert response.status_code == 200
        assert "run_id" in response.json()
        mock_instance.create_agent_run.assert_called_once()

def test_agenthq_webhook_posts_to_jira(client):
    """Test AgentHQ completion webhook posts comment to JIRA"""
    agenthq_payload = {
        "run_id": "run_abc123",
        "status": "completed",
        "ticket_id": "TEST-123",
        "pr_url": "https://github.com/owner/repo/pull/456",
        "pr_number": 456,
        "agent_analysis": "Fixed authentication bug"
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 201

        response = client.post("/agenthq-webhook", json=agenthq_payload)

        assert response.status_code == 200
        # Verify JIRA API was called
        assert mock_post.called

def test_agenthq_error_falls_back_to_github_actions(client, sample_jira_webhook):
    """Test fallback to GitHub Actions when AgentHQ fails"""
    with patch("main.AgentHQClient") as mock_agenthq:
        mock_agenthq.return_value.__enter__.side_effect = Exception("API unavailable")

        with patch("requests.post") as mock_github:
            mock_github.return_value.status_code = 204

            response = client.post("/jira-webhook", json=sample_jira_webhook)

            # Should still succeed via fallback
            assert response.status_code == 200
            # Verify GitHub Actions was called as fallback
            assert mock_github.called

# tests/test_integration_e2e.py
import pytest
import asyncio
from unittest.mock import patch

@pytest.mark.asyncio
async def test_full_flow_with_mock_server(client):
    """
    End-to-end test of full flow:
    1. JIRA webhook received
    2. AgentHQ run created
    3. Mock server simulates completion
    4. Webhook received
    5. JIRA comment posted
    """
    # This would require running the mock server
    # See integration test section below
    pass
```

### Manual Test Cases

#### Test Case 1: Mock AgentHQ Integration
**Objective**: Verify AgentHQ client works in mock mode

```bash
# Setup
export AGENTHQ_MOCK_MODE=true

# Test
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "jira:issue_updated",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "summary": "Fix login bug",
        "description": "Users cannot login with SSO",
        "labels": ["copilot-fix"]
      }
    }
  }'

# Expected Result
# - Status 200
# - Response contains run_id
# - Logs show "AgentHQ run created"
```

#### Test Case 2: AgentHQ Completion Webhook
**Objective**: Verify completion webhook posts to JIRA

```bash
# Prerequisites
# - Mock server running
# - Wait for mock execution to complete (~50 seconds)

# The mock server will automatically call your webhook
# Check logs for:
# - "Received AgentHQ webhook"
# - "Successfully posted comment to JIRA TEST-123"

# Verify in JIRA
# - Comment appears on TEST-123 ticket
# - Contains PR link and analysis
```

#### Test Case 3: Fallback to GitHub Actions
**Objective**: Verify fallback when AgentHQ fails

```bash
# Setup: Break AgentHQ (invalid API key)
export AGENTHQ_MOCK_MODE=false
export AGENTHQ_API_KEY=invalid

# Test: Send JIRA webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Expected Result
# - Logs show "AgentHQ error"
# - Logs show "Falling back to GitHub Actions"
# - GitHub Actions workflow triggered
# - PR created successfully
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_agenthq_client.py -v

# Run with output
pytest -s

# Run only unit tests
pytest -m "not integration"

# Run only integration tests
pytest -m integration
```

---

## Error Handling & Retries

### Error Classification

| Error Type | Action | Retry? | Fallback? |
|------------|--------|--------|-----------|
| AgentHQ Timeout | Retry with exponential backoff | Yes (3x) | Yes (GitHub Actions) |
| AgentHQ 5xx Error | Retry | Yes (3x) | Yes |
| AgentHQ 4xx Error | Log and skip retry | No | Yes |
| AgentHQ 401/403 | Alert admin | No | Yes |
| AgentHQ 429 (Rate limit) | Retry after delay | Yes | No |
| Network error | Retry | Yes (5x) | Yes |
| JIRA API error | Retry | Yes (3x) | Log only |
| GitHub API error | Retry | Yes (3x) | Fail request |

### Retry Implementation

```python
# retry_utils.py
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Type, Tuple

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retry_on: Tuple of exception types to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)

            raise last_exception

        return wrapper
    return decorator

# Usage in AgentHQ client
from retry_utils import retry_with_backoff
from httpx import HTTPStatusError, TimeoutException

class AgentHQClient:
    @retry_with_backoff(
        max_retries=3,
        retry_on=(TimeoutException, HTTPStatusError)
    )
    def create_agent_run(self, ...):
        # API call implementation
        pass
```

### Circuit Breaker Pattern

```python
# circuit_breaker.py
"""
Circuit breaker to prevent cascading failures when AgentHQ is down.
"""
import time
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - AgentHQ unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        return (
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Reset circuit breaker on successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker CLOSED - AgentHQ recovered")

    def _on_failure(self):
        """Record failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )

# Usage
agenthq_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=AgentHQError
)

def create_agent_run_with_breaker(...):
    return agenthq_circuit_breaker.call(
        client.create_agent_run,
        ticket_id=ticket_id,
        ...
    )
```

### Graceful Degradation

```python
# In webhook handler
async def handle_jira_webhook(payload: dict):
    """Handle JIRA webhook with fallback strategy"""

    # Try AgentHQ first
    try:
        with AgentHQClient() as client:
            result = client.create_agent_run(...)
            return {"status": "agent_started", "run_id": result["run_id"]}

    except AgentHQError as e:
        logger.warning(f"AgentHQ unavailable: {e}")

        # Fallback to GitHub Actions
        try:
            response = trigger_github_actions(...)
            if response.status_code == 204:
                return {
                    "status": "fallback_success",
                    "method": "github_actions"
                }
        except Exception as gh_error:
            logger.error(f"GitHub Actions also failed: {gh_error}")
            raise HTTPException(
                status_code=503,
                detail="Both AgentHQ and GitHub Actions unavailable"
            )
```

---

## Observability & Monitoring

### Structured Logging

```python
# logging_config.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra parameter
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)

def setup_logging(json_logs: bool = False):
    """Configure application logging"""
    if json_logs:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

# Usage with context
logger.info(
    "AgentHQ run created",
    extra={
        "extra_data": {
            "run_id": "run_abc123",
            "ticket_id": "PROJ-123",
            "duration_ms": 234
        }
    }
)
```

### Metrics Endpoint

```python
# Add to main.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Metrics
jira_webhooks_total = Counter(
    "jira_webhooks_total",
    "Total JIRA webhooks received",
    ["event_type", "status"]
)

agenthq_runs_total = Counter(
    "agenthq_runs_total",
    "Total AgentHQ runs created",
    ["status"]
)

agenthq_run_duration = Histogram(
    "agenthq_run_duration_seconds",
    "AgentHQ run duration",
    buckets=[30, 60, 120, 300, 600]
)

active_agent_runs = Gauge(
    "active_agent_runs",
    "Number of currently running agents"
)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Use metrics in handlers
@app.post("/jira-webhook")
async def jira_webhook(payload: dict):
    event_type = payload.get("webhookEvent")
    jira_webhooks_total.labels(event_type=event_type, status="received").inc()

    try:
        # Create agent run
        result = client.create_agent_run(...)
        agenthq_runs_total.labels(status="success").inc()
        active_agent_runs.inc()

        return result
    except Exception as e:
        agenthq_runs_total.labels(status="error").inc()
        raise
```

### Status Dashboard

```python
# Add to main.py
from datetime import datetime, timedelta
from storage import get_recent_runs, get_run_statistics

@app.get("/dashboard")
async def dashboard():
    """HTML dashboard showing AgentHQ integration status"""

    # Get statistics
    stats = get_run_statistics()
    recent_runs = get_recent_runs(limit=10)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgentHQ Bridge Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .stat-card {{
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 8px;
                flex: 1;
            }}
            .stat-value {{ font-size: 2em; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            .status-running {{ color: orange; }}
            .status-completed {{ color: green; }}
            .status-failed {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>AgentHQ Bridge Dashboard</h1>
        <p>Last updated: {datetime.now().isoformat()}</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total_runs']}</div>
                <div>Total Runs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['running']}</div>
                <div>Running</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['completed']}</div>
                <div>Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['failed']}</div>
                <div>Failed</div>
            </div>
        </div>

        <h2>Recent Runs</h2>
        <table>
            <tr>
                <th>Run ID</th>
                <th>Ticket</th>
                <th>Status</th>
                <th>Created</th>
                <th>Duration</th>
            </tr>
            {"".join(f'''
            <tr>
                <td>{run['run_id']}</td>
                <td>{run['ticket_id']}</td>
                <td class="status-{run['status']}">{run['status']}</td>
                <td>{run['created_at']}</td>
                <td>{run.get('duration', 'N/A')}</td>
            </tr>
            ''' for run in recent_runs)}
        </table>
    </body>
    </html>
    """

    return Response(content=html, media_type="text/html")
```

---

## Configuration & Deployment

### Environment Variables

```bash
# .env.sample - Updated with AgentHQ variables

# GitHub Configuration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=owner/repo

# JIRA Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_jira_api_token

# AgentHQ Configuration
AGENTHQ_API_KEY=agenthq_your_api_key_here
AGENTHQ_BASE_URL=https://api.agenthq.dev
AGENTHQ_AGENT_ID=agent_default_id
AGENTHQ_WEBHOOK_URL=https://your-domain.com/agenthq-webhook
AGENTHQ_MOCK_MODE=false

# Optional: Webhook Security
WEBHOOK_SECRET=your_webhook_secret

# Application Settings
PORT=8000
LOG_LEVEL=INFO
JSON_LOGS=false

# Feature Flags
ENABLE_AGENTHQ=true
FALLBACK_TO_GITHUB_ACTIONS=true
```

### Configuration Management

```python
# config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application configuration using Pydantic"""

    # GitHub
    github_token: str
    github_repo: str

    # JIRA
    jira_base_url: str
    jira_email: str
    jira_api_token: str

    # AgentHQ
    agenthq_api_key: Optional[str] = None
    agenthq_base_url: str = "https://api.agenthq.dev"
    agenthq_agent_id: Optional[str] = None
    agenthq_webhook_url: Optional[str] = None
    agenthq_mock_mode: bool = True

    # Security
    webhook_secret: Optional[str] = None

    # Application
    port: int = 8000
    log_level: str = "INFO"
    json_logs: bool = False

    # Feature Flags
    enable_agenthq: bool = False
    fallback_to_github_actions: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### Deployment Checklist

- [ ] **Environment Variables Set**
  - All required vars in `.env` or environment
  - Secrets properly secured (not in code)
  - AgentHQ API key obtained and validated

- [ ] **Database Setup** (if using SQLite)
  - Database file created
  - Schema initialized
  - Backup strategy in place

- [ ] **Webhook Configuration**
  - JIRA webhook pointing to `/jira-webhook`
  - GitHub webhook pointing to `/github-pr`
  - AgentHQ webhook URL configured (your `/agenthq-webhook`)
  - Webhook secrets configured and validated

- [ ] **Testing Complete**
  - All unit tests passing
  - Integration tests with mock server passing
  - Manual end-to-end test successful

- [ ] **Monitoring Setup**
  - Logs configured and shipping to aggregator
  - Metrics endpoint accessible
  - Dashboard accessible
  - Alerts configured for errors

- [ ] **Security**
  - Webhook signature validation enabled
  - Rate limiting configured
  - Sensitive data sanitized from logs
  - HTTPS enforced

- [ ] **Documentation**
  - README updated with AgentHQ setup
  - Runbook created for operations
  - Architecture diagrams updated

---

## Troubleshooting Guide

### Common Issues & Solutions

| Issue | Symptoms | Diagnosis | Solution |
|-------|----------|-----------|----------|
| **AgentHQ run not created** | JIRA webhook succeeds but no run_id returned | Check logs for AgentHQ client errors | 1. Verify API key<br>2. Check mock_mode setting<br>3. Verify API URL |
| **Webhook not received** | Agent completes but no JIRA comment | Check AgentHQ webhook configuration | 1. Verify webhook URL is publicly accessible<br>2. Check ngrok tunnel status<br>3. Verify webhook URL in AgentHQ config |
| **JIRA comment fails** | Agent completes, webhook received, but no JIRA comment | Check JIRA API credentials | 1. Verify JIRA_API_TOKEN<br>2. Check JIRA_EMAIL<br>3. Test JIRA API manually |
| **Timeout errors** | Requests to AgentHQ timeout | Network or API performance issue | 1. Increase timeout setting<br>2. Check AgentHQ status page<br>3. Verify network connectivity |
| **Rate limit exceeded** | 429 errors from AgentHQ | Too many requests | 1. Implement request throttling<br>2. Add delay between requests<br>3. Contact AgentHQ support for limit increase |
| **Agent run stuck** | Run shows "running" indefinitely | Agent execution hung or webhook lost | 1. Check run status via API<br>2. Implement timeout monitoring<br>3. Cancel and retry run |
| **PR not created** | Agent completes but no PR on GitHub | GitHub API credentials or permissions | 1. Verify GITHUB_TOKEN has write access<br>2. Check GitHub API logs<br>3. Verify agent has GitHub integration |
| **Fallback not working** | AgentHQ fails and no GitHub Actions triggered | Fallback logic not executing | 1. Check fallback configuration<br>2. Verify FALLBACK_TO_GITHUB_ACTIONS=true<br>3. Check GitHub Actions workflow exists |
| **Database locked** | SQLite errors about locked database | Concurrent access to SQLite | 1. Add connection timeout<br>2. Use WAL mode<br>3. Consider PostgreSQL for production |
| **Webhook signature invalid** | Webhook rejected with 403 | Signature mismatch | 1. Verify webhook secret matches<br>2. Check signature algorithm<br>3. Log expected vs actual signature |

### Debugging Commands

```bash
# Check if FastAPI is running
curl http://localhost:8000/health

# Test JIRA webhook manually
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Test AgentHQ webhook manually
curl -X POST http://localhost:8000/agenthq-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/agenthq_completion.json

# Check AgentHQ run status (if API available)
curl -H "Authorization: Bearer $AGENTHQ_API_KEY" \
  https://api.agenthq.dev/v1/agents/runs/run_abc123

# View recent logs
tail -f logs/app.log | grep AgentHQ

# Check database state (if using SQLite)
sqlite3 agent_runs.db "SELECT * FROM runs ORDER BY created_at DESC LIMIT 10"

# Test JIRA API
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-123"

# Test GitHub API
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user
```

### Log Analysis

```bash
# Find all AgentHQ errors
grep "AgentHQ" logs/app.log | grep ERROR

# Find runs that timed out
grep "timeout" logs/app.log -i

# Count webhook events by type
grep "Received.*webhook" logs/app.log | awk '{print $NF}' | sort | uniq -c

# Find slow requests (>5 seconds)
grep "duration" logs/app.log | awk '$NF > 5000'

# Check for failed JIRA comments
grep "JIRA.*failed" logs/app.log
```

---

## Local Testing Instructions

### Prerequisites

1. **Python Environment**
   ```bash
   python --version  # 3.9+
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   ```bash
   cp .env.sample .env
   # Edit .env with your credentials
   ```

3. **ngrok (for webhook testing)**
   ```bash
   # Install ngrok from ngrok.com
   ngrok http 8000
   ```

### Step-by-Step Testing

#### Test 1: Basic Setup Verification

```bash
# 1. Start FastAPI bridge
python main.py

# Expected output:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000

# 2. Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "github_token": "configured",
#   "jira_token": "configured",
#   "agenthq_api_key": "configured"
# }
```

#### Test 2: Mock AgentHQ Integration

```bash
# Terminal 1: Start FastAPI with mock mode
export AGENTHQ_MOCK_MODE=true
python main.py

# Terminal 2: Send test JIRA webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "jira:issue_updated",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "summary": "Fix authentication bug",
        "description": "Users cannot login with SSO",
        "labels": ["copilot-fix"]
      }
    }
  }'

# Expected response:
# {
#   "status": "agent_started",
#   "run_id": "run_abc123..."
# }

# Check logs:
# INFO:     AgentHQ client initialized (mock_mode=True)
# INFO:     [MOCK] Created agent run: run_abc123 for TEST-123
```

#### Test 3: Mock Server End-to-End

```bash
# Terminal 1: Start mock AgentHQ server
python mock_agenthq_server.py

# Expected output:
# Starting Mock AgentHQ Server on http://localhost:8001
# INFO:     Uvicorn running on http://0.0.0.0:8001

# Terminal 2: Start ngrok for webhook callback
ngrok http 8000

# Note the ngrok URL: https://abc123.ngrok.io

# Terminal 3: Start FastAPI bridge with mock server
export AGENTHQ_MOCK_MODE=false
export AGENTHQ_BASE_URL=http://localhost:8001
export AGENTHQ_WEBHOOK_URL=https://abc123.ngrok.io/agenthq-webhook
python main.py

# Terminal 4: Trigger JIRA webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Watch all terminals for:
# - FastAPI: "AgentHQ run created: run_..."
# - Mock Server: "Simulating agent execution..."
# - Mock Server: "Webhook sent: 200"
# - FastAPI: "Received AgentHQ webhook"
# - FastAPI: "Successfully posted comment to JIRA"
```

#### Test 4: Fallback to GitHub Actions

```bash
# Simulate AgentHQ failure
export AGENTHQ_API_KEY=invalid_key
export FALLBACK_TO_GITHUB_ACTIONS=true

# Send JIRA webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# Expected logs:
# ERROR: AgentHQ error: API key invalid
# INFO: Falling back to GitHub Actions
# INFO: Successfully triggered GitHub workflow
```

#### Test 5: Unit Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest tests/test_agenthq_client.py::test_create_agent_run_mock -v

# Expected output:
# tests/test_agenthq_client.py::test_create_agent_run_mock PASSED
# tests/test_webhooks_agenthq.py::test_jira_webhook_triggers_agenthq PASSED
# ========================= X passed in X.XXs =========================
```

### Switching to Real AgentHQ API

Once AgentHQ API is available:

```bash
# 1. Get API credentials from AgentHQ dashboard
# 2. Update .env
AGENTHQ_API_KEY=your_real_api_key
AGENTHQ_AGENT_ID=your_agent_id
AGENTHQ_MOCK_MODE=false
AGENTHQ_BASE_URL=https://api.agenthq.dev
AGENTHQ_WEBHOOK_URL=https://your-production-domain.com/agenthq-webhook

# 3. Test with real API
python main.py

# 4. Send test webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d @test_payloads/jira_webhook.json

# 5. Monitor logs for real agent execution
# 6. Verify PR created on GitHub
# 7. Verify JIRA comment posted
```

### Validation Checklist

- [ ] Health endpoint returns "healthy"
- [ ] JIRA webhook accepted and returns 200
- [ ] AgentHQ run created (mock or real)
- [ ] Mock server executes agent steps
- [ ] Completion webhook received
- [ ] JIRA comment posted with PR link
- [ ] All tests pass
- [ ] Logs show no errors
- [ ] Dashboard shows run statistics
- [ ] Fallback works when AgentHQ fails

---

## Next Steps

### Immediate Actions
1. **Copy this guide** to your project repository
2. **Create folder structure** as outlined
3. **Implement AgentHQ client** with mock mode
4. **Write unit tests** for client
5. **Test with mock server** end-to-end
6. **Document findings** and adjust as needed

### Before Production
1. **Security audit** - Review all authentication, secrets handling
2. **Load testing** - Test with high volume of webhooks
3. **Monitoring setup** - Configure alerts for failures
4. **Backup strategy** - For database if using persistence
5. **Rollback plan** - Document how to revert to GitHub Actions only

### Future Enhancements
1. **Async processing** - Use Celery or FastAPI BackgroundTasks
2. **Advanced retry** - Dead letter queue, exponential backoff
3. **Multi-agent support** - Route different ticket types to different agents
4. **Rich JIRA comments** - Include code diffs, file changes in comments
5. **Metrics dashboard** - Grafana dashboard for real-time monitoring
6. **A/B testing** - Compare AgentHQ vs GitHub Actions PR quality

---

## Summary

This guide provides a complete roadmap for integrating AgentHQ into your JIRA-GitHub bridge. The approach prioritizes:

- **Mock-first development** - Test without dependency on AgentHQ API availability
- **Backward compatibility** - Keep existing GitHub Actions as fallback
- **Comprehensive testing** - Unit, integration, and end-to-end tests
- **Production readiness** - Error handling, retries, observability
- **Clear documentation** - Step-by-step instructions for local testing and deployment

By following this guide, you'll have a robust, testable, and observable AgentHQ integration that can handle production workloads while gracefully degrading if AgentHQ is unavailable.

**Ready to start?** Begin with Phase 1 tasks and work through the implementation roadmap. All code examples are ready to copy-paste and adapt to your needs.
