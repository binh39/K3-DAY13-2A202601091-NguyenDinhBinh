from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from statistics import mean

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

DEFAULT_LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dashboard" / "index.html"


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {path}. Chạy API + scripts/load_test.py trước để sinh log."
        )
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def compute_panels(events: list[dict], window_minutes: int) -> dict:
    now = datetime.now(timezone.utc)
    window_start = datetime.fromtimestamp(now.timestamp() - window_minutes * 60, tz=timezone.utc)

    def in_window(evt: dict) -> bool:
        ts = parse_ts(evt.get("ts"))
        return ts is None or ts >= window_start

    windowed = [e for e in events if in_window(e)]

    received = [e for e in windowed if e.get("event") == "request_received"]
    failed = [e for e in windowed if e.get("event") == "request_failed"]
    responded = [e for e in windowed if e.get("event") == "response_sent"]

    latencies = [e["latency_ms"] for e in responded if isinstance(e.get("latency_ms"), (int, float))]
    costs = [e["cost_usd"] for e in responded if isinstance(e.get("cost_usd"), (int, float))]
    tokens_in = [e["tokens_in"] for e in responded if isinstance(e.get("tokens_in"), (int, float))]
    tokens_out = [e["tokens_out"] for e in responded if isinstance(e.get("tokens_out"), (int, float))]
    quality = [e["quality_score"] for e in responded if isinstance(e.get("quality_score"), (int, float))]
    error_types = Counter(e.get("error_type") or "unknown" for e in failed)

    total_received = len(received)
    total_failed = len(failed)
    error_rate_pct = round((total_failed / total_received) * 100, 2) if total_received else 0.0

    timestamps = [t for t in (parse_ts(e.get("ts")) for e in windowed) if t]
    span_minutes = (
        max(1.0, (max(timestamps) - min(timestamps)).total_seconds() / 60)
        if len(timestamps) >= 2
        else 1.0
    )

    return {
        "window_start": window_start,
        "generated_at": now,
        "event_count": len(windowed),
        "latency": {
            "p50": round(percentile(latencies, 50), 1),
            "p95": round(percentile(latencies, 95), 1),
            "p99": round(percentile(latencies, 99), 1),
        },
        "traffic": {
            "count": total_received,
            "rate_per_minute": round(total_received / span_minutes, 2),
        },
        "errors": {
            "error_rate_pct": error_rate_pct,
            "count_by_error_type": dict(error_types),
            "total_received": total_received,
            "total_failed": total_failed,
        },
        "cost": {
            "total_usd": round(sum(costs), 4),
            "avg_usd": round(mean(costs), 4) if costs else 0.0,
        },
        "tokens": {
            "tokens_in_total": sum(tokens_in),
            "tokens_out_total": sum(tokens_out),
        },
        "quality": {
            "mean": round(mean(quality), 3) if quality else 0.0,
        },
    }


def check_threshold(operator: str, actual: float, target: float) -> bool:
    if operator == "lte":
        return actual <= target
    if operator == "gte":
        return actual >= target
    raise ValueError(f"Toán tử threshold không hỗ trợ: {operator}")


def evaluate_panel(panel_id: str, metrics: dict, threshold: dict) -> tuple[float, bool]:
    operator = threshold["operator"]
    target = threshold["value"]

    if panel_id == "latency":
        actual = metrics["latency"]["p95"]
    elif panel_id == "traffic":
        actual = metrics["traffic"]["rate_per_minute"]
    elif panel_id == "errors":
        actual = metrics["errors"]["error_rate_pct"]
    elif panel_id == "cost":
        actual = metrics["cost"]["total_usd"]
    elif panel_id == "tokens":
        # sum_by_field threshold applies per field; report the worse of the two.
        actual = max(metrics["tokens"]["tokens_in_total"], metrics["tokens"]["tokens_out_total"])
    elif panel_id == "quality":
        actual = metrics["quality"]["mean"]
    else:
        raise ValueError(f"Panel id không xác định: {panel_id}")

    return actual, check_threshold(operator, actual, target)


