#!/bin/bash
set -e

cd "$(dirname "$0")"
source .venv/bin/activate

echo "=== AgentMemory PyPI Publisher ==="
echo ""

# Prompt for token securely (hidden input)
read -s -p "Paste your PyPI API token: " PYPI_TOKEN
echo ""

if [ -z "$PYPI_TOKEN" ]; then
    echo "Error: No token provided."
    exit 1
fi

# Clean old builds
rm -rf dist/

# Build
echo "Building..."
python -m build --quiet

# Upload
echo "Uploading to PyPI..."
python -m twine upload dist/* \
    --username __token__ \
    --password "$PYPI_TOKEN" \
    --non-interactive

echo ""
echo "Published! Install with: pip install memwright"
