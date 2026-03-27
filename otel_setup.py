import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, BatchSpanProcessor

OTEL_LOG_PATH = pathlib.Path(__file__).parent / "otel.log"


class FileSpanExporter(SpanExporter):
    def __init__(self, path: pathlib.Path = OTEL_LOG_PATH):
        self._path = path
        self._write({"_marker": "session_start", "time": datetime.now(tz=timezone.utc).isoformat()})

    def _write(self, obj: dict) -> None:
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
            "Resource":       {"service.name": "art-appraisal-swarm", "service.version": "1.0.0"},
            "TraceId":        trace_id,
            "SpanId":         span_id,
            "Attributes":     {"logger.name": record.name, **getattr(record, "otel_attributes", {})},
        })


def setup_otel_tracing(
    service_name: str = "art-appraisal-swarm",
    log_path: pathlib.Path = OTEL_LOG_PATH,
) -> trace.Tracer:
    resource = Resource.create({SERVICE_NAME: service_name, "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(FileSpanExporter(log_path)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def setup_otel_logging(
    logger_name: str = "art_appraisal",
    log_path: pathlib.Path = OTEL_LOG_PATH,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(OtelJsonFormatter())
    logger.addHandler(handler)
    return logger


def otel_log(logger: logging.Logger, level: int, message: str, **attributes) -> None:
    record = logger.makeRecord(logger.name, level, fn="(otel)", lno=0,
                               msg=message, args=(), exc_info=None)
    record.otel_attributes = {k: str(v) for k, v in attributes.items()}
    logger.handle(record)
