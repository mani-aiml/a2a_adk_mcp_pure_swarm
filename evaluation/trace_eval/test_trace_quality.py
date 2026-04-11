"""Trace quality assertions (otel.log or JSONL span export).

    pytest evaluation/trace_eval/test_trace_quality.py -v --log-path otel.log
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from evaluation.lib.registry_maps import specialist_trace_services, trace_service_names

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _trace_log_has_per_service_names(traces: dict, specialist_service_names: list[str]) -> bool:
    """True when the log groups spans under registry specialist service_name values (multi-container OTEL)."""
    return any(s in traces for s in specialist_service_names)


def pytest_generate_tests(metafunc):
    if "service_name" not in metafunc.fixturenames:
        return
    cfg = yaml.safe_load((ROOT / "agents.yaml").read_text(encoding="utf-8"))
    name = metafunc.definition.name
    if name == "test_service_produced_spans":
        metafunc.parametrize("service_name", trace_service_names(cfg))
    elif name in ("test_error_rate_below_threshold", "test_avg_latency_within_bounds"):
        metafunc.parametrize("service_name", specialist_trace_services(cfg))


class TestTraceCompleteness:
    def test_otel_log_not_empty(self, traces):
        assert traces, "Trace log is empty or contains no parseable spans."

    def test_service_produced_spans(self, traces, service_name, specialist_service_names):
        if not _trace_log_has_per_service_names(traces, specialist_service_names):
            pytest.skip(
                "Trace log has no per-service resource.service.name for specialists (e.g. single "
                "'art-appraisal-swarm' process). Run full Docker Compose with OTEL_SERVICE_NAME per "
                "service and pass --log-path to that otel.log."
            )
        assert service_name in traces, (
            f"No spans for service '{service_name}'. Available: {list(traces.keys())}."
        )
        assert traces[service_name].span_count >= 1

    def test_all_registry_services_have_traces(self, traces, specialist_service_names):
        if not _trace_log_has_per_service_names(traces, specialist_service_names):
            pytest.skip(
                "Trace log has no per-service resource.service.name for specialists; see "
                "test_service_produced_spans skip reason."
            )
        missing = [s for s in specialist_service_names if s not in traces]
        assert not missing, f"Specialists missing from traces: {missing}."


class TestTraceQualityMetrics:
    MAX_ERROR_RATE = 0.10
    MAX_AVG_LATENCY_MS = 30_000

    def test_error_rate_below_threshold(self, traces, service_name):
        if service_name not in traces:
            pytest.skip(f"No traces for {service_name}")
        rate = traces[service_name].error_rate
        assert rate <= self.MAX_ERROR_RATE, (
            f"Service '{service_name}' error rate {rate:.1%} exceeds {self.MAX_ERROR_RATE:.1%}."
        )

    def test_avg_latency_within_bounds(self, traces, service_name):
        if service_name not in traces:
            pytest.skip(f"No traces for {service_name}")
        avg_ms = traces[service_name].avg_duration_ms
        assert avg_ms <= self.MAX_AVG_LATENCY_MS, (
            f"Service '{service_name}' avg latency {avg_ms:.0f}ms exceeds cap."
        )

    def test_each_specialist_called_at_least_one_tool(self, traces, specialist_service_names):
        if not _trace_log_has_per_service_names(traces, specialist_service_names):
            pytest.skip(
                "Trace log has no per-service specialist spans; cannot assert tool-call counts per specialist."
            )
        for service in specialist_service_names:
            if service not in traces:
                continue
            assert traces[service].tool_call_count >= 1, (
                f"Service '{service}' made zero tool calls (possible ungrounded response)."
            )
