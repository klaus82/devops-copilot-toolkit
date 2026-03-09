"""
compress.py — Token Shield: Unified Compression CLI

Orchestrates the full compression pipeline:
  1. Minify  — strip comments & whitespace (minify_config.py)
  2. TOON    — abbreviate verbose DevOps keys (toon_converter.py)
  3. Dedup   — collapse repeated lines/blocks (deduplicator.py)
  4. Distill — (logs only) extract unique patterns (log_distiller.py)
  5. Report  — token count, cost estimate, Shield summary

Auto-detects input format from file extension or --format flag.

Usage:
    python compress.py manifest.yaml
    python compress.py main.tf
    python compress.py app.log --format log
    python compress.py --format json < config.json
    python compress.py manifest.yaml --model gpt-4.1-mini --report
    python compress.py manifest.yaml --skip toon dedup
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.prometheus import PrometheusMetricsExporter

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

from contextlib import contextmanager


@contextmanager
def _nullctx():
    yield None


# ── Local module imports (same scripts/ directory) ────────────────────────────
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from minify_config import detect_format as _detect_fmt, shrink_devops_file
from toon_converter import convert as toon_convert, detect_format as _toon_detect
from deduplicator import deduplicate_lines
from log_distiller import distill as log_distill
from token_counter import build_report, MODELS, DEFAULT_MODEL

# ── OpenTelemetry setup ─────────────────────────────────────────────────────────
_tracer = None
_meter = None

if OTEL_AVAILABLE:
    resource = Resource.create({"service.name": "token-shield"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    metric_readers = [PeriodicExportingMetricReader(PrometheusMetricsExporter())]

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )
        except Exception:
            pass

        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            metric_readers.append(
                PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint))
            )
        except Exception:
            pass

    metric_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(metric_provider)
    _meter = metrics.get_meter(__name__)

    _requests_counter = _meter.create_counter(
        "agent_requests_total",
        description="Total number of compression requests",
    )
    _tokens_counter = _meter.create_counter(
        "agent_tokens_total",
        description="Total number of tokens processed",
    )
    _errors_counter = _meter.create_counter(
        "agent_errors_total",
        description="Total number of errors",
    )
    _steps_counter = _meter.create_counter(
        "agent_steps_total",
        description="Total number of pipeline steps executed",
    )
    _latency_histogram = _meter.create_histogram(
        "agent_request_latency",
        description="Request latency in seconds",
        unit="s",
    )

# ──────────────────────────────────────────────
# Pipeline
# ──────────────────────────────────────────────

STEPS = ("minify", "toon", "dedup", "distill")

LOG_EXTENSIONS = {".log", ".out", ".txt", ".stderr", ".stdout"}
LOG_FORMATS = {"log", "logs"}


def _is_log(path: str | None, fmt: str) -> bool:
    if fmt in LOG_FORMATS:
        return True
    if path and Path(path).suffix.lower() in LOG_EXTENSIONS:
        return True
    return False


def compress(
    text: str,
    *,
    path: str | None = None,
    fmt: str = "auto",
    skip: set[str] | None = None,
) -> tuple[str, dict]:
    """
    Run the compression pipeline on *text*.

    Returns (compressed_text, pipeline_stats).
    pipeline_stats keys: format, steps_applied, per_step_chars.
    """
    skip = skip or set()
    stats: dict = {"format": fmt, "steps_applied": [], "per_step_chars": {}}

    is_log = _is_log(path, fmt)

    config_fmt = _detect_fmt(path, None if fmt in ("auto", "log", "logs") else fmt)

    if fmt == "auto":
        stats["format"] = "log" if is_log else config_fmt
    elif fmt in ("log", "logs"):
        stats["format"] = "log"
    else:
        stats["format"] = fmt

    result = text
    stats["per_step_chars"]["input"] = len(result)

    start_time = time.perf_counter()
    error_occurred = False

    try:
        with (
            _tracer.start_as_current_span("compress") if _tracer else _nullctx() as span
        ):
            if span:
                span.set_attribute("input.length", len(result))
                span.set_attribute("format", stats["format"])
                if path:
                    span.set_attribute("file.path", path)

            # Step 1: Minify
            if "minify" not in skip and not is_log:
                with _tracer.start_as_current_span("minify") if _tracer else _nullctx():
                    try:
                        result = shrink_devops_file(result, config_fmt)
                        stats["steps_applied"].append("minify")
                    except Exception as e:
                        print(f"  [minify skipped: {e}]", file=sys.stderr)
            stats["per_step_chars"]["after_minify"] = len(result)

            # Step 2: TOON
            if (
                "toon" not in skip
                and not is_log
                and config_fmt in ("yaml", "json", "hcl")
            ):
                with _tracer.start_as_current_span("toon") if _tracer else _nullctx():
                    try:
                        result = toon_convert(result, config_fmt)
                        stats["steps_applied"].append("toon")
                    except Exception as e:
                        print(f"  [toon skipped: {e}]", file=sys.stderr)
            stats["per_step_chars"]["after_toon"] = len(result)

            # Step 3: Distill
            if "distill" not in skip and is_log:
                with (
                    _tracer.start_as_current_span("distill") if _tracer else _nullctx()
                ):
                    result, distill_stats = log_distill(result)
                    stats["steps_applied"].append("distill")
                    stats["distill"] = distill_stats
            stats["per_step_chars"]["after_distill"] = len(result)

            # Step 4: Dedup
            if "dedup" not in skip:
                with _tracer.start_as_current_span("dedup") if _tracer else _nullctx():
                    md_mode = config_fmt == "md"
                    result, dedup_stats = deduplicate_lines(
                        result, annotate=not md_mode
                    )
                    stats["steps_applied"].append("dedup")
                    stats["dedup"] = dedup_stats
            stats["per_step_chars"]["after_dedup"] = len(result)

            if span:
                span.set_attribute("output.length", len(result))
                span.set_attribute("steps_applied", ",".join(stats["steps_applied"]))

    except Exception as e:
        error_occurred = True
        raise
    finally:
        latency = time.perf_counter() - start_time
        input_tokens = len(text) // 4

        if _meter:
            _requests_counter.add(1, {"service": "token-shield"})
            _tokens_counter.add(input_tokens, {"service": "token-shield"})
            _steps_counter.add(len(stats["steps_applied"]), {"service": "token-shield"})
            _latency_histogram.record(latency, {"service": "token-shield"})
            if error_occurred:
                _errors_counter.add(1, {"service": "token-shield"})

    return result, stats


# ──────────────────────────────────────────────
# Shield Report
# ──────────────────────────────────────────────


def _shield_report(
    original: str,
    compressed: str,
    *,
    model: str,
    pipeline_stats: dict,
) -> list[str]:
    report = build_report(original, compressed, model)
    char_before = len(original)
    char_after = len(compressed)
    char_pct = (char_before - char_after) / char_before * 100 if char_before else 0

    lines = [
        "",
        "╔══════════════════════════════════════════════════════╗",
        "║              TOKEN SHIELD  ·  Shield Report          ║",
        "╠══════════════════════════════════════════════════════╣",
        f"║  Format       : {pipeline_stats['format']:<37}║",
        f"║  Pipeline     : {' → '.join(pipeline_stats['steps_applied']) or 'none':<37}║",
        "╠══════════════════════════════════════════════════════╣",
        f"║  Chars   {char_before:>8,} → {char_after:>8,}   saved {char_pct:>5.1f}%        ║",
        f"║  Tokens  {report.original_tokens:>8,} → {report.compressed_tokens:>8,}   saved {report.savings_pct:>5.1f}%        ║",
        f"║  Cost    ${report.original_cost:.6f} → ${report.compressed_cost:.6f}             ║",
        f"║  Saved   ${report.cost_saved:.6f}  ({model})                ║",
        "╚══════════════════════════════════════════════════════╝",
    ]

    # Contextual advice
    if report.savings_pct >= 40:
        lines.append(
            "  ✔ Significant savings — safe to proceed with compressed payload."
        )
    elif report.savings_pct >= 15:
        lines.append("  ✔ Moderate savings applied.")
    else:
        lines.append("  ℹ Minimal savings — input may already be compact.")

    return lines


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Token Shield: compress configs or logs before sending to an LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python compress.py manifest.yaml
  python compress.py main.tf --model gpt-4.1-mini
  python compress.py app.log --format log
  cat big.json | python compress.py --format json
  python compress.py config.yaml --skip toon
        """,
    )
    parser.add_argument("file", nargs="?", help="Input file (default: stdin).")
    parser.add_argument(
        "--format",
        "-f",
        default="auto",
        choices=["auto", "yaml", "json", "hcl", "md", "js", "log"],
        help="Input format (default: auto-detect).",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=list(STEPS),
        default=[],
        metavar="STEP",
        help=f"Skip pipeline steps. Choices: {', '.join(STEPS)}.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(MODELS),
        help=f"Model for cost estimates (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print Shield Report to stdout instead of stderr; suppress compressed output.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Suppress the Shield Report entirely.",
    )
    args = parser.parse_args()

    path = args.file
    if path:
        with open(path) as f:
            original = f.read()
    else:
        original = sys.stdin.read()

    compressed, pipeline_stats = compress(
        original,
        path=path,
        fmt=args.format,
        skip=set(args.skip),
    )

    if not args.report_only:
        print(compressed)

    if not args.no_report:
        report_lines = _shield_report(
            original, compressed, model=args.model, pipeline_stats=pipeline_stats
        )
        dest = sys.stdout if args.report_only else sys.stderr
        print("\n".join(report_lines), file=dest)

    if OTEL_AVAILABLE:
        if "provider" in globals():
            provider.force_flush()
            provider.shutdown()
        if "metric_provider" in globals():
            metric_provider.force_flush()
            metric_provider.shutdown()


if __name__ == "__main__":
    _cli()
