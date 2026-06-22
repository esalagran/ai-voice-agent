#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:7861}"
SLOT_DATE="${SLOT_DATE:-2030-01-15}"
STAMP="$(date +%s)"
NAME="Smoke Test ${STAMP}"
DOB="1990-01-02"

json_field() {
  python3 -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}

json_len() {
  python3 -c 'import json, sys; print(len(json.load(sys.stdin)))'
}

echo "health"
curl -fsS "${BASE_URL}/health"
echo

echo "create_patient"
patient="$(
  curl -fsS -X POST "${BASE_URL}/rpc/create_patient" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${NAME}\",\"date_of_birth\":\"${DOB}\",\"phone\":\"+1-555-0199\",\"email\":\"smoke@example.com\"}"
)"
echo "${patient}"
patient_id="$(printf '%s' "${patient}" | json_field id)"

echo "find_patient"
curl -fsS -X POST "${BASE_URL}/rpc/find_patient" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${NAME}\",\"date_of_birth\":\"${DOB}\"}"
echo

echo "list_availability_slots"
slots="$(
  curl -fsS -X POST "${BASE_URL}/rpc/list_availability_slots" \
    -H "Content-Type: application/json" \
    -d "{\"from_date\":\"${SLOT_DATE}\"}"
)"
echo "${slots}"
slot_id="$(
  printf '%s' "${slots}" | python3 -c '
import json, sys
slots = json.load(sys.stdin)
if not slots:
    raise SystemExit("no availability slots; run: uv run python ehr.py --seed")
print(slots[0]["id"])
'
)"

echo "create_appointment"
appointment="$(
  curl -fsS -X POST "${BASE_URL}/rpc/create_appointment" \
    -H "Content-Type: application/json" \
    -d "{\"patient_id\":${patient_id},\"slot_id\":${slot_id}}"
)"
echo "${appointment}"
appointment_id="$(printf '%s' "${appointment}" | json_field id)"

echo "list_patient_appointments"
appointments="$(
  curl -fsS -X POST "${BASE_URL}/rpc/list_patient_appointments" \
    -H "Content-Type: application/json" \
    -d "{\"patient_id\":${patient_id}}"
)"
echo "${appointments}"
appointment_count="$(printf '%s' "${appointments}" | json_len)"
if [ "${appointment_count}" -lt 1 ]; then
  echo "expected at least one booked appointment" >&2
  exit 1
fi

echo "cancel_appointment"
curl -fsS -X POST "${BASE_URL}/rpc/cancel_appointment" \
  -H "Content-Type: application/json" \
  -d "{\"appointment_id\":${appointment_id}}"
echo

echo "list_patient_appointments_after_cancel"
appointments_after_cancel="$(
  curl -fsS -X POST "${BASE_URL}/rpc/list_patient_appointments" \
    -H "Content-Type: application/json" \
    -d "{\"patient_id\":${patient_id}}"
)"
echo "${appointments_after_cancel}"
appointment_count_after_cancel="$(printf '%s' "${appointments_after_cancel}" | json_len)"
if [ "${appointment_count_after_cancel}" -ne 0 ]; then
  echo "expected no booked appointments after cancel" >&2
  exit 1
fi
