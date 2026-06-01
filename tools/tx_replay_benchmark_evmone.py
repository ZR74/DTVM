#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "tx_replay_benchmarks"
DEFAULT_EVMONE_T8N = (
    Path("/root/DTVM_zr/DTVM_pr507_eval/evmone/build/bin/evmone-t8n")
)


@dataclass
class PreparedReplay:
    dataset: str
    tx_hash: str
    prepared_path: Path
    state_path: Path
    top_level_to: str
    top_level_from: str
    calldata: str
    gas_limit: str
    revision: str


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def summarize_number_list(values: list[float]) -> dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "sum": None,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }
    return {
        "count": len(values),
        "sum": float(sum(values)),
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


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
        command = list(payload.get("command") or [])
        calldata = command[command.index("--calldata") + 1]
        gas_limit = command[command.index("--gas-limit") + 1]
        revision = command[command.index("--evm-revision") + 1]
        items.append(
            PreparedReplay(
                dataset=dataset,
                tx_hash=tx_hash,
                prepared_path=prepared_path,
                state_path=Path(payload["state_path"]),
                top_level_to=str(payload["top_level_to"]),
                top_level_from=str(payload["top_level_from"]),
                calldata=calldata,
                gas_limit=gas_limit,
                revision=revision,
            )
        )
        if limit is not None and len(items) >= limit:
            break
    return items


def revision_to_fork_name(revision: str) -> str:
    if not revision:
        return "Cancun"
    return revision[:1].upper() + revision[1:].lower()


def state_requires_prague(state: dict[str, Any]) -> bool:
    for acc in (state.get("accounts") or {}).values():
        code = acc.get("code", "")
        if isinstance(code, str) and code.startswith("0xef"):
            return True
    return False


def choose_fork_name(prepared_revision: str, state: dict[str, Any]) -> str:
    fork_name = revision_to_fork_name(prepared_revision)
    if fork_name in {"Frontier", "Homestead", "Tangerine", "Spurious", "Byzantium", "Constantinople",
        "Petersburg", "Istanbul", "Berlin", "London", "Paris", "Shanghai", "Cancun"} and state_requires_prague(state):
        return "Prague"
    return fork_name


def build_alloc(state: dict[str, Any]) -> dict[str, Any]:
    alloc: dict[str, Any] = {}
    for addr, acc in (state.get("accounts") or {}).items():
        alloc[addr] = {
            "nonce": hex(int(acc.get("nonce", 0))),
            "balance": acc.get("balance", "0x0"),
            "code": acc.get("code", ""),
            "storage": acc.get("storage", {}),
        }
    return alloc


def build_env(state: dict[str, Any]) -> dict[str, Any]:
    tx_context = state["tx_context"]
    env = {
        "currentCoinbase": tx_context["block_coinbase"],
        "currentNumber": hex(int(tx_context["block_number"])),
        "currentTimestamp": hex(int(tx_context["block_timestamp"])),
        "currentGasLimit": hex(int(tx_context["block_gas_limit"])),
        "currentBaseFee": tx_context["block_base_fee"],
        "currentRandom": tx_context["block_prev_randao"],
    }
    return env


def build_txs(prepared: PreparedReplay, state: dict[str, Any]) -> list[dict[str, Any]]:
    sender = prepared.top_level_from.lower()
    sender_acc = (state.get("accounts") or {}).get(sender) or (state.get("accounts") or {}).get(
        prepared.top_level_from
    )
    if sender_acc is None:
        raise KeyError(f"sender account missing from state: {prepared.top_level_from}")
    return [
        {
            "to": prepared.top_level_to,
            "input": "0x" + prepared.calldata,
            "gas": prepared.gas_limit,
            "nonce": hex(int(sender_acc.get("nonce", 0))),
            "value": "0x0",
            "gasPrice": state["tx_context"]["gas_price"],
            "chainId": "0x1",
            "sender": prepared.top_level_from,
            "v": "0x0",
            "r": "0x1",
            "s": "0x1",
        }
    ]


def run_one(prepared: PreparedReplay, evmone_t8n: Path, timeout_seconds: float) -> dict[str, Any]:
    state = json.loads(prepared.state_path.read_text(encoding="utf-8"))
    alloc = build_alloc(state)
    env = build_env(state)
    txs = build_txs(prepared, state)
    fork_name = choose_fork_name(prepared.revision, state)

    with tempfile.TemporaryDirectory(prefix="evmone_t8n_") as td:
        td_path = Path(td)
        out_dir = td_path / "out"
        out_dir.mkdir()
        (td_path / "alloc.json").write_text(json.dumps(alloc), encoding="utf-8")
        (td_path / "env.json").write_text(json.dumps(env), encoding="utf-8")
        (td_path / "txs.json").write_text(json.dumps(txs), encoding="utf-8")

        command = [
            str(evmone_t8n),
            "--state.fork",
            fork_name,
            "--state.reward",
            "0",
            "--state.chainid",
            "1",
            "--input.alloc",
            str(td_path / "alloc.json"),
            "--input.env",
            str(td_path / "env.json"),
            "--input.txs",
            str(td_path / "txs.json"),
            "--output.basedir",
            str(out_dir),
            "--output.result",
            "out.json",
            "--output.alloc",
            "outAlloc.json",
        ]

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
        wall_time_ms = (time.perf_counter() - start) * 1000.0

        out_result_path = out_dir / "out.json"
        out_payload: dict[str, Any] | None = None
        if out_result_path.exists():
            try:
                out_payload = json.loads(out_result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                error = error or f"invalid out.json: {exc}"

        first_receipt = ((out_payload or {}).get("receipts") or [None])[0]
        rejected = (out_payload or {}).get("rejected") or []
        return {
            "dataset": prepared.dataset,
            "tx_hash": prepared.tx_hash,
            "prepared_revision": prepared.revision,
            "effective_fork": fork_name,
            "prepared_path": str(prepared.prepared_path),
            "state_path": str(prepared.state_path),
            "command": command,
            "command_shell": shlex.join(command),
            "returncode": returncode,
            "timed_out": timed_out,
            "error": error,
            "wall_time_ms": wall_time_ms,
            "receipt_status": None if first_receipt is None else first_receipt.get("status"),
            "receipt_gas_used": None if first_receipt is None else first_receipt.get("gasUsed"),
            "receipt_cumulative_gas_used": None
            if first_receipt is None
            else first_receipt.get("cumulativeGasUsed"),
            "rejected_count": len(rejected),
            "rejected_error": None if not rejected else rejected[0].get("error"),
            "output_result": out_payload,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
        }


def dataset_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exit_codes: dict[str, int] = {}
    receipt_status: dict[str, int] = {}
    rejected_errors: dict[str, int] = {}
    wall_times: list[float] = []
    gas_used_values: list[int] = []
    for row in rows:
        exit_codes[str(row.get("returncode"))] = exit_codes.get(str(row.get("returncode")), 0) + 1
        status = row.get("receipt_status")
        if status is not None:
            receipt_status[str(status)] = receipt_status.get(str(status), 0) + 1
        if row.get("rejected_error"):
            key = str(row["rejected_error"])
            rejected_errors[key] = rejected_errors.get(key, 0) + 1
        if row.get("wall_time_ms") is not None:
            wall_times.append(float(row["wall_time_ms"]))
        if row.get("receipt_gas_used"):
            gas_used_values.append(int(str(row["receipt_gas_used"]), 16))
    return {
        "runs": len(rows),
        "exit_codes": exit_codes,
        "receipt_status": receipt_status,
        "rejected_errors": rejected_errors,
        "wall_time_ms": summarize_number_list(wall_times),
        "gas_used": summarize_number_list([float(v) for v in gas_used_values]),
    }


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_dataset.setdefault(str(row["dataset"]), []).append(row)
    datasets = {name: dataset_summary(items) for name, items in sorted(by_dataset.items())}
    overall = dataset_summary(rows)
    slowest = sorted(rows, key=lambda row: float(row.get("wall_time_ms") or 0.0), reverse=True)[:20]
    return {
        "runs": overall["runs"],
        "exit_codes": overall["exit_codes"],
        "receipt_status": overall["receipt_status"],
        "rejected_errors": overall["rejected_errors"],
        "wall_time_ms": overall["wall_time_ms"],
        "gas_used": overall["gas_used"],
        "datasets": datasets,
        "slowest_runs": slowest,
    }


def write_summary_markdown(summary: dict[str, Any], output_dir: Path, prepared_root: Path) -> None:
    lines = [
        "# EVMone Replay Benchmark Summary",
        "",
        f"- Prepared root: `{prepared_root}`",
        f"- Runs: `{summary['runs']}`",
        f"- Wall mean: `{summary['wall_time_ms']['mean']}` ms",
        f"- Wall median: `{summary['wall_time_ms']['median']}` ms",
        f"- Exit codes: `{summary['exit_codes']}`",
        f"- Receipt status: `{summary['receipt_status']}`",
        "",
        "## Per Dataset",
        "",
    ]
    for dataset, item in summary["datasets"].items():
        lines.extend(
            [
                f"### {dataset}",
                f"- Runs: `{item['runs']}`",
                f"- Wall mean: `{item['wall_time_ms']['mean']}` ms",
                f"- Wall median: `{item['wall_time_ms']['median']}` ms",
                f"- Gas mean: `{item['gas_used']['mean']}`",
                f"- Exit codes: `{item['exit_codes']}`",
                f"- Receipt status: `{item['receipt_status']}`",
                "",
            ]
        )
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run prepared tx replay corpus with evmone-t8n")
    parser.add_argument(
        "--prepared-root",
        type=Path,
        default=REPO_ROOT / "data" / "tx_replay_prepare_200",
        help="Root containing dataset/tx_hash/prepared.json trees",
    )
    parser.add_argument(
        "--evmone-t8n",
        type=Path,
        default=DEFAULT_EVMONE_T8N,
        help="Path to evmone-t8n binary",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output-name", type=str, default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--tx-hash", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    datasets = set(args.dataset) if args.dataset else None
    tx_hashes = {value.lower() for value in args.tx_hash} if args.tx_hash else None
    prepared_root = args.prepared_root.resolve()
    evmone_t8n = args.evmone_t8n.resolve()
    if not evmone_t8n.exists():
        raise SystemExit(f"evmone-t8n not found: {evmone_t8n}")

    output_name = args.output_name or f"ssa200_evmone_{now_stamp()}"
    output_dir = (args.output_root / output_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prepared_replays = load_prepared_replays(
        prepared_root, datasets=datasets, tx_hashes=tx_hashes, limit=args.limit
    )
    rows: list[dict[str, Any]] = []
    runs_path = output_dir / "runs.jsonl"
    with runs_path.open("w", encoding="utf-8") as handle:
        for prepared in prepared_replays:
            row = run_one(prepared, evmone_t8n=evmone_t8n, timeout_seconds=args.timeout_seconds)
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()

    summary = {
        "prepared_root": str(prepared_root),
        "evmone_t8n": str(evmone_t8n),
        "output_dir": str(output_dir),
        "runs": len(rows),
        "summary": build_summary(rows),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_summary_markdown(summary["summary"], output_dir, prepared_root)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
