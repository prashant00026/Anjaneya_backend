#!/usr/bin/env bash
# Pre-deploy sanity checks — run on the dev machine before pushing.
#
# Adapted to this project's actual toolchain: the test runner is Django's
# `manage.py test` (85 TestCase tests across the apps), not pytest. The
# pytest/ruff/bandit lines from the deployment brief are left commented —
# they require the dev toolchain from requirements-dev.txt plus config
# (pytest.ini / pyproject.toml) that this project doesn't ship yet.
#
# On Windows run under Git Bash, or run the equivalent commands in PowerShell.

set -euo pipefail

echo "==> Tests (Django test runner)"
python manage.py test catalog projects enquiries team testimonials site_settings notifications

echo "==> Missing migrations"
python manage.py makemigrations --check --dry-run

echo "==> Production deploy check"
# LOG_DIR is overridden so the prod settings module imports cleanly on a
# machine without /var/log/anjaneya (the file handlers use delay=True too).
LOG_DIR=./logs DJANGO_SETTINGS_MODULE=core.settings.production \
    python manage.py check --deploy

# --- Optional: full lint / security suite -------------------------------
# Requires `pip install -r requirements-dev.txt` plus ruff/bandit config.
# Uncomment once that tooling is wired up:
#
# echo "==> Lint"
# ruff check .
#
# echo "==> Security"
# bandit -r apps/
#
# echo "==> Type check"
# mypy apps/

echo "All pre-deploy checks passed"
