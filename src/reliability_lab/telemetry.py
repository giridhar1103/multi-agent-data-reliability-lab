import os
import time
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

STAGES = Histogram("lab_stage_seconds", "Stage latency", ["role", "mode"])
RUNS = Counter("lab_runs_total", "Completed runs", ["mode", "outcome"])
CALLS = Counter("lab_model_calls_total", "Model HTTP requests", ["outcome"])
TOKENS = Counter("lab_model_tokens_total", "Provider reported tokens", ["kind"])
_provider = None


def setup():
    global _provider
    if _provider is None:
        _provider = TracerProvider(resource=Resource.create({"service.name": "reliability-lab"}))
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if endpoint:
            _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(_provider)


@contextmanager
def stage(store, run_id, role, mode):
    setup()
    started = time.time()
    detail = {}
    status = "ok"
    with trace.get_tracer("reliability_lab").start_as_current_span(role) as span:
        span.set_attribute("lab.run_id", run_id)
        span.set_attribute("lab.mode", mode)
        span.set_attribute("openinference.span.kind", "AGENT")
        try:
            yield detail
        except Exception as exc:
            status = "error"
            detail["error_type"] = type(exc).__name__
            # Do not export prompts, credentials, or raw provider error bodies.
            span.set_status(trace.Status(trace.StatusCode.ERROR, type(exc).__name__))
            raise
        finally:
            elapsed = time.time() - started
            STAGES.labels(role, mode).observe(elapsed)
            span.set_attribute("lab.outcome", status)
            store.event(
                run_id,
                role,
                started,
                elapsed * 1000,
                status,
                detail,
                format(span.get_span_context().trace_id, "032x"),
            )
