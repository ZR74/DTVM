#!/usr/bin/env python3

import argparse
import json
import math
import resource
import shlex
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "tx_replay_benchmarks"

STAT_LINE_RE = re.compile(
    r"statistics\.cpp:\d+\] (?P<label>[A-Za-z ()]+):\s+"
    r"(?P<count>\d+) times, avg (?P<avg_ms>[0-9.]+)ms, total "
    r"(?P<total_ms>[0-9.]+)ms(?:, (?P<pct>[0-9.]+)%)?"
)
STAT_TOTAL_RE = re.compile(
    r"statistics\.cpp:\d+\] Total:\s+(?P<total_ms>[0-9.]+)ms"
)


@dataclass
class PreparedReplay:
    dataset: str
    tx_hash: str
    prepared_path: Path
    command: list[str]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    values = sorted(values)
    idx = (len(values) - 1) * pct
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return float(values[lo])
    frac = idx - lo
    return float(values[lo] * (1.0 - frac) + values[hi] * frac)


def summarize_number_list(values: list[float]) -> dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "sum": None,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "p95": None,
        }
    return {
        "count": len(values),
        "sum": float(sum(values)),
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "p95": percentile(values, 0.95),
    }


def parse_statistics_output(text: str) -> dict[str, Any]:
    phases: dict[str, dict[str, Any]] = {}
    total_ms: Optional[float] = None
    for line in text.splitlines():
        match = STAT_LINE_RE.search(line)
        if match:
            label = match.group("label").strip().lower().replace(" ", "_")
            phases[label] = {
                "count": int(match.group("count")),
                "avg_ms": float(match.group("avg_ms")),
                "total_ms": float(match.group("total_ms")),
                "pct": (
                    float(match.group("pct"))
                    if match.group("pct") is not None
                    else None
                ),
            }
            continue
        total_match = STAT_TOTAL_RE.search(line)
        if total_match:
            total_ms = float(total_match.group("total_ms"))
    return {"phases": phases, "total_ms": total_ms}


def override_command_mode(command: list[str], mode: Optional[str]) -> list[str]:
    if not mode:
        return list(command)
    updated = list(command)
    for idx, token in enumerate(updated):
        if token in {"-m", "--mode"} and idx + 1 < len(updated):
            updated[idx + 1] = mode
            return updated
    updated.extend(["-m", mode])
    return updated


def override_command_binary(command: list[str], dtvm_path: Optional[str]) -> list[str]:
    if not dtvm_path:
        return list(command)
    updated = list(command)
    if not updated:
        raise ValueError("prepared command is empty")
    updated[0] = dtvm_path
    return updated


def ensure_statistics_flag(command: list[str], enable_statistics: bool) -> list[str]:
    updated = list(command)
    if enable_statistics and "--enable-statistics" not in updated:
        updated.append("--enable-statistics")
    return updated


def load_prepared_replays(
    prepared_root: Path,
    datasets: Optional[set[str]] = None,
    tx_hashes: Optional[set[str]] = None,
    limit: Optional[int] = None,
) -> list[PreparedReplay]:
    items: list[PreparedReplay] = []
    for prepared_path in sorted(prepared_root.glob("*/*/prepared.json")):
        payload = json.loads(prepared_path.read_text(encoding="utf-8"))
        dataset = str(payload.get("dataset") or prepared_path.parts[-3])
        tx_hash = str(payload.get("tx_hash") or prepared_path.parts[-2]).lower()
        if datasets and dataset not in datasets:
            continue
        if tx_hashes and tx_hash not in tx_hashes:
            continue
        command = payload.get("command") or []
        if not isinstance(command, list) or not all(
            isinstance(token, str) for token in command
        ):
            raise ValueError(f"invalid command in {prepared_path}")
        items.append(
            PreparedReplay(
                dataset=dataset,
                tx_hash=tx_hash,
                prepared_path=prepared_path,
                command=list(command),
            )
        )
        if limit is not None and len(items) >= limit:
            break
    return items


