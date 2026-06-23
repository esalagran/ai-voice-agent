# Prosper Challenge Solution

## Overview

The solution keeps the voice agent and EHR service separate. The agent talks to
the EHR over HTTP using `EHR_BASE_URL`, which keeps the integration close to a
real external system boundary.

## Shared RPC Contract

`ehr_service/rpc.py` defines the request and response models for every EHR
operation. The FastAPI service uses those models for endpoint validation, and
the agent client uses the same models when making tool calls.

This avoids duplicating patient, slot, and appointment shapes across the API and
agent code. When an RPC shape changes, there is one contract to update.

The EHR exposes JSON RPC-style POST endpoints:

- `POST /rpc/find_patient`
- `POST /rpc/create_patient`
- `POST /rpc/list_availability_slots`
- `POST /rpc/create_appointment`
- `POST /rpc/list_patient_appointments`
- `POST /rpc/cancel_appointment`

## Agent Modularization

Bot-specific EHR code lives under `agent/`:

- `agent/prompts.py` contains the clinic prompt and startup prompt.
- `agent/ehr_client.py` wraps async HTTP calls and maps EHR failures into tool errors.
- `agent/ehr_tools.py` registers the shared RPC operations as Pipecat tools.

`bot.py` stays focused on pipeline composition: transport, model services,
context, aggregators, and lifecycle cleanup.

## Persistence And Cancellation

The EHR uses SQLAlchemy with SQLite by default, so local patient and appointment
data survives process restarts.

Cancellation uses `list_patient_appointments` first, so callers can choose an
appointment by time instead of knowing an internal appointment ID.

## Running The Agent

Run the full local flow with:

```bash
scripts/run-agent-e2e.sh
```

The script seeds the EHR, starts the EHR API, and starts the voice agent with
`EHR_BASE_URL` set.

The seeded availability uses `slot_day = date(2030, 1, 15)`, so January 15,
2030 is the known day with available slots.

## Validation

Run:

```bash
uv run pytest
uv run ruff check .
```
