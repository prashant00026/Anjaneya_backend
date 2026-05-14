#!/usr/bin/env bash
# Ongoing deploy — run as jarvis from /home/jarvis/anjaneya:
#   bash deploy/scripts/deploy.sh
# Override the branch with:  DEPLOY_BRANCH=some-branch bash deploy/scripts/deploy.sh

set -euo pipefail

APP_DIR="/home/jarvis/anjaneya"
VENV="$APP_DIR/venv"
BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

echo "==> Pulling latest from $BRANCH"
git fetch --all --prune
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "==> Installing dependencies"
"$VENV/bin/pip" install --upgrade pip --quiet
"$VENV/bin/pip" install -r requirements.txt --quiet

echo "==> Running migrations"
"$VENV/bin/python" manage.py migrate --noinput

echo "==> Collecting static files"
"$VENV/bin/python" manage.py collectstatic --noinput --clear

echo "==> Deploy check"
"$VENV/bin/python" manage.py check --deploy || echo "WARNING: deploy check has warnings"

echo "==> Reloading gunicorn"
sudo systemctl reload anjaneya.service

sleep 3
echo "==> Verifying health"
if curl -fsS http://127.0.0.1/health/ready/ > /dev/null; then
    echo "Deploy successful"
else
    echo "Health check FAILED"
    sudo systemctl status anjaneya.service --no-pager
    exit 1
fi
