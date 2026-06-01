#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "tx_replay_perf_profiles"
BENCHMARK_TOOL = REPO_ROOT / "tools" / "tx_replay_benchmark.py"

BENCHMARK_SPEC = importlib.util.spec_from_file_location(
    "tx_replay_benchmark", BENCHMARK_TOOL
)
if BENCHMARK_SPEC is None or BENCHMARK_SPEC.loader is None:
    raise RuntimeError(f"failed to load {BENCHMARK_TOOL}")
BENCHMARK_MODULE = importlib.util.module_from_spec(BENCHMARK_SPEC)
BENCHMARK_SPEC.loader.exec_module(BENCHMARK_MODULE)

load_prepared_replays = BENCHMARK_MODULE.load_prepared_replays
override_command_mode = BENCHMARK_MODULE.override_command_mode


FRAME_RE = re.compile(
    r"^\s+[0-9a-fA-F]+\s+(?P<symbol>.+?)\+0x[0-9a-fA-F]+ \((?P<dso>.+)\)$"
)
UNKNOWN_FRAME_RE = re.compile(r"^\s+[0-9a-fA-F]+\s+\[unknown\] \((?P<dso>.+)\)$")


@dataclass
class TopFrame:
    symbol: str
    dso: str


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def strip_benchmark_flags(command: list[str]) -> list[str]:
    result: list[str] = []
    idx = 0
    while idx < len(command):
        token = command[idx]
        if token in {
            "--benchmark",
            "--enable-statistics",
        }:
            idx += 1
            continue
        if token in {
            "--num-extra-compilations",
            "--num-extra-executions",
        }:
            idx += 2
            continue
        result.append(token)
        idx += 1
    return result


def override_command_binary(command: list[str], dtvm_path: str) -> list[str]:
    updated = list(command)
    if not updated:
        raise ValueError("prepared command is empty")
    updated[0] = dtvm_path
    return updated


def build_profile_command(
    command: list[str], dtvm_path: str, mode: Optional[str], extra_executions: int
) -> list[str]:
    updated = override_command_binary(command, dtvm_path)
    updated = override_command_mode(updated, mode)
    updated = strip_benchmark_flags(updated)
    updated.extend(
        [
            "--benchmark",
            "--num-extra-compilations",
            "0",
            "--num-extra-executions",
            str(extra_executions),
        ]
    )
    return updated


def parse_top_frame(line: str) -> Optional[TopFrame]:
    match = FRAME_RE.match(line)
    if match:
        return TopFrame(symbol=match.group("symbol"), dso=match.group("dso"))
    unknown_match = UNKNOWN_FRAME_RE.match(line)
    if unknown_match:
        return TopFrame(symbol="[unknown]", dso=unknown_match.group("dso"))
    return None


def normalize_host_symbol(symbol: str) -> str:
    if "COMPILER::" in symbol:
        symbol = symbol.split("COMPILER::", 1)[1]
    return symbol.split("(", 1)[0]


def classify_symbol(symbol: str, dso: str) -> str:
    symbol_lower = symbol.lower()
    dso_lower = dso.lower()
    if symbol.startswith("EVMBB"):
        return "evm_bb"
    if "keccak" in symbol_lower:
        return "keccak"
    if "compiler::evm" in symbol_lower:
        return "evm_host"
    if "clock_gettime" in symbol_lower or "vdso" in dso_lower:
        return "profiling_overhead"
    if symbol_lower.startswith("compiler::") or symbol_lower.startswith("llvm::"):
        return "compiler"
    if dso == "[kernel.kallsyms]":
        return "kernel"
    if symbol in {"malloc", "malloc@plt", "cfree", "_Znwm", "_ZdlPv"}:
        return "memory"
    if symbol == "[unknown]":
        return "unknown"
    return "other"


