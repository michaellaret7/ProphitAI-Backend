"""
Download Langfuse trace data and save to local JSON files by week.

Usage:
    python download_langfuse_data.py          # downloads last 30 days
    python download_langfuse_data.py 14       # downloads last 14 days

Saves files to langfuse_data/ directory, one file per week:
    langfuse_data/week_2026-04-07_to_2026-04-13.json
    langfuse_data/week_2026-04-14_to_2026-04-20.json
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.api.core.request_options import RequestOptions

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "langfuse_data"
REQUEST_OPTS = RequestOptions(timeout_in_seconds=120)


# ================================
# --> Helper funcs
# ================================

def serialize_observation(obs) -> dict:
    """Convert a Langfuse ObservationsView object to a serializable dict."""

    return {
        "id": getattr(obs, "id", None),
        "type": getattr(obs, "type", None),
        "name": getattr(obs, "name", None),
        "model": getattr(obs, "model", None),
        "level": getattr(obs, "level", None),
        "latency": getattr(obs, "latency", None),
        "usage_details": getattr(obs, "usage_details", None),
        "cost_details": getattr(obs, "cost_details", None),
        "calculated_total_cost": getattr(obs, "calculated_total_cost", None),
        "parent_observation_id": getattr(obs, "parent_observation_id", None),
    }


def serialize_trace(trace, observations: list) -> dict:
    """Convert a Langfuse trace + observations to a serializable dict."""

    return {
        "id": trace.id,
        "name": trace.name,
        "tags": trace.tags or [],
        "latency": trace.latency,
        "total_cost": trace.total_cost,
        "session_id": getattr(trace, "session_id", None),
        "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
        "observations": [serialize_observation(obs) for obs in observations],
    }


def get_week_boundaries(lookback_days: int) -> list[tuple[datetime, datetime, str]]:
    """Generate week boundaries from now going back lookback_days.

    Returns list of (start, end, filename_label) tuples.
    """

    now = datetime.now(timezone.utc)
    end = now
    boundaries = []

    while (now - end).days < lookback_days or len(boundaries) == 0:
        start = end - timedelta(days=7)

        if (now - start).days > lookback_days:
            start = now - timedelta(days=lookback_days)

        label = f"week_{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"
        boundaries.append((start, end, label))

        end = start

        if (now - end).days >= lookback_days:
            break

    boundaries.reverse()

    return boundaries


def download_week(client: Langfuse, start: datetime, end: datetime) -> list[dict]:
    """Download all traces and their observations for a date range."""

    all_traces = []
    page = 1

    while True:
        response = client.api.trace.list(
            limit=50,
            page=page,
            from_timestamp=start,
            to_timestamp=end,
            request_options=REQUEST_OPTS,
        )

        traces = response.data

        if not traces:
            break

        for trace in traces:
            detail = client.api.trace.get(trace.id, request_options=REQUEST_OPTS)
            observations = detail.observations or []
            all_traces.append(serialize_trace(trace, observations))

        print(f"    Page {page}: {len(traces)} traces ({len(all_traces)} total for this week)")

        if len(traces) < 50:
            break

        page += 1

    return all_traces


# ================================
# --> Main
# ================================

def main():
    lookback_days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    OUTPUT_DIR.mkdir(exist_ok=True)
    client = Langfuse()
    weeks = get_week_boundaries(lookback_days)

    print(f"Downloading Langfuse data for last {lookback_days} days ({len(weeks)} weeks)")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    total_traces = 0

    for start, end, label in weeks:
        filepath = OUTPUT_DIR / f"{label}.json"

        print(f"  {label}...")
        traces = download_week(client, start, end)
        total_traces += len(traces)

        with open(filepath, "w") as f:
            json.dump(traces, f, indent=2, default=str)

        print(f"    Saved {len(traces)} traces to {filepath.name}")
        print()

    print(f"Done. {total_traces} total traces saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
