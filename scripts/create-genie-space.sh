#!/usr/bin/env bash
set -euo pipefail
: "${DATABRICKS_PROFILE:?Set DATABRICKS_PROFILE to a configured profile name}"
: "${DATABRICKS_USER_EMAIL:?Set DATABRICKS_USER_EMAIL to your Databricks email}"
: "${DATABRICKS_WAREHOUSE_ID:?Set DATABRICKS_WAREHOUSE_ID to the SQL warehouse Genie should use}"
CATALOG="${DATABRICKS_CATALOG:-workspace}"
SCHEMA="${DATABRICKS_SCHEMA:-grocery_copilot}"
PARENT="/Workspace/Users/${DATABRICKS_USER_EMAIL}/genie"
REQUEST="$(mktemp)"
trap 'rm -f "$REQUEST"' EXIT

python3 genie/build_space.py --catalog "$CATALOG" --schema "$SCHEMA" \
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" --parent-path "$PARENT" > "$REQUEST"
databricks workspace mkdirs "$PARENT" --profile "$DATABRICKS_PROFILE"
databricks genie create-space --json "@$REQUEST" --profile "$DATABRICKS_PROFILE"