def parse_perf_script(text: str) -> dict[str, Any]:
    total_samples = 0
    category_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()
    dso_counts: Counter[str] = Counter()
    evm_bb_counts: Counter[str] = Counter()
    host_symbol_counts: Counter[str] = Counter()
    keccak_symbol_counts: Counter[str] = Counter()

    awaiting_top_frame = False
    top_frame_parsed = False
    for raw_line in text.splitlines():
        if not raw_line.strip():
            awaiting_top_frame = False
            top_frame_parsed = False
            continue
        if not raw_line[0].isspace():
            awaiting_top_frame = True
            top_frame_parsed = False
            continue
        if not awaiting_top_frame or top_frame_parsed:
            continue
        frame = parse_top_frame(raw_line)
        top_frame_parsed = True
        awaiting_top_frame = False
        if frame is None:
            continue

        total_samples += 1
        symbol_counts[frame.symbol] += 1
        dso_counts[frame.dso] += 1
        category = classify_symbol(frame.symbol, frame.dso)
        category_counts[category] += 1
        if category == "evm_bb":
            evm_bb_counts[frame.symbol] += 1
        elif category == "evm_host":
            host_symbol_counts[normalize_host_symbol(frame.symbol)] += 1
        elif category == "keccak":
            keccak_symbol_counts[normalize_host_symbol(frame.symbol)] += 1

    return {
        "top_frame_samples": total_samples,
        "category_counts": dict(category_counts),
        "top_symbols": dict(symbol_counts.most_common(25)),
        "top_dsos": dict(dso_counts.most_common(10)),
        "top_evm_bbs": dict(evm_bb_counts.most_common(20)),
        "top_host_symbols": dict(host_symbol_counts.most_common(20)),
        "top_keccak_symbols": dict(keccak_symbol_counts.most_common(10)),
    }


def counter_share_map(counter_map: dict[str, int], total: int) -> dict[str, float]:
    if total <= 0:
        return {}
    return {
        key: round((value / total) * 100.0, 4)
        for key, value in sorted(counter_map.items())
    }


