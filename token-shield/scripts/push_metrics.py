#!/usr/bin/env python3
"""Push token-shield metrics to Prometheus Pushgateway."""

import argparse
import re
import sys
import time
from urllib import request, parse


def parse_shield_report(output: str) -> dict:
    """Parse Shield Report output to extract metrics."""
    metrics = {}

    tokens_match = re.search(r"Tokens\s+(\d+)\s+→\s+(\d+)", output)
    chars_match = re.search(r"Chars\s+(\d+)\s+→\s+(\d+)", output)
    format_match = re.search(r"Format\s+:\s+(\w+)", output)

    if tokens_match:
        metrics["tokens_original"] = int(tokens_match.group(1))
        metrics["tokens_compressed"] = int(tokens_match.group(2))
        metrics["tokens_saved"] = (
            metrics["tokens_original"] - metrics["tokens_compressed"]
        )
    if chars_match:
        metrics["chars_original"] = int(chars_match.group(1))
        metrics["chars_compressed"] = int(chars_match.group(2))
    if format_match:
        metrics["format"] = format_match.group(1)

    return metrics


def build_prometheus_metrics(data: dict, job: str, instance: str) -> str:
    """Build Prometheus metrics in text format."""
    timestamp = int(time.time())
    lines = []

    labels = f'job="{job}",instance="{instance}"'

    for key, value in data.items():
        if isinstance(value, (int, float)):
            lines.append(f"tokenshield_{key}{{{labels}}} {value} {timestamp}")
        elif isinstance(value, str):
            lines.append(
                f'tokenshield_{key}{{{labels},format="{value}"}} 1 {timestamp}'
            )

    return "\n".join(lines) + "\n"


def push_to_gateway(
    metrics: str, job: str, instance: str, gateway_url: str = "http://localhost:9091"
):
    """Push metrics to Pushgateway."""
    url = f"{gateway_url}/metrics/job/{job}/instance/{parse.quote(instance, safe='')}"

    req = request.Request(
        url, data=metrics.encode("utf-8"), headers={"Content-Type": "text/plain"}
    )

    with request.urlopen(req) as response:
        if response.status == 200:
            print(f"✓ Metrics pushed to {url}")
        else:
            print(f"✗ Failed to push: {response.status}")


def main():
    parser = argparse.ArgumentParser(
        description="Push token-shield metrics to Prometheus"
    )
    parser.add_argument(
        "--input", "-i", help="Shield Report output file (or pipe stdin)"
    )
    parser.add_argument("--job", default="token-shield", help="Prometheus job name")
    parser.add_argument("--instance", default="local", help="Prometheus instance label")
    parser.add_argument(
        "--gateway", default="http://localhost:9091", help="Pushgateway URL"
    )

    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            output = f.read()
    else:
        output = sys.stdin.read()

    metrics = parse_shield_report(output)

    if not metrics:
        print("No metrics found in input", file=sys.stderr)
        sys.exit(1)

    prom_metrics = build_prometheus_metrics(metrics, args.job, args.instance)
    push_to_gateway(prom_metrics, args.job, args.instance, args.gateway)


if __name__ == "__main__":
    main()