PANEL_CARDS = {
    "latency": lambda m: [
        ("P50", f"{m['latency']['p50']:.1f} ms"),
        ("P95", f"{m['latency']['p95']:.1f} ms"),
        ("P99", f"{m['latency']['p99']:.1f} ms"),
    ],
    "traffic": lambda m: [
        ("Requests (window)", str(m["traffic"]["count"])),
        ("Rate / minute", f"{m['traffic']['rate_per_minute']:.2f}"),
    ],
    "errors": lambda m: [
        ("Error rate", f"{m['errors']['error_rate_pct']:.2f} %"),
        ("Failed / Received", f"{m['errors']['total_failed']} / {m['errors']['total_received']}"),
        (
            "By error_type",
            ", ".join(f"{k}={v}" for k, v in m["errors"]["count_by_error_type"].items()) or "none",
        ),
    ],
    "cost": lambda m: [
        ("Total", f"${m['cost']['total_usd']:.4f}"),
        ("Avg / request", f"${m['cost']['avg_usd']:.4f}"),
    ],
    "tokens": lambda m: [
        ("Tokens in (sum)", str(m["tokens"]["tokens_in_total"])),
        ("Tokens out (sum)", str(m["tokens"]["tokens_out_total"])),
    ],
    "quality": lambda m: [
        ("Mean quality_score", f"{m['quality']['mean']:.3f}"),
    ],
}


def render_html(dashboard_cfg: dict, metrics: dict, evaluations: dict) -> str:
    d = dashboard_cfg["dashboard"]
    rows = []
    for panel in d["panels"]:
        pid = panel["id"]
        actual, passed = evaluations[pid]
        badge_class = "pass" if passed else "fail"
        badge_text = "OK" if passed else "VUOT NGUONG"
        stat_rows = "".join(
            f"<div class='stat'><span class='label'>{escape(label)}</span>"
            f"<span class='value'>{escape(value)}</span></div>"
            for label, value in PANEL_CARDS[pid](metrics)
        )
        threshold = panel["threshold"]
        rows.append(
            f"""
            <section class="panel">
              <header>
                <h2>{escape(panel['title'])}</h2>
                <span class="badge {badge_class}">{badge_text}</span>
              </header>
              <p class="meta">unit: {escape(panel['unit'])} &middot;
                threshold: {threshold['aggregation']} {threshold['operator']} {threshold['value']}
                &middot; actual: {actual:.2f}</p>
              <div class="stats">{stat_rows}</div>
            </section>
            """
        )

    generated_at = metrics["generated_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
    window_start = metrics["window_start"].strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<title>{escape(d['title'])}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 0; padding: 24px;
         background: #0b0f14; color: #e6edf3; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  .meta-top {{ color: #8b949e; font-size: 13px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
  .panel {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .panel header {{ display: flex; justify-content: space-between; align-items: center; }}
  .panel h2 {{ font-size: 15px; margin: 0; }}
  .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600; }}
  .badge.pass {{ background: #1f6f43; color: #d3f5df; }}
  .badge.fail {{ background: #7d2d2d; color: #ffd7d7; }}
  .meta {{ color: #8b949e; font-size: 12px; margin: 8px 0 12px; }}
  .stats {{ display: flex; flex-direction: column; gap: 6px; }}
  .stat {{ display: flex; justify-content: space-between; font-size: 13px; }}
  .stat .label {{ color: #8b949e; }}
  .stat .value {{ font-weight: 600; }}
</style>
</head>
<body>
  <h1>{escape(d['title'])}</h1>
  <p class="meta-top">
    time_range: {d['time_range_minutes']} min &middot; refresh: {d['refresh_seconds']}s &middot;
    window start: {window_start} &middot; generated: {generated_at} &middot;
    events in window: {metrics['event_count']}
  </p>
  <div class="grid">
    {''.join(rows)}
  </div>
</body>
</html>
"""


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build 6-panel dashboard HTML from data/logs.jsonl")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    dashboard_cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    events = load_events(args.logs)
    metrics = compute_panels(events, dashboard_cfg["dashboard"]["time_range_minutes"])

    evaluations = {}
    for panel in dashboard_cfg["dashboard"]["panels"]:
        pid = panel["id"]
        evaluations[pid] = evaluate_panel(pid, metrics, panel["threshold"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(dashboard_cfg, metrics, evaluations), encoding="utf-8")

    print(f"Dashboard HTML: {args.output}")
    print(f"events_in_window={metrics['event_count']}")
    for pid, (actual, passed) in evaluations.items():
        print(f"  {pid}: actual={actual:.2f} pass={passed}")
    print(f"error_rate_pct = {metrics['errors']['error_rate_pct']:.2f} "
          f"({metrics['errors']['total_failed']}/{metrics['errors']['total_received']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
