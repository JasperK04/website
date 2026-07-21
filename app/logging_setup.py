"""
Logging setup and lightweight analytics helpers.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from ipaddress import ip_address
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import current_app, g, render_template, request, session


def setup_logging(app) -> None:
    """Configure file loggers and register request hooks."""
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)

    loggers = {
        "analytics": _build_logger(app, "analytics", log_dir / "analytics.log"),
        "performance": _build_logger(app, "performance", log_dir / "performance.log"),
        "errors": _build_logger(app, "errors", log_dir / "errors.log"),
    }
    app.extensions["loggers"] = loggers
    app.extensions["geoip_reader"] = _build_geoip_reader(app)

    app.before_request(_start_timer)
    app.after_request(_after_request)
    app.register_error_handler(404, _handle_404)
    app.register_error_handler(500, _handle_500)


def log_search_query(query: str, has_results: bool, result_count: int) -> None:
    """Log a search query event for analytics."""
    cleaned = (query or "").strip()
    if not cleaned:
        return
    _log_event(
        "analytics",
        {
            "event": "search",
            "query": cleaned,
            "query_length": len(cleaned),
            "has_results": has_results,
            "result_count": result_count,
            "path": request.path,
            "referrer": request.referrer,
        },
    )


def log_cv_download() -> None:
    """Log a CV download event and include an approximate location when available."""
    session_id, page_count = _get_session_state()
    payload = {
        "event": "cv_download",
        "path": request.path,
        "referrer": request.referrer,
        "session_id": session_id,
        "page_count": page_count,
    }

    geoip = _lookup_geoip_location(_get_client_ip())
    if geoip:
        payload.update(geoip)

    _log_event("analytics", payload)


def _build_logger(app, name: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(f"website.{name}")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        path,
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))

    if not _handler_registered(logger, handler):
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def _handler_registered(logger: logging.Logger, handler: RotatingFileHandler) -> bool:
    for existing in logger.handlers:
        if (
            isinstance(existing, RotatingFileHandler)
            and existing.baseFilename == handler.baseFilename
        ):
            return True
    return False


def _start_timer() -> None:
    g.request_start = time.perf_counter()


def _build_geoip_reader(app):
    db_path = Path(app.config.get("GEOIP_DB_PATH", ""))
    if not db_path or not db_path.is_file():
        return None

    try:
        from geoip2.database import Reader
    except ImportError:
        return None

    try:
        return Reader(str(db_path))
    except Exception:
        return None


def _after_request(response):
    _log_slow_request(response)
    _log_page_view(response)
    return response


def _log_page_view(response) -> None:
    if (
        request.method != "GET"
        or response.mimetype != "text/html"
        or response.status_code >= 400
    ):
        return
    if not request.endpoint or not request.endpoint.startswith("main."):
        return

    session_id, page_count = _get_session_state()
    page_count += 1
    session["analytics_page_count"] = page_count

    _log_event(
        "analytics",
        {
            "event": "page_view",
            "path": request.path,
            "referrer": request.referrer,
            "session_id": session_id,
            "page_count": page_count,
            "bounce_candidate": page_count == 1,
        },
    )


def _get_session_state() -> tuple[str, int]:
    now = int(time.time())
    session_seconds = int(current_app.config["ANALYTICS_SESSION_SECONDS"])
    last_seen = session.get("analytics_last_seen")

    if not last_seen or now - int(last_seen) > session_seconds:
        session["analytics_id"] = uuid.uuid4().hex
        session["analytics_page_count"] = 0
        session["analytics_session_start"] = now

    session["analytics_last_seen"] = now
    return session["analytics_id"], session.get("analytics_page_count", 0)


def _log_slow_request(response) -> None:
    start = getattr(g, "request_start", None)
    if start is None:
        return
    duration_ms = (time.perf_counter() - start) * 1000
    threshold_ms = int(current_app.config["LOG_SLOW_TTFB_MS"])
    if duration_ms < threshold_ms:
        return

    _log_event(
        "performance",
        {
            "event": "slow_request",
            "path": request.path,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "referrer": request.referrer,
        },
    )


def _handle_404(error):
    _log_event(
        "errors",
        {
            "event": "http_404",
            "path": request.path,
            "method": request.method,
            "referrer": request.referrer,
        },
    )
    return render_template("404.html"), 404


def _handle_500(error):
    _log_event(
        "errors",
        {
            "event": "http_500",
            "path": request.path,
            "method": request.method,
            "referrer": request.referrer,
        },
    )
    return render_template("500.html"), 500


def _get_client_ip() -> str | None:
    if request.remote_addr:
        return request.remote_addr
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    return None


def _lookup_geoip_location(client_ip: str | None) -> dict:
    if not client_ip:
        return {}

    try:
        ip_address(client_ip)
    except ValueError:
        return {}

    reader = current_app.extensions.get("geoip_reader")
    if reader is None:
        return {}

    try:
        lookup = reader.city(client_ip)
    except Exception:
        return {}

    country = lookup.country.names.get("en") if lookup.country.names else None
    region = (
        lookup.subdivisions.most_specific.names.get("en")
        if lookup.subdivisions
        else None
    )
    city = lookup.city.names.get("en") if lookup.city.names else None

    payload = {}
    if country:
        payload["geo_country"] = country
    if region:
        payload["geo_region"] = region
    if city:
        payload["geo_city"] = city

    location_parts = [part for part in (city, region, country) if part]
    if location_parts:
        payload["geo_location"] = ", ".join(location_parts)

    return payload


def _log_event(logger_key: str, payload: dict) -> None:
    logger = current_app.extensions.get("loggers", {}).get(logger_key)
    if not logger:
        return
    payload["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    logger.info(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
