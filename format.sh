#!/bin/bash
# Format all Python files using ruff

echo "Formatting code with ruff..."
ruff format .

echo "Checking and fixing linting issues..."
ruff check --fix .

echo "Done! Code formatted and linted."

