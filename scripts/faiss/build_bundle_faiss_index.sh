#!/usr/bin/env bash
# Local one-shot build for optional bundle FAISS index (PLAN_GAP §14 #12).
# Same defaults as .github/workflows/bundle_faiss_index.yml.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_ROOT="${1:-$ROOT}"
cd "$REPO_ROOT"
poetry install --with faiss
poetry run python scripts/faiss/build_bundle_faiss_index.py --repo-root "$REPO_ROOT"
