#!/usr/bin/env bash
set -euo pipefail
python -m pytest -q
python -m compileall -q app notebooks genie
