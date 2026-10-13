#!/usr/bin/env bash
set -euo pipefail
: "${DATABRICKS_PROFILE:?Set DATABRICKS_PROFILE to a configured profile name}"
: "${DATABRICKS_USER_EMAIL:?Set DATABRICKS_USER_EMAIL to your Databricks email}"
: "${DATABRICKS_APP_NAME:?Set DATABRICKS_APP_NAME to your existing Databricks App name}"
TARGET="/Workspace/Users/${DATABRICKS_USER_EMAIL}/databricks-demo-factory"
databricks sync . "$TARGET" --profile "$DATABRICKS_PROFILE" --exclude '.venv/**' --exclude '.git/**' --exclude 'tests/**'
databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$TARGET" --profile "$DATABRICKS_PROFILE"
