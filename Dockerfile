
FROM ghcr.io/benoitc/gunicorn:latest

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml .python-version ./

USER root

RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

RUN mkdir -p /app/logs

CMD ["uv", "run", "-m", "gunicorn", "-w", "2", "-b", "0.0.0.0:80", "run:app"]
