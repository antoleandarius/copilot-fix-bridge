"""
Mock AgentHQ server for local testing.
Simulates agent runs with realistic timing and webhook callbacks.

Usage:
    python mock_agenthq_server.py

Then configure your bridge to use:
    AGENTHQ_BASE_URL=http://localhost:8001
    AGENTHQ_MOCK_MODE=false
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import asyncio
import httpx
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mock AgentHQ Server",
    description="Simulates AgentHQ API for testing copilot-fix-bridge"
)

# In-memory storage for runs
mock_runs: Dict[str, Dict[str, Any]] = {}


class AgentRunInput(BaseModel):
    task_type: str = "jira_fix"
    ticket_id: str
    ticket_summary: str
    ticket_description: str
    jira_url: str
    repository: str
    branch_base: str = "main"
    branch_name: Optional[str] = None


class AgentRunRequest(BaseModel):
    agent_id: str
    input: AgentRunInput
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    ticket_id: str
    ticket_summary: str
    created_at: float
    estimated_duration: int = 120


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mock AgentHQ Server",
        "version": "1.0.0",
        "runs": len(mock_runs),
        "active_runs": len([r for r in mock_runs.values() if r["status"] == "running"])
    }


@app.post("/v1/agents/runs", response_model=AgentRunResponse, status_code=201)
async def create_run(request: AgentRunRequest, background_tasks: BackgroundTasks):
    """
    Create a new agent run (simulated).
    Immediately returns run details and simulates execution in background.
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    ticket_id = request.input.ticket_id
    ticket_summary = request.input.ticket_summary

    logger.info(f"Creating run {run_id} for ticket {ticket_id}")

    run_data = {
        "run_id": run_id,
        "status": "running",
        "ticket_id": ticket_id,
        "ticket_summary": ticket_summary,
        "created_at": time.time(),
        "estimated_duration": 120,
        "webhook_url": request.webhook_url,
        "input": request.input.model_dump(),
        "agent_id": request.agent_id,
        "metadata": request.metadata or {}
    }

    mock_runs[run_id] = run_data

    # Simulate async agent execution
    if request.webhook_url:
        background_tasks.add_task(simulate_agent_execution, run_id, request.webhook_url)
        logger.info(f"Scheduled agent execution for {run_id}")
    else:
        logger.warning(f"No webhook URL provided for {run_id}")

    return AgentRunResponse(
        run_id=run_id,
        status="running",
        ticket_id=ticket_id,
        ticket_summary=ticket_summary,
        created_at=run_data["created_at"],
        estimated_duration=120
    )


@app.get("/v1/agents/runs/{run_id}")
async def get_run_status(run_id: str):
    """Get current status of an agent run"""
    if run_id not in mock_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = mock_runs[run_id]

    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "ticket_id": run["ticket_id"],
        "progress": run.get("progress", 0.0),
        "current_step": run.get("current_step", "Initializing"),
        "updated_at": run.get("updated_at", run["created_at"]),
        "pr_url": run.get("pr_url"),
        "error_message": run.get("error_message")
    }


