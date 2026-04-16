from __future__ import annotations

import argparse
import re
from pathlib import Path


SUMMARY_RE = re.compile(
    r"frames=(?P<frames>\d+), positives=(?P<positives>\d+), "
    r"saved=(?P<saved>\d+), gps_fixes=(?P<gps>\d+), "
    r"avg_inference_ms=(?P<avg_ms>\d+\.?\d*), throughput_fpm=(?P<fpm>\d+\.?\d*)"
)


def parse_summary(log_text: str) -> dict[str, float] | None:
    matches = SUMMARY_RE.findall(log_text)
    if not matches:
        return None
    last = matches[-1]
    return {
        "frames": float(last[0]),
        "positives": float(last[1]),
        "saved": float(last[2]),
        "gps_fixes": float(last[3]),
        "avg_inference_ms": float(last[4]),
        "throughput_fpm": float(last[5]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract pothole runtime metrics from log.")
    parser.add_argument("log_file", help="Path to runtime log output.")
    args = parser.parse_args()

    log_text = Path(args.log_file).read_text(encoding="utf-8")
    summary = parse_summary(log_text)
    if summary is None:
        print("No runtime summary found in log.")
        return

    print("Parsed runtime metrics")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
