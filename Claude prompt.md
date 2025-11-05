You are an expert in AI-driven DevOps automation and GitHub AgentHQ workflows.
Build me a complete, working POC project that does the following end-to-end:

Goal:
When a JIRA ticket is labeled with copilot-fix, it automatically triggers an automation that:

Reads the JIRA ticket ID and description

Creates a branch in GitHub named fix/<TICKET_ID>

Generates a simple HTML file named <TICKET_ID>.html containing the ticket ID in <h1> and the ticket description in <p>

Commits and pushes this file to GitHub

Creates a pull request (PR) in the repo

Posts the PR URL as a comment back to the JIRA issue

Architecture requirements:

The bridge service should be written in FastAPI (Python)

Use GitHub REST API and JIRA REST API for communication

GitHub PR creation should be automated via GitHub Actions (repository_dispatch event)

Use ngrok for local testing of webhooks

Include clear instructions for .env setup and configuration of webhooks on both sides (JIRA and GitHub)

Deliverables to generate:

Complete folder structure:

/copilot-fix-bridge
  ├── main.py
  ├── .env.sample
  ├── requirements.txt
  ├── README.md
  └── .github/workflows/agent-pr.yml


main.py: FastAPI app with two endpoints:

/jira-webhook: handles JIRA “issue updated” event when label = copilot-fix, triggers GitHub dispatch

/github-pr: handles GitHub PR webhook and posts PR link back to JIRA

agent-pr.yml: GitHub workflow that:

Creates a branch fix/<ticket_id>

Creates the HTML file

Commits & pushes changes

Opens a PR

README.md: step-by-step setup instructions for:

JIRA webhook config (trigger on label copilot-fix)

GitHub PAT setup & repo dispatch config

ngrok local tunnel testing

Optional Render/Fly.io deployment

Extra notes:

Keep the code simple, clear, and production-friendly.

Use environment variables for all tokens and base URLs.

Show the example .env.sample content with placeholders.

Add basic print logs for visibility.

Make sure the README provides copy-paste-ready CLI commands to run locally.

Output everything as a single well-formatted code block with explanations in between sections.