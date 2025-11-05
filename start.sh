#!/bin/bash

# Copilot Fix Bridge - Quick Start Script

echo "=========================================="
echo "  Copilot Fix Bridge - Starting Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.sample to .env and fill in your credentials:"
    echo ""
    echo "  cp .env.sample .env"
    echo "  nano .env"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check environment variables
echo "Checking configuration..."
python3 - << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

required = {
    'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
    'GITHUB_REPO': os.getenv('GITHUB_REPO'),
    'JIRA_BASE_URL': os.getenv('JIRA_BASE_URL'),
    'JIRA_EMAIL': os.getenv('JIRA_EMAIL'),
    'JIRA_API_TOKEN': os.getenv('JIRA_API_TOKEN')
}

missing = [k for k, v in required.items() if not v or v.startswith('your_') or v.startswith('your-')]

if missing:
    print(f"⚠ WARNING: Missing or incomplete configuration:")
    for key in missing:
        print(f"  - {key}")
    print("\nPlease update your .env file with actual values")
else:
    print("✓ All required environment variables are set")
EOF

echo ""
echo "=========================================="
echo "  Starting FastAPI Server"
echo "=========================================="
echo ""
echo "Server will be available at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python main.py
