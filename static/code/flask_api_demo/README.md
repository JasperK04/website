# Flask API Demo

A production-ready REST API built with Flask, featuring JWT-style authentication,
rate limiting, and clean architecture using dataclasses.

## Features

- Token-based authentication via HMAC
- Sliding-window rate limiting (100 req/min per IP)
- Task CRUD endpoints
- Input validation and error handling
- Modular design with separate auth, models, and app layers

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/login` | No | Get auth token |
| GET | `/api/tasks` | Yes | List all tasks |
| POST | `/api/tasks` | Yes | Create task |
| GET | `/api/tasks/<id>` | Yes | Get single task |
| PUT | `/api/tasks/<id>` | Yes | Update task |

## Quick Start

```bash
pip install flask
python app.py
```

## Authentication

POST to `/api/login` with:
```json
{ "username": "admin", "password": "password123" }
```

Use the returned token in subsequent requests:
```
Authorization: Bearer <token>
```

## Task Status Values

- `pending` (default)
- `in_progress`
- `done`
- `cancelled`
