#!/usr/bin/env bash
set -euo pipefail

EHR_HOST="${EHR_HOST:-127.0.0.1}"
EHR_PORT="${EHR_PORT:-7861}"
EHR_BASE_URL="${EHR_BASE_URL:-http://${EHR_HOST}:${EHR_PORT}}"
EHR_DATABASE_URL="${EHR_DATABASE_URL:-sqlite:///./ehr.db}"

cleanup() {
  if [ -n "${ehr_pid:-}" ] && kill -0 "${ehr_pid}" 2>/dev/null; then
    kill "${ehr_pid}"
    wait "${ehr_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Seeding EHR demo data"
EHR_DATABASE_URL="${EHR_DATABASE_URL}" uv run python ehr.py --seed

echo "Starting EHR at ${EHR_BASE_URL}"
EHR_DATABASE_URL="${EHR_DATABASE_URL}" uv run python ehr.py --host "${EHR_HOST}" --port "${EHR_PORT}" &
ehr_pid="$!"

until curl -fsS "${EHR_BASE_URL}/health" >/dev/null; do
  sleep 0.2
done

echo "Starting voice agent"
echo "Open http://localhost:7860 and click Connect"
EHR_BASE_URL="${EHR_BASE_URL}" uv run bot.py
