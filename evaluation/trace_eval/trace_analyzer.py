"""OTEL trace analyzer for swarm agent evaluation.

This module parses otel.log (OpenTelemetry JSONL export from the swarm)
and computes per-agent metrics: latency, tool call count, error rate.

These metrics complement golden dataset scores. A golden dataset tells you
if the agent got the right answer. Trace analysis tells you how it got there:
which agent was slow, which called the most tools, which produced errors.

Usage:
    python evaluation/trace_eval/trace_analyzer.py --log otel.log
    python evaluation/trace_eval/trace_analyzer.py --log otel.log --agent style-agent
"""

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Optional


def _value_from_otlp_attr_value(val: Any) -> Optional[str]:
    """String form of an OTLP JSON 'value' object, or a plain scalar."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if "stringValue" in val:
            return val.get("stringValue")
        if "intValue" in val:
            return str(val.get("intValue"))
        if "boolValue" in val:
            return str(val.get("boolValue")).lower()
    return str(val)


def lookup_span_attribute(span: dict, key: str) -> Optional[str]:
    """Read a span attribute by key.

    Supports a plain dict (as written by ``FileSpanExporter``) or OTLP JSON style
    lists of ``{"key": ..., "value": {"stringValue": ...}}`` objects.
    """
    raw = span.get("attributes")
    if raw is None:
        return None
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            if item.get("key") != key:
                continue
            return _value_from_otlp_attr_value(item.get("value"))
        return None
    if isinstance(raw, dict):
        if key not in raw:
            return None
        return _value_from_otlp_attr_value(raw[key])
    return None


@dataclass
class AgentTrace:
    """Aggregated trace metrics for one agent service."""

    service_name: str
    span_count: int = 0
    total_duration_ms: float = 0.0
    tool_call_count: int = 0
    error_count: int = 0
    spans: list[dict] = field(default_factory=list)

    @property
    def avg_duration_ms(self) -> float:
        if self.span_count == 0:
            return 0.0
        return self.total_duration_ms / self.span_count

    @property
    def error_rate(self) -> float:
        if self.span_count == 0:
            return 0.0
        return self.error_count / self.span_count


def parse_otel_log(log_path: pathlib.Path) -> list[dict]:
    """Parse otel.log as JSONL. Each line is one span or resource event."""
    spans = []
    with log_path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                spans.append(obj)
            except json.JSONDecodeError as e:
                print(f"Warning: skipping malformed line {line_num}: {e}", file=sys.stderr)
    return spans


def extract_service_name(span: dict) -> Optional[str]:
    """Extract the service.name from a span's resource attributes."""
    resource = span.get("resource", {})
    attrs = resource.get("attributes", [])
    for attr in attrs:
        if attr.get("key") == "service.name":
            return attr.get("value", {}).get("stringValue")

    body = span.get("resourceSpans", [])
    for resource_span in body:
        res_attrs = resource_span.get("resource", {}).get("attributes", [])
        for attr in res_attrs:
            if attr.get("key") == "service.name":
                return attr.get("value", {}).get("stringValue")

    return lookup_span_attribute(span, "service.name")


def compute_duration_ms(span: dict) -> float:
    """Compute span duration in milliseconds from startTimeUnixNano and endTimeUnixNano."""
    start = span.get("startTimeUnixNano", 0)
    end = span.get("endTimeUnixNano", 0)
    if isinstance(start, str):
        start = int(start)
    if isinstance(end, str):
        end = int(end)
    if end > start:
        return (end - start) / 1_000_000
    return 0.0


def is_tool_call_span(span: dict) -> bool:
    """Heuristic: spans with 'tool' in the name represent MCP tool calls."""
    name = span.get("name", "").lower()
    return "tool" in name or "mcp" in name or "call_tool" in name


def is_error_span(span: dict) -> bool:
    """A span is an error if its status code is ERROR or if it has an exception event."""
    status = span.get("status", {})
    if isinstance(status, str):
        if "ERROR" in status.upper():
            return True
    elif isinstance(status, dict):
        if status.get("code") in ("STATUS_CODE_ERROR", "ERROR", 2):
            return True
    events = span.get("events", [])
    for event in events:
        if "exception" in event.get("name", "").lower():
            return True
    return False


def analyze(spans: list[dict], filter_service: Optional[str] = None) -> dict[str, AgentTrace]:
    """Aggregate spans by service name into AgentTrace objects."""
    traces: dict[str, AgentTrace] = {}

    for span in spans:
        service = extract_service_name(span) or "unknown"
        if filter_service and service != filter_service:
            continue

        if service not in traces:
            traces[service] = AgentTrace(service_name=service)

        t = traces[service]
        t.span_count += 1
        t.total_duration_ms += compute_duration_ms(span)
        t.spans.append(span)

        if is_tool_call_span(span):
            t.tool_call_count += 1
        if is_error_span(span):
            t.error_count += 1

    return traces


def print_report(traces: dict[str, AgentTrace]) -> None:
    print("\n" + "=" * 60)
    print("SWARM TRACE ANALYSIS REPORT")
    print("=" * 60)

    if not traces:
        print("No traces found. Check that otel.log is not empty.")
        return

    for service, trace in sorted(traces.items()):
        print(f"\nService: {service}")
        print(f"  Spans:           {trace.span_count}")
        print(f"  Avg Duration:    {trace.avg_duration_ms:.1f} ms")
        print(f"  Tool Calls:      {trace.tool_call_count}")
        print(f"  Errors:          {trace.error_count}")
        print(f"  Error Rate:      {trace.error_rate:.1%}")

    print("\n" + "=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze OTEL traces from the swarm.")
    parser.add_argument("--log", default="otel.log", help="Path to otel.log file")
    parser.add_argument("--agent", default=None, help="Filter to a specific service name")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    log_path = pathlib.Path(args.log)
    if not log_path.exists():
        print(f"Error: {log_path} not found. Run the swarm first to generate traces.", file=sys.stderr)
        sys.exit(1)

    spans = parse_otel_log(log_path)
    print(f"Parsed {len(spans)} spans from {log_path}", file=sys.stderr)

    traces = analyze(spans, filter_service=args.agent)

    if args.json:
        output = {
            svc: {
                "span_count": t.span_count,
                "avg_duration_ms": round(t.avg_duration_ms, 2),
                "tool_call_count": t.tool_call_count,
                "error_count": t.error_count,
                "error_rate": round(t.error_rate, 4),
            }
            for svc, t in traces.items()
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(traces)


if __name__ == "__main__":
    main()