def usage_delta(before: resource.struct_rusage, after: resource.struct_rusage) -> dict[str, float]:
    return {
        "user_cpu_ms": (after.ru_utime - before.ru_utime) * 1000.0,
        "system_cpu_ms": (after.ru_stime - before.ru_stime) * 1000.0,
        "minor_faults": float(after.ru_minflt - before.ru_minflt),
        "major_faults": float(after.ru_majflt - before.ru_majflt),
        "voluntary_ctx_switches": float(after.ru_nvcsw - before.ru_nvcsw),
        "involuntary_ctx_switches": float(after.ru_nivcsw - before.ru_nivcsw),
    }


def run_one(
    command: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    timed_out = False
    stdout = ""
    stderr = ""
    returncode: Optional[int] = None
    error: Optional[str] = None
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        error = f"timeout after {timeout_seconds}s"
    except OSError as exc:
        error = str(exc)
    end = time.perf_counter()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    stats = parse_statistics_output("\n".join(part for part in (stdout, stderr) if part))
    payload: dict[str, Any] = {
        "command": command,
        "command_shell": shlex.join(command),
        "wall_time_ms": (end - start) * 1000.0,
        "returncode": returncode,
        "timed_out": timed_out,
        "error": error,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
        "statistics": stats,
    }
    payload.update(usage_delta(before, after))
    return payload


def dataset_summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    exit_codes: dict[str, int] = {}
    wall_times: list[float] = []
    jit_times: list[float] = []
    instantiation_times: list[float] = []
    stat_totals: list[float] = []
    for row in rows:
        exit_codes[str(row.get("returncode"))] = exit_codes.get(
            str(row.get("returncode")), 0
        ) + 1
        if row.get("wall_time_ms") is not None:
            wall_times.append(float(row["wall_time_ms"]))
        stats = row.get("statistics") or {}
        phases = stats.get("phases") or {}
        if phases.get("jit_compilation", {}).get("total_ms") is not None:
            jit_times.append(float(phases["jit_compilation"]["total_ms"]))
        if phases.get("instantiation", {}).get("total_ms") is not None:
            instantiation_times.append(float(phases["instantiation"]["total_ms"]))
        if stats.get("total_ms") is not None:
            stat_totals.append(float(stats["total_ms"]))
    return {
        "runs": len(rows),
        "exit_codes": exit_codes,
        "wall_time_ms": summarize_number_list(wall_times),
        "jit_compilation_ms": summarize_number_list(jit_times),
        "instantiation_ms": summarize_number_list(instantiation_times),
        "statistics_total_ms": summarize_number_list(stat_totals),
    }


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    by_exit_code: dict[str, int] = {}
    for row in rows:
        by_dataset.setdefault(str(row["dataset"]), []).append(row)
        by_exit_code[str(row.get("returncode"))] = by_exit_code.get(
            str(row.get("returncode")), 0
        ) + 1

    slowest = sorted(rows, key=lambda row: row["wall_time_ms"], reverse=True)[:10]
    return {
        "runs": len(rows),
        "exit_codes": by_exit_code,
        "wall_time_ms": summarize_number_list(
            [float(row["wall_time_ms"]) for row in rows]
        ),
        "user_cpu_ms": summarize_number_list(
            [float(row["user_cpu_ms"]) for row in rows]
        ),
        "system_cpu_ms": summarize_number_list(
            [float(row["system_cpu_ms"]) for row in rows]
        ),
        "datasets": {
            dataset: dataset_summary(dataset_rows)
            for dataset, dataset_rows in sorted(by_dataset.items())
        },
        "slowest_runs": [
            {
                "dataset": row["dataset"],
                "tx_hash": row["tx_hash"],
                "wall_time_ms": row["wall_time_ms"],
                "returncode": row.get("returncode"),
                "jit_compilation_ms": (
                    ((row.get("statistics") or {}).get("phases") or {})
                    .get("jit_compilation", {})
                    .get("total_ms")
                ),
                "prepared_path": row["prepared_path"],
            }
            for row in slowest
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def write_markdown_summary(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Replay Benchmark Summary",
        "",
        f"- Prepared root: `{payload['prepared_root']}`",
        f"- Mode override: `{payload['mode_override'] or 'none'}`",
        f"- Repetitions: `{payload['repetitions']}`",
        f"- Runs: `{summary['runs']}`",
        f"- Exit codes: `{json.dumps(summary['exit_codes'], sort_keys=True)}`",
        "",
        "## Wall Time",
        "",
        f"- Mean: `{summary['wall_time_ms']['mean']}` ms",
        f"- Median: `{summary['wall_time_ms']['median']}` ms",
        f"- P95: `{summary['wall_time_ms']['p95']}` ms",
        "",
        "## Per Dataset",
        "",
    ]
    for dataset, dataset_summary_payload in summary["datasets"].items():
        lines.extend(
            [
                f"### {dataset}",
                "",
                f"- Runs: `{dataset_summary_payload['runs']}`",
                f"- Exit codes: `{json.dumps(dataset_summary_payload['exit_codes'], sort_keys=True)}`",
                f"- Mean wall time: `{dataset_summary_payload['wall_time_ms']['mean']}` ms",
                f"- Mean JIT compilation: `{dataset_summary_payload['jit_compilation_ms']['mean']}` ms",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run DTVM prepared replays and summarize baseline timings"
    )
    parser.add_argument(
        "--prepared-root",
        required=True,
        help="Root containing dataset/tx_hash/prepared.json trees",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT / now_stamp()),
        help="Output directory for JSONL and summary artifacts",
    )
    parser.add_argument(
        "--mode",
        choices=["multipass", "interpreter"],
        default=None,
        help="Override the replay command mode",
    )
    parser.add_argument(
        "--dtvm-path",
        default=None,
        help="Override the DTVM binary path embedded in prepared commands",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="How many fresh process runs to do per prepared replay",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of prepared replays to run",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Restrict to one or more dataset names",
    )
    parser.add_argument(
        "--tx-hash",
        action="append",
        default=[],
        help="Restrict to one or more tx hashes",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=900.0,
        help="Per-process timeout in seconds",
    )
    parser.add_argument(
        "--disable-statistics",
        action="store_true",
        help="Do not append --enable-statistics to replay commands",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prepared_root = Path(args.prepared_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    datasets = set(args.dataset) if args.dataset else None
    tx_hashes = {value.lower() for value in args.tx_hash} if args.tx_hash else None

    prepared_items = load_prepared_replays(
        prepared_root,
        datasets=datasets,
        tx_hashes=tx_hashes,
        limit=args.limit,
    )
    if not prepared_items:
        payload = {
            "prepared_root": str(prepared_root),
            "error": "no prepared replays matched the requested filters",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    rows: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in prepared_items:
        base_command = override_command_binary(item.command, args.dtvm_path)
        base_command = override_command_mode(base_command, args.mode)
        base_command = ensure_statistics_flag(
            base_command, enable_statistics=not args.disable_statistics
        )
        for repetition in range(args.repetitions):
            result = run_one(base_command, timeout_seconds=args.timeout_seconds)
            result.update(
                {
                    "dataset": item.dataset,
                    "tx_hash": item.tx_hash,
                    "prepared_path": str(item.prepared_path),
                    "repetition": repetition,
                }
            )
            rows.append(result)

    payload = {
        "prepared_root": str(prepared_root),
        "output_dir": str(output_dir),
        "dtvm_path": args.dtvm_path,
        "mode_override": args.mode,
        "repetitions": args.repetitions,
        "filters": {
            "datasets": sorted(datasets) if datasets else [],
            "tx_hashes": sorted(tx_hashes) if tx_hashes else [],
            "limit": args.limit,
        },
        "summary": build_summary(rows),
    }

    write_json(output_dir / "summary.json", payload)
    write_jsonl(output_dir / "runs.jsonl", rows)
    write_markdown_summary(output_dir / "summary.md", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
