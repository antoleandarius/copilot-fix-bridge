"""
AgentHQ API Client with mock mode support.
Handles all interactions with AgentHQ API including agent run creation,
status checks, and cancellation.
"""
import httpx
import time
import logging
import uuid
from typing import Dict, Optional, Any
from config import settings
from models import (
    AgentRunInput,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatusResponse,
    AgentRunStatus
)

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

    Usage:
        # Mock mode (for testing)
        with AgentHQClient(mock_mode=True) as client:
            result = client.create_agent_run(...)

        # Real API mode
        with AgentHQClient() as client:
            result = client.create_agent_run(...)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize AgentHQ client.

        Args:
            api_key: AgentHQ API key (defaults to settings)
            base_url: API base URL (defaults to settings)
            agent_id: Default agent ID to use (defaults to settings)
            webhook_url: Webhook URL for callbacks (defaults to settings)
            mock_mode: Enable mock mode (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.api_key = api_key or settings.agenthq_api_key
        self.base_url = base_url or settings.agenthq_base_url
        self.agent_id = agent_id or settings.agenthq_agent_id
        self.webhook_url = webhook_url or settings.agenthq_webhook_url
        self.mock_mode = mock_mode if mock_mode is not None else settings.agenthq_mock_mode
        self.timeout = timeout or settings.agenthq_timeout

        # Validate configuration
        if not self.mock_mode and not self.api_key:
            raise AgentHQError("API key required when not in mock mode")

        # Initialize HTTP client
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )

        logger.info(
            f"AgentHQ client initialized (mock_mode={self.mock_mode}, "
            f"base_url={self.base_url})"
        )

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
        branch_base: str = "main",
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
            branch_base: Base branch for PR (default: "main")
            agent_id: Optional specific agent to use (defaults to configured agent)

        Returns:
            Dict with run_id, status, and other details

        Raises:
            AgentHQAPIError: If API returns error
            AgentHQTimeoutError: If request times out
            AgentHQError: For other errors
        """
        if self.mock_mode:
            return self._mock_create_agent_run(ticket_id, ticket_summary)

        # Prepare agent run input
        agent_input = AgentRunInput(
            task_type="jira_fix",
            ticket_id=ticket_id,
            ticket_summary=ticket_summary,
            ticket_description=ticket_description,
            jira_url=jira_url,
            repository=github_repo,
            branch_base=branch_base,
            branch_name=f"fix/{ticket_id}"
        )

        # Prepare request payload
        request_payload = AgentRunRequest(
            agent_id=agent_id or self.agent_id,
            input=agent_input,
            webhook_url=self.webhook_url,
            metadata={
                "source": "jira_webhook",
                "bridge_version": "1.0.0",
                "ticket_id": ticket_id
            }
        )

        try:
            logger.info(f"Creating AgentHQ run for {ticket_id}")
            logger.debug(f"Request payload: {request_payload.model_dump()}")

            response = self.client.post(
                "/v1/agents/runs",
                json=request_payload.model_dump()
            )

            if response.status_code == 201:
                data = response.json()
                logger.info(f"AgentHQ run created: {data.get('run_id')}")
                return data
            else:
                error_data = None
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", response.text)
                except Exception:
                    error_msg = response.text

                logger.error(f"AgentHQ API error: {response.status_code} - {error_msg}")
                raise AgentHQAPIError(response.status_code, error_msg, error_data)

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

        Raises:
            AgentHQAPIError: If API returns error
            AgentHQTimeoutError: If request times out
        """
        if self.mock_mode:
            return self._mock_get_run_status(run_id)

        try:
            logger.info(f"Checking status for run {run_id}")
            response = self.client.get(f"/v1/agents/runs/{run_id}")

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Run {run_id} status: {data.get('status')}")
                return data
            else:
                error_msg = response.json().get("error", response.text) if response.text else "Unknown error"
                raise AgentHQAPIError(
                    response.status_code,
                    f"Failed to get run status: {error_msg}",
                    response.json() if response.text else None
                )

        except httpx.TimeoutException:
            logger.error(f"Timeout checking status for run {run_id}")
            raise AgentHQTimeoutError(f"Status check timed out for {run_id}")
        except httpx.RequestError as e:
            logger.error(f"Request error checking status: {e}")
            raise AgentHQError(f"Failed to check run status: {e}")

    def cancel_run(self, run_id: str) -> bool:
        """
        Cancel a running agent execution.

        Args:
            run_id: The agent run identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        if self.mock_mode:
            logger.info(f"[MOCK] Cancelled run {run_id}")
            return True

        try:
            logger.info(f"Cancelling run {run_id}")
            response = self.client.post(f"/v1/agents/runs/{run_id}/cancel")

            if response.status_code == 200:
                logger.info(f"Run {run_id} cancelled successfully")
                return True
            else:
                logger.error(f"Failed to cancel run {run_id}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
            return False

    # Mock implementations for testing

    def _mock_create_agent_run(self, ticket_id: str, ticket_summary: str) -> Dict[str, Any]:
        """
        Mock agent run creation for testing.
        Returns a simulated successful response.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        logger.info(f"[MOCK] Created agent run: {run_id} for {ticket_id}")

        return {
            "run_id": run_id,
            "status": AgentRunStatus.RUNNING.value,
            "ticket_id": ticket_id,
            "ticket_summary": ticket_summary,
            "created_at": time.time(),
            "estimated_duration": 120  # 2 minutes
        }

    def _mock_get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Mock status check for testing.
        Returns a simulated running state.
        """
        logger.debug(f"[MOCK] Status check for {run_id}")

        return {
            "run_id": run_id,
            "status": AgentRunStatus.RUNNING.value,
            "progress": 0.5,
            "current_step": "Analyzing codebase",
            "updated_at": time.time()
        }

    def close(self):
        """Close the HTTP client"""
        self.client.close()
        logger.debug("AgentHQ client closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function for quick client creation
def create_client(mock_mode: Optional[bool] = None) -> AgentHQClient:
    """
    Create an AgentHQ client with default settings.

    Args:
        mock_mode: Override mock mode setting

    Returns:
        Configured AgentHQ client
    """
    return AgentHQClient(mock_mode=mock_mode)