def wait_for_sync(sync_path: Path, proc: subprocess.Popen[str], timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if sync_path.exists():
            return
        if proc.poll() is not None:
            raise RuntimeError(f"dtvm exited before sync marker: rc={proc.returncode}")
        time.sleep(0.05)
    raise RuntimeError(f"timed out waiting for sync marker {sync_path}")


def remove_repo_jit_artifacts() -> None:
    for pattern in ("jit-*.dump", "jitted-*.so"):
        for path in REPO_ROOT.glob(pattern):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def cleanup_perf_maps() -> None:
    for path in Path("/tmp").glob("perf-*.map"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run_perf_report(perf_bin: str, perf_data: Path) -> str:
    result = subprocess.run(
        [
            perf_bin,
            "report",
            "-i",
            str(perf_data),
            "--percent-limit",
            "0",
            "--no-children",
            "--sort=symbol",
            "--stdio",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def run_perf_script(perf_bin: str, perf_data: Path) -> str:
    result = subprocess.run(
        [perf_bin, "script", "-i", str(perf_data)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_samples = 0
    category_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()
    dso_counts: Counter[str] = Counter()
    evm_bb_counts: Counter[str] = Counter()
    host_counts: Counter[str] = Counter()
    keccak_counts: Counter[str] = Counter()
    zero_execution: list[dict[str, str]] = []
    by_dataset: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        dataset = str(row["dataset"])
        by_dataset.setdefault(dataset, []).append(row)
        parsed = row.get("parsed") or {}
        samples = int(parsed.get("top_frame_samples") or 0)
        total_samples += samples
        category_counts.update(parsed.get("category_counts") or {})
        symbol_counts.update(parsed.get("top_symbols") or {})
        dso_counts.update(parsed.get("top_dsos") or {})
        evm_bb_counts.update(parsed.get("top_evm_bbs") or {})
        host_counts.update(parsed.get("top_host_symbols") or {})
        keccak_counts.update(parsed.get("top_keccak_symbols") or {})
        execution_samples = (
            int((parsed.get("category_counts") or {}).get("evm_bb", 0))
            + int((parsed.get("category_counts") or {}).get("evm_host", 0))
            + int((parsed.get("category_counts") or {}).get("keccak", 0))
        )
        if execution_samples == 0:
            zero_execution.append(
                {"dataset": dataset, "tx_hash": str(row["tx_hash"])}
            )

    datasets_payload: dict[str, Any] = {}
    for dataset, dataset_rows in sorted(by_dataset.items()):
        dataset_total = sum(
            int((row.get("parsed") or {}).get("top_frame_samples") or 0)
            for row in dataset_rows
        )
        dataset_categories: Counter[str] = Counter()
        dataset_bbs: Counter[str] = Counter()
        dataset_hosts: Counter[str] = Counter()
        for row in dataset_rows:
            parsed = row.get("parsed") or {}
            dataset_categories.update(parsed.get("category_counts") or {})
            dataset_bbs.update(parsed.get("top_evm_bbs") or {})
            dataset_hosts.update(parsed.get("top_host_symbols") or {})
        datasets_payload[dataset] = {
            "runs": len(dataset_rows),
            "top_frame_samples": dataset_total,
            "category_counts": dict(dataset_categories),
            "category_pct": counter_share_map(dict(dataset_categories), dataset_total),
            "top_evm_bbs": dict(dataset_bbs.most_common(10)),
            "top_host_symbols": dict(dataset_hosts.most_common(10)),
        }

    return {
        "runs": len(rows),
        "top_frame_samples": total_samples,
        "category_counts": dict(category_counts),
        "category_pct": counter_share_map(dict(category_counts), total_samples),
        "top_symbols": dict(symbol_counts.most_common(30)),
        "top_dsos": dict(dso_counts.most_common(15)),
        "top_evm_bbs": dict(evm_bb_counts.most_common(20)),
        "top_host_symbols": dict(host_counts.most_common(20)),
        "top_keccak_symbols": dict(keccak_counts.most_common(10)),
        "zero_execution_runs": zero_execution,
        "datasets": datasets_payload,
    }


def write_markdown_summary(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Replay Perf Profiling Summary",
        "",
        f"- Prepared root: `{payload['prepared_root']}`",
        f"- DTVM path: `{payload['dtvm_path']}`",
        f"- Mode override: `{payload['mode_override']}`",
        f"- Extra executions: `{payload['extra_executions']}`",
        f"- Perf frequency: `{payload['perf_frequency']}`",
        f"- Runs: `{summary['runs']}`",
        f"- Top-frame samples: `{summary['top_frame_samples']}`",
        f"- Category pct: `{json.dumps(summary['category_pct'], sort_keys=True)}`",
        "",
        "## Top EVM BBs",
        "",
    ]
    for symbol, count in summary["top_evm_bbs"].items():
        lines.append(f"- `{symbol}`: `{count}` samples")
    lines.extend(["", "## Top Host Symbols", ""])
    for symbol, count in summary["top_host_symbols"].items():
        lines.append(f"- `{symbol}`: `{count}` samples")
    lines.extend(["", "## Datasets", ""])
    for dataset, dataset_payload in summary["datasets"].items():
        lines.append(f"### {dataset}")
        lines.append("")
        lines.append(f"- Top-frame samples: `{dataset_payload['top_frame_samples']}`")
        lines.append(f"- Category pct: `{json.dumps(dataset_payload['category_pct'], sort_keys=True)}`")
        lines.append(f"- Top BBs: `{json.dumps(dataset_payload['top_evm_bbs'])}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_one(
    item: Any,
    output_dir: Path,
    perf_bin: str,
    dtvm_path: str,
    mode: str,
    extra_executions: int,
    perf_frequency: int,
    sync_timeout_seconds: float,
    attach_settle_ms: float,
    perf_timeout_seconds: float,
) -> dict[str, Any]:
    run_dir = output_dir / str(item.dataset) / str(item.tx_hash)
    run_dir.mkdir(parents=True, exist_ok=True)
    sync_path = run_dir / "benchmark.sync"
    perf_data = run_dir / "perf_dtvm.data"
    perf_report_path = run_dir / "perf_report.txt"
    perf_script_path = run_dir / "perf_script.txt"
    dtvm_stdout_path = run_dir / "dtvm.stdout.log"
    dtvm_stderr_path = run_dir / "dtvm.stderr.log"
    perf_stdout_path = run_dir / "perf_record.stdout.log"
    perf_stderr_path = run_dir / "perf_record.stderr.log"

    remove_repo_jit_artifacts()
    cleanup_perf_maps()
    if sync_path.exists():
        sync_path.unlink()

    command = build_profile_command(
        list(item.command), dtvm_path=dtvm_path, mode=mode, extra_executions=extra_executions
    )
    env = os.environ.copy()
    env["DTVM_BENCHMARK_SYNC_FILE"] = str(sync_path)
    env["DTVM_BENCHMARK_SYNC_TIMEOUT_MS"] = str(int(sync_timeout_seconds * 1000.0))

    start = time.perf_counter()
    perf_proc: Optional[subprocess.Popen[str]] = None
    dtvm_proc: Optional[subprocess.Popen[str]] = None
    dtvm_rc: Optional[int] = None
    perf_rc: Optional[int] = None
    error: Optional[str] = None
    perf_map_copy: Optional[str] = None
    jit_dump_copy: Optional[str] = None
    try:
        with dtvm_stdout_path.open("w", encoding="utf-8") as stdout_handle, dtvm_stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            dtvm_proc = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                env=env,
            )
            wait_for_sync(sync_path, dtvm_proc, timeout_seconds=sync_timeout_seconds)
            sync_wall_ms = (time.perf_counter() - start) * 1000.0

            perf_proc = subprocess.Popen(
                [
                    perf_bin,
                    "record",
                    "-F",
                    str(perf_frequency),
                    "-k",
                    "1",
                    "-g",
                    "-o",
                    str(perf_data),
                    "-p",
                    str(dtvm_proc.pid),
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(max(0.0, attach_settle_ms / 1000.0))
            if sync_path.exists():
                sync_path.unlink()

            dtvm_rc = dtvm_proc.wait(timeout=perf_timeout_seconds)
            perf_rc = perf_proc.wait(timeout=perf_timeout_seconds)
            perf_out, perf_err = perf_proc.communicate()
            perf_stdout_path.write_text(perf_out or "", encoding="utf-8")
            perf_stderr_path.write_text(perf_err or "", encoding="utf-8")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if dtvm_proc is not None and dtvm_proc.poll() is None:
            dtvm_proc.kill()
        if perf_proc is not None and perf_proc.poll() is None:
            perf_proc.kill()
    finally:
        if sync_path.exists():
            sync_path.unlink()

    total_wall_ms = (time.perf_counter() - start) * 1000.0

    if dtvm_proc is not None:
        perf_map_path = Path("/tmp") / f"perf-{dtvm_proc.pid}.map"
        if perf_map_path.exists():
            copied = run_dir / perf_map_path.name
            shutil.copy2(perf_map_path, copied)
            perf_map_copy = str(copied)
        repo_jit_dump = REPO_ROOT / f"jit-{dtvm_proc.pid}.dump"
        if repo_jit_dump.exists():
            copied = run_dir / repo_jit_dump.name
            shutil.copy2(repo_jit_dump, copied)
            jit_dump_copy = str(copied)

    parsed: dict[str, Any] = {
        "top_frame_samples": 0,
        "category_counts": {},
        "top_symbols": {},
        "top_dsos": {},
        "top_evm_bbs": {},
        "top_host_symbols": {},
        "top_keccak_symbols": {},
    }
    if error is None and perf_data.exists():
        report_text = run_perf_report(perf_bin, perf_data)
        perf_report_path.write_text(report_text, encoding="utf-8")
        script_text = run_perf_script(perf_bin, perf_data)
        perf_script_path.write_text(script_text, encoding="utf-8")
        parsed = parse_perf_script(script_text)
    else:
        perf_report_path.write_text("", encoding="utf-8")
        perf_script_path.write_text("", encoding="utf-8")

    execution_samples = (
        int(parsed["category_counts"].get("evm_bb", 0))
        + int(parsed["category_counts"].get("evm_host", 0))
        + int(parsed["category_counts"].get("keccak", 0))
    )
    top_samples = int(parsed["top_frame_samples"])
    return {
        "dataset": item.dataset,
        "tx_hash": item.tx_hash,
        "prepared_path": str(item.prepared_path),
        "command": command,
        "command_shell": shlex.join(command),
        "dtvm_returncode": dtvm_rc,
        "perf_returncode": perf_rc,
        "error": error,
        "sync_wall_ms": round(locals().get("sync_wall_ms", total_wall_ms), 3),
        "total_wall_ms": round(total_wall_ms, 3),
        "profile_window_ms": round(
            total_wall_ms - locals().get("sync_wall_ms", total_wall_ms), 3
        ),
        "extra_executions": extra_executions,
        "perf_frequency": perf_frequency,
        "perf_data_path": str(perf_data),
        "perf_report_path": str(perf_report_path),
        "perf_script_path": str(perf_script_path),
        "perf_map_copy": perf_map_copy,
        "jit_dump_copy": jit_dump_copy,
        "execution_top_frame_samples": execution_samples,
        "execution_sample_pct": (
            round((execution_samples / top_samples) * 100.0, 4)
            if top_samples > 0
            else None
        ),
        "parsed": parsed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Attach-perf profile prepared DTVM replays after warmup"
    )
    parser.add_argument(
        "--prepared-root",
        required=True,
        help="Root containing dataset/tx_hash/prepared.json trees",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT / now_stamp()),
        help="Output directory for per-tx perf artifacts and summaries",
    )
    parser.add_argument(
        "--dtvm-path",
        default="./build_perf/dtvm",
        help="DTVM binary to use for profiling",
    )
    parser.add_argument(
        "--mode",
        choices=["multipass"],
        default="multipass",
        help="Replay mode override",
    )
    parser.add_argument(
        "--perf-bin",
        default="perf",
        help="perf executable",
    )
    parser.add_argument(
        "--extra-executions",
        type=int,
        default=10000,
        help="How many repeated executions to run after warmup",
    )
    parser.add_argument(
        "--perf-frequency",
        type=int,
        default=9999,
        help="perf record sampling frequency",
    )
    parser.add_argument(
        "--sync-timeout-seconds",
        type=float,
        default=180.0,
        help="How long to wait for the warmup sync marker",
    )
    parser.add_argument(
        "--attach-settle-ms",
        type=float,
        default=500.0,
        help="How long to wait after perf attach before releasing warmup sync",
    )
    parser.add_argument(
        "--perf-timeout-seconds",
        type=float,
        default=900.0,
        help="Timeout for the attached perf window plus process shutdown",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of prepared replays",
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
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prepared_root = Path(args.prepared_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    datasets = set(args.dataset) if args.dataset else None
    tx_hashes = {value.lower() for value in args.tx_hash} if args.tx_hash else None

    items = load_prepared_replays(
        prepared_root,
        datasets=datasets,
        tx_hashes=tx_hashes,
        limit=args.limit,
    )
    if not items:
        payload = {
            "prepared_root": str(prepared_root),
            "error": "no prepared replays matched the requested filters",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            run_one(
                item=item,
                output_dir=output_dir,
                perf_bin=args.perf_bin,
                dtvm_path=args.dtvm_path,
                mode=args.mode,
                extra_executions=args.extra_executions,
                perf_frequency=args.perf_frequency,
                sync_timeout_seconds=args.sync_timeout_seconds,
                attach_settle_ms=args.attach_settle_ms,
                perf_timeout_seconds=args.perf_timeout_seconds,
            )
        )

    payload = {
        "prepared_root": str(prepared_root),
        "output_dir": str(output_dir),
        "dtvm_path": args.dtvm_path,
        "mode_override": args.mode,
        "extra_executions": args.extra_executions,
        "perf_frequency": args.perf_frequency,
        "filters": {
            "datasets": sorted(datasets) if datasets else [],
            "tx_hashes": sorted(tx_hashes) if tx_hashes else [],
            "limit": args.limit,
        },
        "summary": aggregate_rows(rows),
    }

    write_json(output_dir / "summary.json", payload)
    write_jsonl(output_dir / "runs.jsonl", rows)
    write_markdown_summary(output_dir / "summary.md", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
