#!/bin/bash
# Script to run GitHub Actions test hooks

set -e

echo "Installing dependencies for test hooks..."
uv add pyyaml

echo "Running GitHub Actions validation..."
uv run python test_hooks.py

echo "Running with JSON output..."
uv run python test_hooks.py --json > github_actions_report.json

echo "Report saved to github_actions_report.json"
echo "Done!"
