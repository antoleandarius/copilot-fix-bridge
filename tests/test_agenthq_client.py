"""
Unit tests for AgentHQ client.
"""
import pytest
from agenthq_client import AgentHQClient, AgentHQError, AgentHQAPIError, AgentHQTimeoutError


class TestAgentHQClientInitialization:
    """Test client initialization"""

    def test_client_initialization_mock_mode(self):
        """Test client can initialize in mock mode without API key"""
        client = AgentHQClient(mock_mode=True)
        assert client.mock_mode is True
        assert client.timeout > 0
        client.close()

    def test_client_initialization_requires_api_key_in_real_mode(self):
        """Test client requires API key in real mode"""
        with pytest.raises(AgentHQError, match="API key required"):
            AgentHQClient(mock_mode=False, api_key=None)

    def test_client_initialization_with_custom_params(self):
        """Test client initialization with custom parameters"""
        client = AgentHQClient(
            api_key="test_key",
            base_url="https://test.example.com",
            agent_id="test_agent",
            webhook_url="https://webhook.test.com",
            mock_mode=False,
            timeout=60
        )
        assert client.api_key == "test_key"
        assert client.base_url == "https://test.example.com"
        assert client.agent_id == "test_agent"
        assert client.webhook_url == "https://webhook.test.com"
        assert client.mock_mode is False
        assert client.timeout == 60
        client.close()

    def test_context_manager(self):
        """Test client works as context manager"""
        with AgentHQClient(mock_mode=True) as client:
            assert client is not None
        # Client should be closed after exiting context


class TestAgentHQClientMockMode:
    """Test client operations in mock mode"""

    def test_create_agent_run_mock(self, mock_agenthq_client):
        """Test creating agent run in mock mode"""
        result = mock_agenthq_client.create_agent_run(
            ticket_id="TEST-123",
            ticket_summary="Fix bug",
            ticket_description="Description of the bug",
            jira_url="https://example.atlassian.net/browse/TEST-123",
            github_repo="owner/repo"
        )

        assert "run_id" in result
        assert result["run_id"].startswith("run_")
        assert result["status"] == "running"
        assert result["ticket_id"] == "TEST-123"
        assert result["ticket_summary"] == "Fix bug"
        assert "created_at" in result
        assert "estimated_duration" in result

    def test_create_agent_run_with_custom_branch(self, mock_agenthq_client):
        """Test creating agent run with custom branch base"""
        result = mock_agenthq_client.create_agent_run(
            ticket_id="TEST-456",
            ticket_summary="Update feature",
            ticket_description="Feature description",
            jira_url="https://example.atlassian.net/browse/TEST-456",
            github_repo="owner/repo",
            branch_base="develop"
        )

        assert result["ticket_id"] == "TEST-456"
        assert "run_id" in result

    def test_get_run_status_mock(self, mock_agenthq_client):
        """Test getting run status in mock mode"""
        status = mock_agenthq_client.get_run_status("run_test123")

        assert "run_id" in status
        assert status["run_id"] == "run_test123"
        assert "status" in status
        assert status["status"] == "running"
        assert "progress" in status
        assert "current_step" in status
        assert "updated_at" in status

    def test_cancel_run_mock(self, mock_agenthq_client):
        """Test cancelling run in mock mode"""
        result = mock_agenthq_client.cancel_run("run_test123")
        assert result is True


class TestAgentHQClientRealMode:
    """Test client operations in real mode (with mocking)"""

    @pytest.fixture
    def real_client(self, mocker):
        """Create client in real mode with mocked HTTP client"""
        # Mock the httpx.Client to prevent actual API calls
        mock_http_client = mocker.MagicMock()
        mocker.patch('httpx.Client', return_value=mock_http_client)

        client = AgentHQClient(
            api_key="test_api_key",
            agent_id="test_agent",
            webhook_url="https://test.com/webhook",
            mock_mode=False
        )
        client.client = mock_http_client
        return client

    def test_create_agent_run_success(self, real_client, mocker):
        """Test successful agent run creation"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "run_id": "run_abc123",
            "status": "running",
            "ticket_id": "TEST-123",
            "ticket_summary": "Fix bug",
            "created_at": 1699564800.0
        }
        real_client.client.post.return_value = mock_response

        result = real_client.create_agent_run(
            ticket_id="TEST-123",
            ticket_summary="Fix bug",
            ticket_description="Bug description",
            jira_url="https://example.atlassian.net/browse/TEST-123",
            github_repo="owner/repo"
        )

        assert result["run_id"] == "run_abc123"
        assert result["status"] == "running"
        real_client.client.post.assert_called_once()

    def test_create_agent_run_api_error(self, real_client, mocker):
        """Test handling API error response"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {"error": "Invalid agent_id"}
        real_client.client.post.return_value = mock_response

        with pytest.raises(AgentHQAPIError) as exc_info:
            real_client.create_agent_run(
                ticket_id="TEST-123",
                ticket_summary="Fix bug",
                ticket_description="Bug description",
                jira_url="https://example.atlassian.net/browse/TEST-123",
                github_repo="owner/repo"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid agent_id" in str(exc_info.value)

    def test_get_run_status_success(self, real_client, mocker):
        """Test successful status check"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run_abc123",
            "status": "completed",
            "progress": 1.0
        }
        real_client.client.get.return_value = mock_response

        result = real_client.get_run_status("run_abc123")

        assert result["run_id"] == "run_abc123"
        assert result["status"] == "completed"
        assert result["progress"] == 1.0

    def test_cancel_run_success(self, real_client, mocker):
        """Test successful run cancellation"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        real_client.client.post.return_value = mock_response

        result = real_client.cancel_run("run_abc123")
        assert result is True

    def test_cancel_run_failure(self, real_client, mocker):
        """Test failed run cancellation"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 404
        real_client.client.post.return_value = mock_response

        result = real_client.cancel_run("run_nonexistent")
        assert result is False
