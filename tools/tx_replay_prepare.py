#!/usr/bin/env python3
"""
Prepare DTVM replay inputs from trace-backed transaction rows.

This tool is intentionally pragmatic:
- it consumes existing JSONL corpus rows and local trace files,
- reconstructs the observable access set from structLogs,
- uses ordinary historical RPC calls to backfill account/code data,
- emits DTVM state.json, top-level bytecode, and a replay manifest.

    Limitations:
    - top-level contract creation traces are reported as unsupported,
- balance / nonce fields that are not directly observable in the trace are
  approximated from historical RPC snapshots,
- trace files must still exist locally.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "tx_replay_prepare"
EMPTY_ADDRESS = "0x" + ("0" * 40)
EMPTY_BYTES32 = "0x" + ("0" * 64)


def strip_hex_prefix(value: str) -> str:
    if value.startswith(("0x", "0X")):
        return value[2:]
    return value


def ensure_hex_prefix(value: str) -> str:
    return value if value.startswith(("0x", "0X")) else f"0x{value}"


def parse_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return 0
    if text.startswith(("0x", "0X")):
        return int(text, 16)
    return int(text)


def pad_hex(value: Any, byte_len: int) -> str:
    return f"0x{parse_int(value):0{byte_len * 2}x}"


def normalize_address(value: Any) -> str:
    text = strip_hex_prefix(str(value or "")).lower()
    if not text:
        return EMPTY_ADDRESS
    return f"0x{text[-40:].zfill(40)}"


def normalize_bytes32(value: Any) -> str:
    text = strip_hex_prefix(str(value or "")).lower()
    if not text:
        return EMPTY_BYTES32
    return f"0x{text[-64:].zfill(64)}"


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def summarize_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


class JsonRpcClient:
    def __init__(self, url: str, cache_dir: Path, timeout: float = 30.0) -> None:
        self.url = url
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.request_id = 0
        self.cache_hits = 0
        self.network_calls = 0

    def _cache_path(self, method: str, params: List[Any]) -> Path:
        digest = hashlib.sha256(
            json.dumps(params, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / method / f"{digest}.json"

    def call(self, method: str, params: List[Any]) -> Any:
        cache_path = self._cache_path(method, params)
        if cache_path.exists():
            self.cache_hits += 1
            return json.loads(cache_path.read_text(encoding="utf-8"))["result"]

        self.request_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in real runs
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - exercised in real runs
            raise RuntimeError(f"{method} network error: {exc}") from exc

        if "error" in payload:
            raise RuntimeError(f"{method} RPC error: {payload['error']}")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        self.network_calls += 1
        return payload["result"]


@dataclass
class Frame:
    storage_address: str
    code_address: str
    caller_address: str


@dataclass
class TraceAnalysis:
    accounts: set[str] = field(default_factory=set)
    code_accounts: set[str] = field(default_factory=set)
    storage_keys: Dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    storage_values: Dict[tuple[str, str], str] = field(default_factory=dict)
    balance_values: Dict[str, str] = field(default_factory=dict)
    outgoing_value: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    block_hash_values: List[str] = field(default_factory=list)
    unsupported_ops: set[str] = field(default_factory=set)
    total_struct_logs: int = 0


def next_same_depth(struct_logs: List[Dict[str, Any]], index: int, depth: int) -> Optional[Dict[str, Any]]:
    if index + 1 >= len(struct_logs):
        return None
    next_item = struct_logs[index + 1]
    return next_item if parse_int(next_item.get("depth")) == depth else None


def infer_same_height_word(
    struct_logs: List[Dict[str, Any]], index: int, depth: int, expected_delta: int
) -> Optional[str]:
    current = struct_logs[index]
    current_stack = current.get("stack") or []
    next_item = next_same_depth(struct_logs, index, depth)
    if not next_item:
        return None
    next_stack = next_item.get("stack") or []
    if len(next_stack) != len(current_stack) + expected_delta:
        return None
    if not next_stack:
        return None
    return normalize_bytes32(next_stack[-1])


def child_frame_from_call(op: str, stack: List[str], frame: Frame) -> Optional[Frame]:
    if op == "CALL":
        if len(stack) < 7:
            return None
        target = normalize_address(stack[-2])
        return Frame(target, target, frame.storage_address)
    if op == "STATICCALL":
        if len(stack) < 6:
            return None
        target = normalize_address(stack[-2])
        return Frame(target, target, frame.storage_address)
    if op == "CALLCODE":
        if len(stack) < 7:
            return None
        target = normalize_address(stack[-2])
        return Frame(frame.storage_address, target, frame.storage_address)
    if op == "DELEGATECALL":
        if len(stack) < 6:
            return None
        target = normalize_address(stack[-2])
        return Frame(frame.storage_address, target, frame.caller_address)
    return None


def synthetic_created_address(index: int, depth: int, op: str) -> str:
    digest = hashlib.sha256(f"{op}:{index}:{depth}".encode("utf-8")).hexdigest()
    return normalize_address(f"0x{digest[-40:]}")


def analyze_trace(struct_logs: List[Dict[str, Any]], top_level_to: str, top_level_from: str) -> TraceAnalysis:
    analysis = TraceAnalysis(total_struct_logs=len(struct_logs))
    top_level_to = normalize_address(top_level_to)
    top_level_from = normalize_address(top_level_from)
    frames: List[Frame] = [Frame(top_level_to, top_level_to, top_level_from)]
    analysis.accounts.update({top_level_to, top_level_from})
    analysis.code_accounts.add(top_level_to)

    for index, item in enumerate(struct_logs):
        depth = parse_int(item.get("depth"))
        while len(frames) > depth:
            frames.pop()
        if depth <= 0 or len(frames) < depth:
            raise ValueError(f"unexpected trace depth at log index {index}: {depth}")

        frame = frames[depth - 1]
        op = str(item.get("op") or "")
        stack = item.get("stack") or []

        if op == "SLOAD" and stack:
            key = normalize_bytes32(stack[-1])
            analysis.storage_keys[frame.storage_address].add(key)
            value = infer_same_height_word(struct_logs, index, depth, 0)
            if value is not None:
                analysis.storage_values.setdefault((frame.storage_address, key), value)
            continue

        if op == "SSTORE" and stack:
            key = normalize_bytes32(stack[-1])
            analysis.storage_keys[frame.storage_address].add(key)
            continue

        if op in {"BALANCE", "EXTCODESIZE", "EXTCODEHASH", "EXTCODECOPY"} and stack:
            address = normalize_address(stack[-1])
            analysis.accounts.add(address)
            analysis.code_accounts.add(address)
            if op == "BALANCE":
                value = infer_same_height_word(struct_logs, index, depth, 0)
                if value is not None:
                    analysis.balance_values.setdefault(address, value)
            continue

        if op == "SELFBALANCE":
            analysis.accounts.add(frame.storage_address)
            value = infer_same_height_word(struct_logs, index, depth, 1)
            if value is not None:
                analysis.balance_values.setdefault(frame.storage_address, value)
            continue

        if op == "BLOCKHASH":
            value = infer_same_height_word(struct_logs, index, depth, 0)
            if value is not None and value not in analysis.block_hash_values:
                analysis.block_hash_values.append(value)
            continue

        if op in {"CALL", "STATICCALL", "CALLCODE", "DELEGATECALL"}:
            child = child_frame_from_call(op, stack, frame)
            if child is not None:
                analysis.accounts.add(child.storage_address)
                analysis.accounts.add(child.code_address)
                analysis.code_accounts.add(child.code_address)
                if op == "CALL" and len(stack) >= 3:
                    analysis.outgoing_value[frame.storage_address] += parse_int(stack[-3])
                if index + 1 < len(struct_logs) and parse_int(struct_logs[index + 1].get("depth")) == depth + 1:
                    frames.append(child)
            continue

        if op == "SELFDESTRUCT" and stack:
            analysis.accounts.add(normalize_address(stack[-1]))
            continue

        if op in {"CREATE", "CREATE2"}:
            if index + 1 < len(struct_logs) and parse_int(struct_logs[index + 1].get("depth")) == depth + 1:
                child_address = synthetic_created_address(index, depth, op)
                analysis.accounts.add(child_address)
                analysis.code_accounts.add(child_address)
                frames.append(Frame(child_address, child_address, frame.storage_address))
            continue

    return analysis


def resolve_trace_path(
    raw_path: str, repo_root: Path, search_roots: Iterable[Path]
) -> Optional[Path]:
    if not raw_path:
        return None

    direct = Path(raw_path)
    candidates = [direct]
    if not direct.is_absolute():
        candidates.append((repo_root / direct).resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    basename = Path(raw_path).name
    for root in search_roots:
        if not root.exists():
            continue
        matches = list(root.rglob(basename))
        if matches:
            return matches[0].resolve()
    return None


def load_trace_payload(path: Path) -> Dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def top_level_trace_struct_logs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "trace" in payload and isinstance(payload["trace"], dict):
        return payload["trace"].get("structLogs") or []
    return payload.get("structLogs") or []


def effective_gas_price_hex(row: Dict[str, Any], tx_result: Dict[str, Any]) -> str:
    for key in ("effective_gas_price", "receipt_effective_gas_price", "gasPrice"):
        value = row.get(key) if key in row else tx_result.get(key)
        if value:
            return pad_hex(value, 32)
    value = tx_result.get("gasPrice")
    return pad_hex(value, 32) if value else EMPTY_BYTES32


def build_access_list(tx_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    access_list = tx_result.get("accessList") or []
    items: List[Dict[str, Any]] = []
    for entry in access_list:
        address = normalize_address(entry.get("address"))
        storage_keys = [normalize_bytes32(item) for item in (entry.get("storageKeys") or [])]
        items.append({"address": address, "storage_keys": storage_keys})
    return items


def proof_storage_map(proof: Dict[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in proof.get("storageProof") or []:
        mapping[normalize_bytes32(entry.get("key"))] = normalize_bytes32(entry.get("value"))
    return mapping


def build_state_payload(
    row: Dict[str, Any],
    tx_result: Dict[str, Any],
    block_result: Dict[str, Any],
    analysis: TraceAnalysis,
    account_payloads: Dict[str, Dict[str, Any]],
    account_codes: Dict[str, str],
    top_level_to: str,
    top_level_from: str,
) -> Dict[str, Any]:
    sender = normalize_address(top_level_from)
    recipient = normalize_address(top_level_to)
    block_coinbase = normalize_address(block_result.get("miner"))
    gas_price_hex = effective_gas_price_hex(row, tx_result)
    sender_required_balance = parse_int(tx_result.get("value")) + parse_int(tx_result.get("gas")) * parse_int(
        gas_price_hex
    )

    accounts: Dict[str, Any] = {}
    for address in sorted(analysis.accounts | {sender, recipient, block_coinbase}):
        proof = account_payloads[address]
        storage_map = proof_storage_map(proof)
        account_storage: Dict[str, Any] = {}
        observed_keys = analysis.storage_keys.get(address) or set()
        for key in sorted(observed_keys):
            value = analysis.storage_values.get((address, key)) or storage_map.get(key) or EMPTY_BYTES32
            account_storage[key] = value

        balance = analysis.balance_values.get(address) or pad_hex(proof.get("balance"), 32)
        balance_int = parse_int(balance)
        if address == sender:
            balance_int = max(balance_int, sender_required_balance)
        if address in analysis.outgoing_value and address not in analysis.balance_values:
            balance_int = max(balance_int, analysis.outgoing_value[address])

        nonce = parse_int(proof.get("nonce"))
        if address == sender:
            nonce = parse_int(tx_result.get("nonce"))

        accounts[address] = {
            "balance": pad_hex(balance_int, 32),
            "nonce": nonce,
            "code": account_codes.get(address, "0x"),
            "codehash": normalize_bytes32(proof.get("codeHash")),
            "storage": account_storage,
        }

    payload: Dict[str, Any] = {
        "accounts": accounts,
        "tx_context": {
            "gas_price": gas_price_hex,
            "block_number": parse_int(block_result.get("number")),
            "block_timestamp": parse_int(block_result.get("timestamp")),
            "block_coinbase": block_coinbase,
            "block_prev_randao": normalize_bytes32(block_result.get("mixHash")),
            "block_gas_limit": parse_int(block_result.get("gasLimit")),
            "block_base_fee": pad_hex(block_result.get("baseFeePerGas"), 32),
            "tx_origin": sender,
        },
    }

    if analysis.block_hash_values:
        payload["block_hash"] = analysis.block_hash_values[0]

    access_list = build_access_list(tx_result)
    if access_list:
        payload["access_list"] = access_list

    return payload


def build_command(
    bytecode_path: Path,
    state_path: Path,
    tx_result: Dict[str, Any],
    top_level_to: str,
    top_level_from: str,
    mode: str,
    evm_revision: str,
    num_extra_executions: int,
) -> List[str]:
    command = [
        "./build/dtvm",
        "-m",
        mode,
        "--format",
        "evm",
        str(bytecode_path),
        "--load-state",
        str(state_path),
        "--contract-address",
        normalize_address(top_level_to),
        "--sender",
        normalize_address(top_level_from),
        "--calldata",
        strip_hex_prefix(tx_result.get("input") or ""),
        "--gas-limit",
        ensure_hex_prefix(str(tx_result.get("gas") or "0x0")),
        "--evm-revision",
        evm_revision,
    ]
    if num_extra_executions > 0:
        command.extend(["--num-extra-executions", str(num_extra_executions)])
    return command


def find_row_by_tx_hash(jsonl_path: Path, tx_hash: str) -> Optional[Dict[str, Any]]:
    target = tx_hash.lower()
    for row in load_jsonl(jsonl_path):
        if str(row.get("tx_hash") or "").lower() == target:
            return row
    return None


def prepare_row(
    row: Dict[str, Any],
    args: argparse.Namespace,
    rpc: JsonRpcClient,
    search_roots: List[Path],
) -> Dict[str, Any]:
    dataset = str(row.get("dataset") or "unknown")
    tx_hash = str(row.get("tx_hash") or "")
    result: Dict[str, Any] = {
        "dataset": dataset,
        "tx_hash": tx_hash,
        "ready": False,
    }

    trace_path = resolve_trace_path(str(row.get("trace_path") or ""), REPO_ROOT, search_roots)
    result["trace_path"] = str(trace_path) if trace_path else str(row.get("trace_path") or "")
    if trace_path is None:
        result["error"] = "trace file not found"
        return result

    trace_payload = load_trace_payload(trace_path)
    struct_logs = top_level_trace_struct_logs(trace_payload)
    if not struct_logs:
        result["error"] = "trace file does not contain structLogs"
        return result

    tx_result = rpc.call("eth_getTransactionByHash", [tx_hash])
    if not tx_result:
        result["error"] = "transaction not found from RPC"
        return result

    top_level_to = row.get("top_level_to") or tx_result.get("to") or ""
    top_level_from = row.get("top_level_from") or tx_result.get("from") or ""
    if not top_level_to:
        result["error"] = "contract creation traces are not supported yet"
        return result

    analysis = analyze_trace(struct_logs, str(top_level_to), str(top_level_from))
    result["unsupported_ops"] = sorted(analysis.unsupported_ops)
    if analysis.unsupported_ops:
        result["error"] = f"unsupported trace ops: {', '.join(sorted(analysis.unsupported_ops))}"
        return result

    block_number = parse_int(row.get("receipt_block_number") or row.get("sample_block_number") or tx_result.get("blockNumber"))
    block_tag = ensure_hex_prefix(hex(block_number))
    block_result = rpc.call("eth_getBlockByNumber", [block_tag, False])
    coinbase = normalize_address(block_result.get("miner") or block_result.get("author"))

    account_payloads: Dict[str, Dict[str, Any]] = {}
    account_codes: Dict[str, str] = {}
    accounts_to_fetch = analysis.accounts | {
        normalize_address(top_level_to),
        normalize_address(top_level_from),
        coinbase,
    }
    for address in sorted(accounts_to_fetch):
        storage_keys = sorted(analysis.storage_keys.get(address) or set())
        account_payloads[address] = rpc.call("eth_getProof", [address, storage_keys, block_tag])
        if address in analysis.code_accounts or address == normalize_address(top_level_to):
            account_codes[address] = str(rpc.call("eth_getCode", [address, block_tag]) or "0x").lower()
        else:
            account_codes[address] = "0x"

    state_payload = build_state_payload(
        row=row,
        tx_result=tx_result,
        block_result=block_result,
        analysis=analysis,
        account_payloads=account_payloads,
        account_codes=account_codes,
        top_level_to=str(top_level_to),
        top_level_from=str(top_level_from),
    )

    tx_dir = Path(args.output_root) / dataset / tx_hash
    state_path = tx_dir / "state.json"
    bytecode_path = tx_dir / "bytecode.evm.hex"
    metadata_path = tx_dir / "prepared.json"

    top_level_code = account_codes[normalize_address(top_level_to)]
    if not top_level_code:
        top_level_code = "0x"

    write_json(state_path, state_payload)
    write_text(bytecode_path, f"{strip_hex_prefix(top_level_code)}\n")

    command = build_command(
        bytecode_path=bytecode_path,
        state_path=state_path,
        tx_result=tx_result,
        top_level_to=str(top_level_to),
        top_level_from=str(top_level_from),
        mode=args.mode,
        evm_revision=args.evm_revision,
        num_extra_executions=args.num_extra_executions,
    )

    observed_storage_slots = len(analysis.storage_values)
    total_storage_slots = sum(len(keys) for keys in analysis.storage_keys.values())
    metadata = {
        "dataset": dataset,
        "tx_hash": tx_hash,
        "trace_path": str(trace_path),
        "state_path": str(state_path),
        "bytecode_path": str(bytecode_path),
        "top_level_to": normalize_address(top_level_to),
        "top_level_from": normalize_address(top_level_from),
        "block_number": block_number,
        "accounts": len(analysis.accounts),
        "code_accounts": len(analysis.code_accounts),
        "storage_slots": total_storage_slots,
        "observed_storage_slots": observed_storage_slots,
        "proof_backfilled_slots": total_storage_slots - observed_storage_slots,
        "block_hash_values": analysis.block_hash_values,
        "command": command,
    }
    write_json(metadata_path, metadata)

    result.update(
        {
            "ready": True,
            "state_path": str(state_path),
            "bytecode_path": str(bytecode_path),
            "prepared_metadata_path": str(metadata_path),
            "command": command,
            "block_number": block_number,
            "accounts": len(analysis.accounts),
            "storage_slots": total_storage_slots,
            "observed_storage_slots": observed_storage_slots,
            "proof_backfilled_slots": total_storage_slots - observed_storage_slots,
        }
    )
    return result


def command_prepare_one(args: argparse.Namespace) -> int:
    row = find_row_by_tx_hash(Path(args.jsonl), args.tx_hash)
    if row is None:
        payload = {"ready": False, "error": f"tx hash not found in {args.jsonl}: {args.tx_hash}"}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    rpc = JsonRpcClient(args.rpc_url, Path(args.cache_dir), timeout=args.timeout_seconds)
    search_roots = [Path(root).resolve() for root in args.trace_search_root]
    result = prepare_row(row, args, rpc, search_roots)
    result["rpc_network_calls"] = rpc.network_calls
    result["rpc_cache_hits"] = rpc.cache_hits
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


def command_prepare_manifest(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    perf_root = Path(args.perf_root)
    rpc = JsonRpcClient(args.rpc_url, Path(args.cache_dir), timeout=args.timeout_seconds)
    search_roots = [Path(root).resolve() for root in args.trace_search_root]

    dataset_rows: Dict[str, Dict[str, Dict[str, Any]]] = {}
    items: List[Dict[str, Any]] = []
    for entry in manifest:
        dataset = str(entry.get("dataset") or "")
        tx_hash = str(entry.get("tx_hash") or "")
        if not dataset or not tx_hash:
            items.append({"ready": False, "error": "manifest entry missing dataset/tx_hash"})
            continue

        if dataset not in dataset_rows:
            perf_path = perf_root / f"{dataset}.jsonl"
            if not perf_path.exists():
                dataset_rows[dataset] = {}
            else:
                dataset_rows[dataset] = {
                    str(row.get("tx_hash") or "").lower(): row for row in load_jsonl(perf_path)
                }

        row = dataset_rows[dataset].get(tx_hash.lower())
        if row is None:
            items.append({"dataset": dataset, "tx_hash": tx_hash, "ready": False, "error": "perf row not found"})
            continue

        items.append(prepare_row(row, args, rpc, search_roots))

    payload = {
        "prepared": sum(1 for item in items if item.get("ready")),
        "failed": sum(1 for item in items if not item.get("ready")),
        "rpc_network_calls": rpc.network_calls,
        "rpc_cache_hits": rpc.cache_hits,
        "items": items,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["failed"] == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare DTVM replay inputs from trace-backed tx rows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_arguments(common_parser: argparse.ArgumentParser) -> None:
        common_parser.add_argument(
            "--rpc-url",
            default=os.environ.get("ETH_RPC_URL") or os.environ.get("ARCHIVE_RPC_URL") or "",
            help="Ethereum RPC URL; defaults to ETH_RPC_URL or ARCHIVE_RPC_URL",
        )
        common_parser.add_argument(
            "--cache-dir",
            default=str(DEFAULT_CACHE_DIR),
            help=f"Disk cache for RPC responses (default: {DEFAULT_CACHE_DIR})",
        )
        common_parser.add_argument(
            "--output-root",
            default=str(REPO_ROOT / "data" / "tx_replay_prepare"),
            help="Output directory for generated state/bytecode/manifest files",
        )
        common_parser.add_argument(
            "--trace-search-root",
            action="append",
            default=[str(REPO_ROOT), str(REPO_ROOT / "tests" / "fulltrace_transactions")],
            help="Extra root to search when the trace_path in JSONL is stale",
        )
        common_parser.add_argument("--timeout-seconds", type=float, default=30.0)
        common_parser.add_argument("--mode", default="multipass", choices=["interpreter", "multipass"])
        common_parser.add_argument("--evm-revision", default="cancun")
        common_parser.add_argument("--num-extra-executions", type=int, default=0)

    prepare_one = subparsers.add_parser("prepare-one", help="Prepare one tx from a JSONL corpus row")
    prepare_one.add_argument("--jsonl", required=True, help="Input JSONL file containing tx rows")
    prepare_one.add_argument("--tx-hash", required=True, help="Transaction hash to prepare")
    add_common_arguments(prepare_one)
    prepare_one.set_defaults(func=command_prepare_one)

    prepare_manifest = subparsers.add_parser("prepare-manifest", help="Prepare all entries from a replay manifest")
    prepare_manifest.add_argument("--manifest", required=True, help="Manifest JSON (e.g. replay_hotset_manifest.json)")
    prepare_manifest.add_argument("--perf-root", required=True, help="Directory containing per-dataset perf JSONL files")
    add_common_arguments(prepare_manifest)
    prepare_manifest.set_defaults(func=command_prepare_manifest)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.rpc_url:
        parser.error("missing --rpc-url and ETH_RPC_URL/ARCHIVE_RPC_URL are not set")
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
