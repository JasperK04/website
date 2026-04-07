"""
Flask CLI commands for log summaries.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import click
from flask import current_app


@click.command("logs-summary")
@click.option("--limit", default=10, show_default=True, help="Rows per section.")
def logs_summary(limit: int) -> None:
    """Summarize analytics, errors, and performance logs."""
    log_dir = Path(current_app.config["LOG_DIR"])

    analytics = _read_events(log_dir / "analytics.log")
    errors = _read_events(log_dir / "errors.log")
    performance = _read_events(log_dir / "performance.log")

    page_views = [e for e in analytics if e.get("event") == "page_view"]
    search_events = [e for e in analytics if e.get("event") == "search"]

    click.echo("\nAnalytics")
    click.echo("----------")
    click.echo(f"Total page views: {len(page_views)}")
    click.echo(f"Total searches: {len(search_events)}")
    click.echo(
        f"Distinct sessions: {len({e.get('session_id') for e in page_views if e.get('session_id')})}"
    )
    click.echo(f"Bounces: {len([e for e in page_views if e.get('bounce_candidate')])}")

    if page_views:
        top_pages = Counter(e.get("path") for e in page_views if e.get("path"))
        click.echo("\nTop pages")
        _render_counter(top_pages, limit)

    if search_events:
        top_queries = Counter(e.get("query") for e in search_events if e.get("query"))
        click.echo("\nTop search queries")
        _render_counter(top_queries, limit)

        no_result = [e for e in search_events if not e.get("has_results")]
        if no_result:
            click.echo("\nSearches with no results")
            missing = Counter(e.get("query") for e in no_result if e.get("query"))
            _render_counter(missing, limit)

    click.echo("\nErrors")
    click.echo("------")
    click.echo(f"404s: {len([e for e in errors if e.get('event') == 'http_404'])}")
    click.echo(f"500s: {len([e for e in errors if e.get('event') == 'http_500'])}")

    if errors:
        top_404 = Counter(
            e.get("path")
            for e in errors
            if e.get("event") == "http_404" and e.get("path")
        )
        if top_404:
            click.echo("\nTop 404 paths")
            _render_counter(top_404, limit)

    click.echo("\nPerformance")
    click.echo("-----------")
    click.echo(f"Slow requests: {len(performance)}")

    if performance:
        slow_paths = Counter(e.get("path") for e in performance if e.get("path"))
        click.echo("\nSlowest paths (count)")
        _render_counter(slow_paths, limit)

        sorted_perf = sorted(
            (
                e
                for e in performance
                if e.get("path") and e.get("duration_ms") is not None
            ),
            key=lambda e: e.get("duration_ms", 0),
            reverse=True,
        )[:limit]
        if sorted_perf:
            click.echo("\nSlowest requests (ms)")
            for entry in sorted_perf:
                click.echo(f"{entry.get('duration_ms'):>8}  {entry.get('path')}")


def _read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _render_counter(counter: Counter, limit: int) -> None:
    for key, count in counter.most_common(limit):
        click.echo(f"{count:>5}  {key}")
