#!/usr/bin/env bash
# One-time local dev setup for the two Python services. Requires python3-venv
# and python3-pip on the host (see docs — this repo's plan notes this as a
# host prerequisite, not something the app installs for you).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

setup_service() {
  local service_dir="$1"
  echo "--- Setting up $service_dir ---"
  python3 -m venv "$ROOT_DIR/$service_dir/.venv"
  "$ROOT_DIR/$service_dir/.venv/bin/pip" install --upgrade pip
  "$ROOT_DIR/$service_dir/.venv/bin/pip" install -e "$ROOT_DIR/packages/py-shared"
  "$ROOT_DIR/$service_dir/.venv/bin/pip" install -e "$ROOT_DIR/$service_dir"
}

setup_service "apps/api"
setup_service "apps/ai-orchestrator"

echo "Done. Activate with: source apps/api/.venv/bin/activate (or apps/ai-orchestrator)"
