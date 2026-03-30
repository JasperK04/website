"""
Flask API Demo - Main Application
A production-ready REST API with JWT auth and rate limiting.
"""
from flask import Flask, jsonify, request, abort
from functools import wraps
import time
import hashlib
import hmac
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# In-memory rate limiter (use Redis in production)
RATE_LIMIT = {}
RATE_LIMIT_MAX = 100  # requests per minute

# Simple in-memory user store (use database in production)
USERS = {
    "admin": hashlib.sha256(b"password123").hexdigest(),
}

TASKS = []
TASK_ID_COUNTER = 1


def rate_limited(f):
    """Decorator to apply rate limiting per IP address."""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        window_start = now - 60

        if ip not in RATE_LIMIT:
            RATE_LIMIT[ip] = []

        # Clean old requests
        RATE_LIMIT[ip] = [t for t in RATE_LIMIT[ip] if t > window_start]

        if len(RATE_LIMIT[ip]) >= RATE_LIMIT_MAX:
            return jsonify({"error": "Rate limit exceeded"}), 429

        RATE_LIMIT[ip].append(now)
        return f(*args, **kwargs)
    return decorated


def require_auth(f):
    """Decorator to require a valid token in the Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or not validate_token(token):
            abort(401)
        return f(*args, **kwargs)
    return decorated


def validate_token(token: str) -> bool:
    """Validate a simple HMAC token."""
    expected = hmac.new(
        app.config['SECRET_KEY'].encode(),
        b"authenticated",
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(token, expected)


def make_token() -> str:
    """Generate an authentication token."""
    return hmac.new(
        app.config['SECRET_KEY'].encode(),
        b"authenticated",
        hashlib.sha256
    ).hexdigest()


@app.route('/api/login', methods=['POST'])
@rate_limited
def login():
    """Authenticate a user and return a token."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    username = data.get('username', '')
    password = data.get('password', '')
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if username in USERS and hmac.compare_digest(USERS[username], password_hash):
        return jsonify({"token": make_token(), "user": username})

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/api/tasks', methods=['GET'])
@rate_limited
@require_auth
def get_tasks():
    """Return all tasks, with optional status filter."""
    status = request.args.get('status')
    result = TASKS if not status else [t for t in TASKS if t['status'] == status]
    return jsonify({"tasks": result, "count": len(result)})


@app.route('/api/tasks', methods=['POST'])
@rate_limited
@require_auth
def create_task():
    """Create a new task."""
    global TASK_ID_COUNTER
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({"error": "Title is required"}), 400

    task = {
        "id": TASK_ID_COUNTER,
        "title": data['title'],
        "description": data.get('description', ''),
        "status": "pending",
        "created_at": time.time(),
        "tags": data.get('tags', []),
    }
    TASKS.append(task)
    TASK_ID_COUNTER += 1
    return jsonify(task), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@rate_limited
@require_auth
def get_task(task_id: int):
    """Return a single task by ID."""
    task = next((t for t in TASKS if t['id'] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@rate_limited
@require_auth
def update_task(task_id: int):
    """Update a task's status or description."""
    task = next((t for t in TASKS if t['id'] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json() or {}
    if 'status' in data:
        task['status'] = data['status']
    if 'description' in data:
        task['description'] = data['description']
    if 'title' in data:
        task['title'] = data['title']

    return jsonify(task)


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized"}), 401


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=5000)
