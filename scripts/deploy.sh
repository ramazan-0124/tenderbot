#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-178.105.93.245}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PATH="${SERVER_PATH:-/opt/tender-smart-search}"
SERVICE_NAME="${SERVICE_NAME:-tender-smart-search}"
BRANCH="${BRANCH:-main}"

commit_message="${1:-Deploy $(date '+%Y-%m-%d %H:%M:%S')}"

echo "1/5 Checking Python files..."
PYTHONPYCACHEPREFIX=/tmp/python-cache python3 -m py_compile app/main.py app/smart_search.py

echo "2/5 Preparing git commit..."
git add .gitignore README.md app deploy scripts

if git diff --cached --quiet; then
  echo "No local changes to commit."
else
  git commit -m "$commit_message"
fi

echo "3/5 Pushing to GitHub..."
git push origin "$BRANCH"

echo "4/5 Updating server..."
ssh "${SERVER_USER}@${SERVER_HOST}" \
  "cd '${SERVER_PATH}' && git pull --ff-only origin '${BRANCH}' && systemctl restart '${SERVICE_NAME}'"

echo "5/5 Verifying service..."
ssh "${SERVER_USER}@${SERVER_HOST}" \
  "systemctl is-active '${SERVICE_NAME}' && curl -fsS 'http://127.0.0.1:8090/' >/dev/null"

echo "Deploy complete: https://tender.capi.garden"

