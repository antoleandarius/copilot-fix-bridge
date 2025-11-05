#!/usr/bin/env python3
"""
Test script to validate Copilot Fix Bridge setup
Run this before starting the service to ensure everything is configured correctly
"""

import os
import sys
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def check_env_var(name, required=True):
    """Check if environment variable is set and valid"""
    value = os.getenv(name)

    if not value:
        if required:
            print_error(f"{name} is not set")
            return False
        else:
            print_warning(f"{name} is not set (optional)")
            return True

    # Check for placeholder values
    placeholder_indicators = ['your_', 'your-', 'example', 'placeholder']
    if any(indicator in value.lower() for indicator in placeholder_indicators):
        print_error(f"{name} contains placeholder value: {value[:30]}...")
        return False

    print_success(f"{name} is configured")
    return True

def validate_github_token():
    """Validate GitHub token by making a test API call"""
    token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')

    if not token or not repo:
        return False

    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json'
        }
        response = requests.get(
            f'https://api.github.com/repos/{repo}',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            print_success(f"GitHub API connection successful")
            repo_data = response.json()
            print(f"  └─ Repository: {repo_data.get('full_name')}")
            print(f"  └─ Private: {repo_data.get('private')}")
            return True
        elif response.status_code == 404:
            print_error(f"Repository '{repo}' not found or token doesn't have access")
            return False
        elif response.status_code == 401:
            print_error("GitHub token is invalid")
            return False
        else:
            print_error(f"GitHub API error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Failed to connect to GitHub API: {str(e)}")
        return False

def validate_jira_connection():
    """Validate JIRA credentials by making a test API call"""
    base_url = os.getenv('JIRA_BASE_URL')
    email = os.getenv('JIRA_EMAIL')
    token = os.getenv('JIRA_API_TOKEN')

    if not all([base_url, email, token]):
        return False

    # Remove trailing slash if present
    base_url = base_url.rstrip('/')

    try:
        response = requests.get(
            f'{base_url}/rest/api/3/myself',
            auth=(email, token),
            timeout=10
        )

        if response.status_code == 200:
            print_success("JIRA API connection successful")
            user_data = response.json()
            print(f"  └─ User: {user_data.get('displayName')}")
            print(f"  └─ Email: {user_data.get('emailAddress')}")
            return True
        elif response.status_code == 401:
            print_error("JIRA credentials are invalid")
            return False
        else:
            print_error(f"JIRA API error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Failed to connect to JIRA API: {str(e)}")
        return False

def check_github_repo_format():
    """Validate GitHub repo format"""
    repo = os.getenv('GITHUB_REPO')
    if not repo:
        return False

    if repo.count('/') != 1:
        print_error(f"GITHUB_REPO format is invalid: '{repo}'")
        print("  Expected format: owner/repository")
        return False

    owner, repo_name = repo.split('/')
    if not owner or not repo_name:
        print_error(f"GITHUB_REPO has empty owner or repository name")
        return False

    print_success(f"GitHub repository format is valid: {repo}")
    return True

def check_jira_url_format():
    """Validate JIRA URL format"""
    url = os.getenv('JIRA_BASE_URL')
    if not url:
        return False

    if not url.startswith('https://'):
        print_error(f"JIRA_BASE_URL should start with https://")
        return False

    if url.endswith('/'):
        print_warning(f"JIRA_BASE_URL should not end with '/' (will be handled automatically)")

    print_success(f"JIRA URL format is valid")
    return True

def check_workflow_file():
    """Check if GitHub Actions workflow file exists"""
    workflow_path = '.github/workflows/agent-pr.yml'

    if os.path.exists(workflow_path):
        print_success(f"GitHub Actions workflow file exists: {workflow_path}")
        return True
    else:
        print_error(f"GitHub Actions workflow file not found: {workflow_path}")
        return False

def main():
    print_header("Copilot Fix Bridge - Setup Validation")

    # Track overall status
    all_checks_passed = True

    # Check if .env exists
    if not os.path.exists('.env'):
        print_error(".env file not found")
        print("\nPlease create .env file:")
        print("  cp .env.sample .env")
        print("  nano .env")
        sys.exit(1)

    print_success(".env file found")

    # Environment Variables Check
    print_header("Environment Variables")

    checks = [
        ('GITHUB_TOKEN', True),
        ('GITHUB_REPO', True),
        ('JIRA_BASE_URL', True),
        ('JIRA_EMAIL', True),
        ('JIRA_API_TOKEN', True),
        ('WEBHOOK_SECRET', False),
        ('PORT', False)
    ]

    for var_name, required in checks:
        if not check_env_var(var_name, required):
            all_checks_passed = False

    # Format Validation
    print_header("Configuration Format Validation")

    if not check_github_repo_format():
        all_checks_passed = False

    if not check_jira_url_format():
        all_checks_passed = False

    # File Structure Check
    print_header("File Structure")

    if not check_workflow_file():
        all_checks_passed = False

    # API Connectivity Tests
    print_header("API Connectivity Tests")

    if not validate_github_token():
        all_checks_passed = False

    if not validate_jira_connection():
        all_checks_passed = False

    # Final Summary
    print_header("Summary")

    if all_checks_passed:
        print_success("All checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("  1. Start the service: ./start.sh")
        print("  2. Setup ngrok: ngrok http 8000")
        print("  3. Configure webhooks in JIRA and GitHub")
        print("  4. Test with a JIRA ticket labeled 'copilot-fix'")
        sys.exit(0)
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Update .env with valid credentials")
        print("  - Ensure GITHUB_REPO format is: owner/repo")
        print("  - Verify GitHub token has 'repo' and 'workflow' scopes")
        print("  - Check JIRA API token is valid")
        sys.exit(1)

if __name__ == '__main__':
    main()
