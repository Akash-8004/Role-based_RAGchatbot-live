#!/usr/bin/env sh
set -eu

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
STREAMLIT_PORT="${PORT:-8501}"

export API_BASE_URL="${API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"

uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" &
BACKEND_PID="$!"

cleanup() {
  kill "${BACKEND_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

streamlit run streamlit_app/app.py \
  --server.address 0.0.0.0 \
  --server.port "${STREAMLIT_PORT}" \
  --server.headless true \
  --browser.gatherUsageStats false