@app.post("/v1/agents/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a running agent"""
    if run_id not in mock_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run = mock_runs[run_id]

    if run["status"] in ["completed", "failed", "cancelled"]:
        return {"message": f"Run {run_id} already {run['status']}"}

    run["status"] = "cancelled"
    run["updated_at"] = time.time()

    logger.info(f"Cancelled run {run_id}")

    return {"status": "cancelled", "run_id": run_id}


@app.get("/v1/agents/runs")
async def list_runs():
    """List all runs"""
    return {
        "runs": list(mock_runs.values()),
        "total": len(mock_runs)
    }


async def simulate_agent_execution(run_id: str, webhook_url: str):
    """
    Simulate realistic agent execution with multiple steps and timing.
    Sends webhook notification when complete.
    """
    run = mock_runs[run_id]
    ticket_id = run["ticket_id"]

    logger.info(f"[{run_id}] Starting agent execution for {ticket_id}")

    # Simulation steps with realistic durations
    steps = [
        ("Initializing agent", 2, 0.05),
        ("Analyzing JIRA ticket", 3, 0.15),
        ("Searching codebase for related files", 8, 0.30),
        ("Analyzing code context", 5, 0.45),
        ("Generating code fix", 10, 0.65),
        ("Running tests on generated code", 7, 0.80),
        ("Creating branch fix/" + ticket_id, 2, 0.85),
        ("Committing changes", 3, 0.90),
        ("Pushing to remote", 2, 0.95),
        ("Creating pull request", 3, 1.0)
    ]

    try:
        for step_name, duration, progress in steps:
            # Check if cancelled
            if run["status"] == "cancelled":
                logger.info(f"[{run_id}] Execution cancelled at step: {step_name}")
                return

            run["current_step"] = step_name
            run["progress"] = progress
            run["updated_at"] = time.time()

            logger.info(f"[{run_id}] {step_name} (progress: {int(progress * 100)}%)")

            await asyncio.sleep(duration)

        # Mark as completed
        run["status"] = "completed"
        run["completed_at"] = time.time()
        run["progress"] = 1.0
        run["current_step"] = "Completed"

        # Generate mock PR details
        pr_number = hash(run_id) % 1000 + 1  # Deterministic but varied
        run["pr_number"] = pr_number
        run["pr_url"] = f"https://github.com/{run['input']['repository']}/pull/{pr_number}"
        run["branch_name"] = run["input"]["branch_name"]
        run["commit_sha"] = f"{uuid.uuid4().hex[:7]}"

        logger.info(f"[{run_id}] Agent execution completed successfully")

        # Send webhook callback
        await send_completion_webhook(run)

    except Exception as e:
        logger.error(f"[{run_id}] Agent execution failed: {e}")
        run["status"] = "failed"
        run["error_message"] = str(e)
        run["updated_at"] = time.time()

        # Send failure webhook
        await send_completion_webhook(run)


async def send_completion_webhook(run: Dict[str, Any]):
    """
    Send webhook notification to bridge about agent completion.
    """
    webhook_url = run.get("webhook_url")
    if not webhook_url:
        logger.warning(f"[{run['run_id']}] No webhook URL configured")
        return

    webhook_payload = {
        "run_id": run["run_id"],
        "status": run["status"],
        "ticket_id": run["ticket_id"]
    }

    # Add success fields
    if run["status"] == "completed":
        webhook_payload.update({
            "pr_url": run.get("pr_url"),
            "pr_number": run.get("pr_number"),
            "branch_name": run.get("branch_name"),
            "commit_sha": run.get("commit_sha"),
            "agent_analysis": (
                f"Successfully fixed {run['ticket_id']}: {run['ticket_summary']}. "
                f"Updated files: src/main.py, tests/test_main.py"
            ),
            "files_changed": ["src/main.py", "tests/test_main.py"],
            "completed_at": run.get("completed_at")
        })
    elif run["status"] == "failed":
        webhook_payload["error_message"] = run.get("error_message")

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"[{run['run_id']}] Sending webhook to {webhook_url}")
            logger.debug(f"[{run['run_id']}] Webhook payload: {webhook_payload}")

            response = await client.post(
                webhook_url,
                json=webhook_payload,
                timeout=10.0
            )

            if response.status_code in [200, 201, 204]:
                logger.info(f"[{run['run_id']}] Webhook sent successfully: {response.status_code}")
            else:
                logger.warning(
                    f"[{run['run_id']}] Webhook returned {response.status_code}: {response.text}"
                )

    except httpx.TimeoutException:
        logger.error(f"[{run['run_id']}] Webhook timeout")
    except Exception as e:
        logger.error(f"[{run['run_id']}] Webhook failed: {e}")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Mock AgentHQ Server")
    print("=" * 60)
    print("Starting server on http://localhost:8001")
    print()
    print("Configuration for your bridge:")
    print("  AGENTHQ_BASE_URL=http://localhost:8001")
    print("  AGENTHQ_MOCK_MODE=false")
    print("  AGENTHQ_API_KEY=any_value_works")
    print()
    print("Endpoints:")
    print("  POST /v1/agents/runs - Create agent run")
    print("  GET  /v1/agents/runs/{run_id} - Get run status")
    print("  POST /v1/agents/runs/{run_id}/cancel - Cancel run")
    print("  GET  /v1/agents/runs - List all runs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
