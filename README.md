# MAX Taxi Chatbot Backend

Production-ready MVP backend for a taxi ordering chatbot built with FastAPI, SQLAlchemy, SQLite, and a dedicated MAX messenger adapter layer. The app works immediately in mock mode and is structured so a real MAX API can replace the adapter internals later without touching business logic.

## Features

- FastAPI webhook endpoint: `POST /webhook/max`
- Dedicated MAX adapter for parsing and sending messages
- SQLite + SQLAlchemy ORM persistence
- Order flow for riders: start → order taxi → pickup → destination → order saved
- Driver broadcast + accept flow with single-assignment protection
- Mock MAX mode for Postman/manual testing
- Environment-based configuration and structured logging

## Project structure

```text
/app
  /api        webhook and mock endpoints
  /adapters   MAX adapter abstraction
  /services   taxi ordering business logic
  /models     SQLAlchemy ORM entities
  /schemas    Pydantic DTOs
  /core       config, logging, database
```

## Requirements

- Python 3.11+

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file if needed:

```env
MAX_BOT_TOKEN=mock-token
MAX_WEBHOOK_SECRET=mock-secret
DATABASE_URL=sqlite:///./max_taxi.db
MOCK_MAX_MODE=true
LOG_LEVEL=INFO
```

## Run the server

```bash
uvicorn app.main:app --reload
```

## How MAX integration works

The MAX-specific behavior is isolated in `app/adapters/max_adapter.py`.

Current adapter responsibilities:
- parse incoming webhook JSON into an internal message contract
- expose `send_message(user_id, text)`
- expose `send_buttons(user_id, text, buttons)`
- store outgoing messages in an in-memory mock outbox for testing

To connect a real MAX messenger later, replace the outgoing mock implementation and the webhook payload parsing rules inside the adapter.

## Test the webhook in mock mode

### 1. Seed mock drivers

```bash
curl -X POST http://127.0.0.1:8000/mock/seed-drivers
```

### 2. Start chat as user

```bash
curl -X POST http://127.0.0.1:8000/webhook/max \
  -H 'Content-Type: application/json' \
  -H 'x-max-secret: mock-secret' \
  -d '{
    "sender": {"id": "user_1"},
    "message": {"text": "start"}
  }'
```

### 3. Create an order

```bash
curl -X POST http://127.0.0.1:8000/webhook/max \
  -H 'Content-Type: application/json' \
  -H 'x-max-secret: mock-secret' \
  -d '{"sender": {"id": "user_1"}, "message": {"text": "order taxi"}}'

curl -X POST http://127.0.0.1:8000/webhook/max \
  -H 'Content-Type: application/json' \
  -H 'x-max-secret: mock-secret' \
  -d '{"sender": {"id": "user_1"}, "message": {"text": "1 Main Street"}}'

curl -X POST http://127.0.0.1:8000/webhook/max \
  -H 'Content-Type: application/json' \
  -H 'x-max-secret: mock-secret' \
  -d '{"sender": {"id": "user_1"}, "message": {"text": "Airport Terminal A"}}'
```

### 4. Inspect outgoing mock MAX messages

```bash
curl http://127.0.0.1:8000/mock/outbox
```

You will see:
- responses sent back to the rider
- order offers sent to seeded drivers

### 5. Simulate driver acceptance

```bash
curl -X POST http://127.0.0.1:8000/webhook/max \
  -H 'Content-Type: application/json' \
  -H 'x-max-secret: mock-secret' \
  -d '{
    "sender": {"id": "driver_alice"},
    "payload": {"action": "accept_order:1"}
  }'
```

### 6. Inspect saved orders

```bash
curl http://127.0.0.1:8000/mock/orders
```

## Concurrency / single-driver acceptance

When a driver accepts an order, the service performs an atomic conditional update that only succeeds while the order is still in `new` state and has no assigned driver. This works in SQLite today and maps cleanly to stronger row-level locking strategies when moving to PostgreSQL.

## Notes for production hardening

- Replace SQLite with PostgreSQL for true row-level locking under heavy concurrency
- Add Alembic migrations
- Add authentication/signature verification required by the real MAX API
- Replace in-memory outbox with real MAX API HTTP client calls
- Add retry and dead-letter handling for outbound delivery
