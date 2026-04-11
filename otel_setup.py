"""OpenTelemetry: local JSONL (dev) and/or OTLP HTTP to Jaeger (distributed).

Env (see also standard OTEL vars):

- ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`` — e.g. ``http://jaeger:4318/v1/traces`` (Compose) or
  ``http://localhost:4318/v1/traces`` (host CLI).
- ``OTEL_EXPORTER_OTLP_ENDPOINT`` — optional base URL; ``/v1/traces`` is appended if set.
- ``OTEL_SERVICE_NAME`` — ``service.name`` resource attribute.
- ``OTEL_FILE_LOG`` — ``1``/``0`` for ``otel.log``. Default: file on when no OTLP, off when OTLP set.
- ``OTEL_LOG_PATH`` — absolute path to the JSONL file (default: ``otel.log`` next to this module). Use with a **directory**
  bind mount in Docker (e.g. ``/otel_logs/otel.log``) so the host path is never a file mount of a missing file (which
  Docker would create as a directory).

Jaeger UI: http://localhost:16686
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from datetime import datetime, timezone
from typing import Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

def resolve_otel_log_path() -> pathlib.Path:
    """Path to the OTEL JSONL file; override with ``OTEL_LOG_PATH`` (container-friendly)."""
    raw = (os.environ.get("OTEL_LOG_PATH") or "").strip()
    if raw:
        return pathlib.Path(raw)
    return pathlib.Path(__file__).resolve().parent / "otel.log"


OTEL_LOG_PATH = resolve_otel_log_path()

_provider_configured = False


def _otlp_traces_endpoint() -> str | None:
    explicit = (os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or "").strip()
    if explicit:
        return explicit
    base = (os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip().rstrip("/")
    if base:
        return f"{base}/v1/traces"
    return None


class FileSpanExporter(SpanExporter):
    def __init__(self, path: pathlib.Path = OTEL_LOG_PATH):
        self._path = path
        self._write({"_marker": "session_start", "time": datetime.now(tz=timezone.utc).isoformat()})

    def _write(self, obj: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj) + "\n")

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            ctx = span.context
            self._write({
                "otel_type":      "span",
                "name":           span.name,
                "trace_id":       format(ctx.trace_id, "032x"),
                "span_id":        format(ctx.span_id,  "016x"),
                "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
                "start_time":     _ns_to_iso(span.start_time),
                "end_time":       _ns_to_iso(span.end_time),
                "duration_ms":    round((span.end_time - span.start_time) / 1e6, 3),
                "status":         span.status.status_code.name,
                "attributes":     dict(span.attributes or {}),
                "resource":       dict(span.resource.attributes or {}),
            })
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._write({"_marker": "session_end", "time": datetime.now(tz=timezone.utc).isoformat()})


def _ns_to_iso(ns: int | None) -> str | None:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat() if ns else None


class OtelJsonFormatter(logging.Formatter):
    SEVERITY_MAP = {
        logging.DEBUG:    (5,  "DEBUG"),
        logging.INFO:     (9,  "INFO"),
        logging.WARNING:  (13, "WARN"),
        logging.ERROR:    (17, "ERROR"),
        logging.CRITICAL: (21, "FATAL"),
    }

    def __init__(self, service_name: str = "adk-service", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        sev_num, sev_text = self.SEVERITY_MAP.get(record.levelno, (9, "INFO"))
        span_ctx = trace.get_current_span().get_span_context()
        trace_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else "0" * 32
        span_id  = format(span_ctx.span_id,  "016x") if span_ctx.is_valid else "0" * 16
        return json.dumps({
            "otel_type":      "log",
            "Timestamp":      datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "SeverityText":   sev_text,
            "SeverityNumber": sev_num,
            "Body":           record.getMessage(),
            "Resource":       {"service.name": self._service_name, "service.version": "1.0.0"},
            "TraceId":        trace_id,
            "SpanId":         span_id,
            "Attributes":     {"logger.name": record.name, **getattr(record, "otel_attributes", {})},
        })


def setup_otel_tracing(
    service_name: str | None = None,
    log_path: pathlib.Path | None = None,
    *,
    enable_file: bool | None = None,
    enable_otlp: bool | None = None,
) -> trace.Tracer:
    global _provider_configured

    name = service_name or os.environ.get("OTEL_SERVICE_NAME") or "adk-service"
    path = log_path if log_path is not None else resolve_otel_log_path()
    otlp_url = _otlp_traces_endpoint()

    if enable_otlp is None:
        enable_otlp = bool(otlp_url)
    if enable_file is None:
        raw = os.environ.get("OTEL_FILE_LOG")
        if raw is None:
            enable_file = not enable_otlp
        else:
            enable_file = raw.strip().lower() not in ("0", "false", "no")

    if not enable_file and not enable_otlp:
        enable_file = True

    if _provider_configured:
        return trace.get_tracer(name)

    resource = Resource.create({SERVICE_NAME: name, "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)

    if enable_file:
        provider.add_span_processor(BatchSpanProcessor(FileSpanExporter(path)))

    if enable_otlp and otlp_url:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", otlp_url)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider_configured = True
    return trace.get_tracer(name)


def setup_otel_logging(
    logger_name: str = "art_appraisal",
    log_path: pathlib.Path | None = None,
    service_name: str | None = None,
) -> logging.Logger:
    path = log_path if log_path is not None else resolve_otel_log_path()
    svc = service_name or os.environ.get("OTEL_SERVICE_NAME") or "adk-service"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    marker = "_otel_appraisal_handler"
    if not any(getattr(h, marker, False) for h in logger.handlers):
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, mode="a", encoding="utf-8")
        handler.setFormatter(OtelJsonFormatter(service_name=svc))
        setattr(handler, marker, True)
        logger.addHandler(handler)
    return logger


def otel_log(logger: logging.Logger, level: int, message: str, **attributes) -> None:
    record = logger.makeRecord(logger.name, level, fn="(otel)", lno=0,
                               msg=message, args=(), exc_info=None)
    record.otel_attributes = {k: str(v) for k, v in attributes.items()}
    logger.handle(record)
