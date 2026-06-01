#!/usr/bin/env python3
"""
Transaction corpus helper for DTVM workload analysis.

The tool is designed for "free RPC" workflows:

- Etherscan is used for cheap candidate discovery.
- JSON-RPC is used for enrichment with aggressive local caching.
- Sampling prefers diversity across template/codehash, gas, and calldata size.

Examples:

  python3 tools/tx_corpus.py report-existing \
    --input-dir tests/fulltrace_transactions

  python3 tools/tx_corpus.py collect \
    --dataset erc4337_bundle \
    --from-block 25000000 \
    --to-block 25010000 \
    --output data/tx_corpus/erc4337_candidates.jsonl

  python3 tools/tx_corpus.py enrich \
    --input data/tx_corpus/erc4337_candidates.jsonl \
    --output data/tx_corpus/erc4337_enriched.jsonl \
    --cache-dir .cache/tx_corpus \
    --max-rpc-calls 500 \
    --trace-method none

  python3 tools/tx_corpus.py sample \
    --input data/tx_corpus/erc4337_enriched.jsonl \
    --output data/tx_corpus/erc4337_perf.jsonl \
    --target-count 50

  python3 tools/tx_corpus.py estimate-budget \
    --input data/tx_corpus/erc4337_candidates.jsonl \
    --trace-transactions 20
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
UNISWAP_V3_SWAP_TOPIC0 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
ERC4337_USER_OPERATION_TOPIC0 = "0x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f"
COW_TRADE_TOPIC0 = "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17"
COW_SETTLEMENT_TOPIC0 = "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4"

DEFAULT_CONFIG: Dict[str, Any] = {
    "etherscan": {
        "base_url": "https://api.etherscan.io/v2/api",
        "chainid": 1,
        "api_key_env": "ETHERSCAN_API_KEY",
    },
    "rpc": {
        "url_env": "ETH_RPC_URL",
        "trace_method": "debug_traceTransaction",
    },
    "datasets": {
        "erc20_transfer": {
            "mode": "logs",
            "topics": [TRANSFER_TOPIC0],
            "addresses": [
                "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xdac17f958d2ee523a2206206994597c13d831ec7",
                "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
                "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",
            ],
            "performance_target": 60,
        },
        "uniswap_v3_swap": {
            "mode": "logs",
            "topics": [UNISWAP_V3_SWAP_TOPIC0],
            "addresses": [],
            "performance_target": 60,
        },
        "erc4337_bundle": {
            "mode": "logs",
            "topics": [ERC4337_USER_OPERATION_TOPIC0],
            "addresses": [
                "0x0000000071727de22e5e9d8baf0edac6f37da032",
                "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789",
                "0x4337084d9e255ff0702461cf8895ce9e3b5ff108",
            ],
            "performance_target": 60,
        },
        "cow_settlement": {
            "mode": "logs",
            "topics": [COW_TRADE_TOPIC0, COW_SETTLEMENT_TOPIC0],
            "addresses": [
                "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
            ],
            "performance_target": 30,
        },
        "uniswapx_reactor": {
            "mode": "txlist",
            "topics": [],
            "addresses": [
                "0x00000011f84b9aa48e5f8aa8b9897600006289be",
                "0x6000da47483062a0d734ba3dc7576ce6a0b645c4",
            ],
            "performance_target": 30,
        },
    },
}

DEFAULT_CAMPAIGN_PLAN: Dict[str, Any] = {
    "output_root": "data/tx_corpus_campaign",
    "cache_dir": ".cache/tx_corpus",
    "trace_output_dir": "data/tx_corpus_campaign/traces",
    "collect": {
        "chunk_size": 5000,
        "page_size": 1000,
        "max_etherscan_calls": 60,
        "sleep_seconds": 0.2,
        "timeout_seconds": 30.0,
        "txlist_sort": "asc",
        "allow_missing_api_key": False,
    },
    "enrich": {
        "sleep_seconds": 0.0,
        "timeout_seconds": 30.0,
        "max_rpc_calls": 1200,
        "max_trace_calls": 0,
        "code_block_tag": "latest",
        "trace_method": "none",
        "skip_done": True,
        "continue_on_error": True,
    },
    "sample": {
        "seed": 0,
        "require_done": True,
        "exclude_trace_failed": True,
    },
    "datasets": {
        "erc20_transfer": {
            "enabled": True,
            "input_path": "tests/fulltrace_transactions/erc20_transfer_transactions.jsonl",
            "collect_max_transactions": 0,
            "enrich_enabled": False,
            "pre_enrich_sample_count": None,
            "sample_target_count": 50,
        },
        "uniswap_v3_swap": {
            "enabled": True,
            "input_path": "tests/fulltrace_transactions/uniswap_v3_swap_transactions.jsonl",
            "collect_max_transactions": 0,
            "enrich_enabled": False,
            "pre_enrich_sample_count": None,
            "sample_target_count": 50,
        },
        "erc4337_bundle": {
            "enabled": True,
            "input_path": "tests/fulltrace_transactions/erc4337_bundle_transactions.jsonl",
            "collect_max_transactions": 0,
            "enrich_enabled": True,
            "pre_enrich_sample_count": 80,
            "sample_target_count": 50,
        },
        "cow_settlement": {
            "enabled": True,
            "input_path": "tests/fulltrace_transactions/cow_settlement_transactions.jsonl",
            "collect_max_transactions": 0,
            "enrich_enabled": True,
            "pre_enrich_sample_count": 40,
            "sample_target_count": 25,
        },
        "uniswapx_reactor": {
            "enabled": True,
            "input_path": None,
            "from_block": None,
            "to_block": None,
            "collect_max_transactions": 80,
            "enrich_enabled": True,
            "pre_enrich_sample_count": None,
            "sample_target_count": 25,
        },
    },
}

CANONICAL_FIELD_ORDER = [
    "dataset",
    "tx_hash",
    "trace_path",
    "trace_source",
    "source",
    "generated_at",
    "sample_dataset",
    "sample_tx_hash",
    "sample_block_number",
    "sample_transaction_index",
    "sample_log_index",
    "sample_emitter_address",
    "sample_topic0",
    "sample_source",
    "matched_logs",
    "matched_emitters",
    "receipt_type",
    "receipt_status",
    "receipt_from",
    "receipt_to",
    "receipt_contract_address",
    "receipt_gas_used",
    "receipt_effective_gas_price",
    "receipt_transaction_hash",
    "receipt_transaction_index",
    "receipt_block_number",
    "top_level_to",
    "top_level_from",
    "selector",
    "calldata_size",
    "gas_limit",
    "gas_used",
    "status",
    "effective_gas_price",
    "tx_value",
    "top_level_codehash",
    "top_level_template_hash",
    "top_level_template_hash_source",
    "tx_input",
    "trace_failed",
    "trace_gas",
    "trace_return_value",
    "candidate_enrichment_status",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        return int(value, 16) if value.startswith(("0x", "0X")) else int(value)
    raise ValueError(f"unsupported integer value: {value!r}")


def lower_hex(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    text = value.strip()
    if not text:
        return None
    return text.lower()


def input_selector(input_hex: Optional[str]) -> str:
    if not input_hex:
        return ""
    text = input_hex.lower()
    return text[:10] if text.startswith("0x") and len(text) >= 10 else ""


def calldata_size(input_hex: Optional[str]) -> int:
    if not input_hex:
        return 0
    text = input_hex[2:] if input_hex.startswith("0x") else input_hex
    return len(text) // 2


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Optional[str]) -> Dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not path:
        return config
    with open(path, "r", encoding="utf-8") as handle:
        override = json.load(handle)
    return deep_merge(config, override)


def load_campaign_plan(path: Optional[str]) -> Tuple[Dict[str, Any], Path]:
    plan = copy.deepcopy(DEFAULT_CAMPAIGN_PLAN)
    base_dir = Path.cwd()
    if not path:
        return plan, base_dir
    plan_path = Path(path).resolve()
    with plan_path.open("r", encoding="utf-8") as handle:
        override = json.load(handle)
    return deep_merge(plan, override), plan_path.parent


def resolve_path(base_dir: Path, value: Optional[str]) -> Optional[Path]:
    if value in (None, ""):
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()


def canonicalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    ordered: Dict[str, Any] = {}
    for key in CANONICAL_FIELD_ORDER:
        if key in row:
            ordered[key] = row[key]
    for key in sorted(row.keys()):
        if key not in ordered:
            ordered[key] = row[key]
    return ordered


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                rows.append(json.loads(line))
            else:
                rows.append({"tx_hash": line})
    return rows


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(canonicalize_row(row), ensure_ascii=True))
            handle.write("\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def keccak_hex(code_hex: Optional[str]) -> str:
    if not code_hex:
        return ""
    text = code_hex[2:] if code_hex.startswith("0x") else code_hex
    if not text:
        return ""
    payload = bytes.fromhex(text)

    try:
        from eth_hash.auto import keccak  # type: ignore

        return "0x" + keccak(payload).hex()
    except ImportError:
        try:
            from Crypto.Hash import keccak as crypto_keccak  # type: ignore

            digest = crypto_keccak.new(digest_bits=256)
            digest.update(payload)
            return "0x" + digest.hexdigest()
        except ImportError:
            return ""


class CallBudget:
    def __init__(
        self,
        max_ordinary_calls: Optional[int],
        max_trace_calls: Optional[int],
    ) -> None:
        self.max_ordinary_calls = max_ordinary_calls
        self.max_trace_calls = max_trace_calls
        self.ordinary_calls = 0
        self.trace_calls = 0

    def charge(self, kind: str) -> None:
        if kind == "trace":
            if self.max_trace_calls is not None and self.trace_calls >= self.max_trace_calls:
                raise RuntimeError("trace RPC call budget exhausted")
            self.trace_calls += 1
            return

        if self.max_ordinary_calls is not None and self.ordinary_calls >= self.max_ordinary_calls:
            raise RuntimeError("ordinary RPC call budget exhausted")
        self.ordinary_calls += 1

    def summary(self) -> Dict[str, int]:
        return {
            "ordinary_calls": self.ordinary_calls,
            "trace_calls": self.trace_calls,
        }


class CachedHttpClient:
    def __init__(
        self,
        cache_dir: Path,
        sleep_seconds: float,
        timeout_seconds: float,
        budget: Optional[CallBudget],
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sleep_seconds = sleep_seconds
        self.timeout_seconds = timeout_seconds
        self.budget = budget

    def _cache_path(self, namespace: str, payload: Dict[str, Any]) -> Path:
        key = sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return self.cache_dir / namespace / f"{key}.json"

    def _load_cache(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_cache(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True)

    def get_json(self, namespace: str, url: str, params: Dict[str, Any], kind: str = "ordinary") -> Dict[str, Any]:
        payload = {"method": "GET", "url": url, "params": params}
        cache_path = self._cache_path(namespace, payload)
        cached = self._load_cache(cache_path)
        if cached is not None:
            return cached

        if self.budget is not None:
            self.budget.charge(kind)
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)

        query = urllib.parse.urlencode(params)
        request_url = f"{url}?{query}"
        request = urllib.request.Request(request_url, method="GET")
        request.add_header("User-Agent", "DTVM tx_corpus tool")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        self._save_cache(cache_path, data)
        return data

    def post_json(self, namespace: str, url: str, payload: Dict[str, Any], kind: str = "ordinary") -> Dict[str, Any]:
        cache_path = self._cache_path(namespace, {"method": "POST", "url": url, "payload": payload})
        cached = self._load_cache(cache_path)
        if cached is not None:
            return cached

        if self.budget is not None:
            self.budget.charge(kind)
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)

        encoded = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=encoded, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "DTVM tx_corpus tool")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        self._save_cache(cache_path, data)
        return data


class EtherscanClient:
    def __init__(self, http_client: CachedHttpClient, base_url: str, chainid: int, api_key: str) -> None:
        self.http_client = http_client
        self.base_url = base_url
        self.chainid = chainid
        self.api_key = api_key

    def _call(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        full_params = dict(params)
        full_params["chainid"] = self.chainid
        if self.api_key:
            full_params["apikey"] = self.api_key
        response = self.http_client.get_json("etherscan", self.base_url, full_params)
        result = response.get("result", [])
        if isinstance(result, list):
            return result
        if isinstance(result, str) and result.lower().startswith("no "):
            return []
        raise RuntimeError(f"Etherscan response error: {response}")

    def get_logs(
        self,
        start_block: int,
        end_block: int,
        topic0: str,
        address: Optional[str],
        page: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        params = {
            "module": "logs",
            "action": "getLogs",
            "fromBlock": start_block,
            "toBlock": end_block,
            "topic0": topic0,
            "page": page,
            "offset": offset,
        }
        if address:
            params["address"] = address
        return self._call(params)

    def get_txlist(
        self,
        address: str,
        start_block: int,
        end_block: int,
        page: int,
        offset: int,
        sort: str,
    ) -> List[Dict[str, Any]]:
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
        }
        return self._call(params)


class RpcClient:
    def __init__(self, http_client: CachedHttpClient, rpc_url: str) -> None:
        self.http_client = http_client
        self.rpc_url = rpc_url

    def call(self, method: str, params: Sequence[Any], kind: str = "ordinary") -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": list(params),
        }
        response = self.http_client.post_json("rpc", self.rpc_url, payload, kind=kind)
        if "error" in response:
            raise RuntimeError(f"RPC {method} error: {response['error']}")
        return response.get("result")


def iter_block_ranges(start_block: int, end_block: int, chunk_size: int) -> Iterator[Tuple[int, int]]:
    current = start_block
    while current <= end_block:
        chunk_end = min(end_block, current + chunk_size - 1)
        yield current, chunk_end
        current = chunk_end + 1


def merge_candidate_row(existing: Optional[Dict[str, Any]], candidate: Dict[str, Any]) -> Dict[str, Any]:
    if existing is None:
        return candidate
    existing["matched_logs"] = (existing.get("matched_logs") or 0) + (candidate.get("matched_logs") or 0)
    emitters = set(existing.get("matched_emitters") or [])
    emitters.update(candidate.get("matched_emitters") or [])
    existing["matched_emitters"] = sorted(emitters)
    return existing


def candidate_from_log(dataset: str, log_row: Dict[str, Any]) -> Dict[str, Any]:
    tx_hash = lower_hex(log_row.get("transactionHash")) or ""
    emitter = lower_hex(log_row.get("address"))
    topics = log_row.get("topics") or []
    return {
        "dataset": dataset,
        "tx_hash": tx_hash,
        "trace_path": "",
        "trace_source": "",
        "source": "etherscan:getLogs",
        "generated_at": now_iso(),
        "sample_dataset": dataset,
        "sample_tx_hash": tx_hash,
        "sample_block_number": parse_int(log_row.get("blockNumber")),
        "sample_transaction_index": parse_int(log_row.get("transactionIndex")),
        "sample_log_index": parse_int(log_row.get("logIndex")),
        "sample_emitter_address": emitter,
        "sample_topic0": lower_hex(topics[0]) if topics else None,
        "sample_source": "etherscan:getLogs",
        "matched_logs": 1,
        "matched_emitters": [emitter] if emitter else [],
        "trace_failed": None,
        "trace_gas": None,
        "trace_return_value": None,
        "candidate_enrichment_status": "pending",
    }


def candidate_from_txlist(dataset: str, seed_address: str, tx_row: Dict[str, Any]) -> Dict[str, Any]:
    tx_hash = lower_hex(tx_row.get("hash")) or ""
    return {
        "dataset": dataset,
        "tx_hash": tx_hash,
        "trace_path": "",
        "trace_source": "",
        "source": "etherscan:txlist",
        "generated_at": now_iso(),
        "sample_dataset": dataset,
        "sample_tx_hash": tx_hash,
        "sample_block_number": parse_int(tx_row.get("blockNumber")),
        "sample_transaction_index": parse_int(tx_row.get("transactionIndex")),
        "sample_log_index": None,
        "sample_emitter_address": lower_hex(seed_address),
        "sample_topic0": None,
        "sample_source": "etherscan:txlist",
        "matched_logs": 0,
        "matched_emitters": [],
        "selector": lower_hex(tx_row.get("methodId")) or "",
        "trace_failed": None,
        "trace_gas": None,
        "trace_return_value": None,
        "candidate_enrichment_status": "pending",
    }


def resolve_dataset_config(config: Dict[str, Any], dataset: str) -> Dict[str, Any]:
    try:
        return config["datasets"][dataset]
    except KeyError as exc:
        raise SystemExit(f"unknown dataset: {dataset}") from exc


def sort_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("dataset") or "",
            parse_int(row.get("sample_block_number")) or parse_int(row.get("receipt_block_number")) or 0,
            parse_int(row.get("sample_transaction_index")) or parse_int(row.get("receipt_transaction_index")) or 0,
            parse_int(row.get("sample_log_index")) or 0,
            row.get("tx_hash") or row.get("sample_tx_hash") or "",
        ),
    )


def template_key(row: Dict[str, Any]) -> str:
    for key in (
        "top_level_template_hash",
        "top_level_codehash",
        "top_level_to",
        "sample_emitter_address",
        "tx_hash",
    ):
        value = lower_hex(row.get(key))
        if value:
            return value
    return "unknown"


def numeric_gas(row: Dict[str, Any]) -> Optional[int]:
    for key in ("gas_used", "trace_gas", "receipt_gas_used"):
        value = parse_int(row.get(key))
        if value is not None:
            return value
    return None


def gas_bucket(value: Optional[int]) -> str:
    if value is None:
        return "unknown"
    if value < 80_000:
        return "lt80k"
    if value < 200_000:
        return "80k-200k"
    if value < 500_000:
        return "200k-500k"
    if value < 1_000_000:
        return "500k-1m"
    return "gte1m"


def calldata_bucket(value: Optional[int]) -> str:
    if value is None:
        return "unknown"
    if value == 0:
        return "0"
    if value <= 128:
        return "1-128"
    if value <= 512:
        return "129-512"
    if value <= 2048:
        return "513-2048"
    return "gt2048"


def stable_tiebreak(tx_hash: str, seed: int) -> int:
    return int(sha256_text(f"{seed}:{tx_hash}")[:12], 16)


def choose_representative(rows: Sequence[Dict[str, Any]], seed: int) -> Dict[str, Any]:
    return sorted(
        rows,
        key=lambda row: (
            -int(not bool(row.get("trace_failed"))),
            -int((row.get("candidate_enrichment_status") or "") == "done"),
            -(numeric_gas(row) or 0),
            -(parse_int(row.get("calldata_size")) or 0),
            stable_tiebreak(row.get("tx_hash") or "", seed),
        ),
    )[0]


def greedy_sample(rows: Sequence[Dict[str, Any]], target_count: int, seed: int) -> List[Dict[str, Any]]:
    if target_count >= len(rows):
        return sort_rows(rows)

    by_template: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_template[template_key(row)].append(row)

    selected: List[Dict[str, Any]] = []
    selected_hashes: set[str] = set()

    for key in sorted(by_template.keys(), key=lambda item: (len(by_template[item]), item)):
        representative = choose_representative(by_template[key], seed)
        tx_hash = representative.get("tx_hash") or ""
        if tx_hash in selected_hashes:
            continue
        selected.append(representative)
        selected_hashes.add(tx_hash)
        if len(selected) >= target_count:
            return sort_rows(selected)

    strata: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        tx_hash = row.get("tx_hash") or ""
        if tx_hash in selected_hashes:
            continue
        strata[
            (
                template_key(row),
                gas_bucket(numeric_gas(row)),
                calldata_bucket(parse_int(row.get("calldata_size"))),
            )
        ].append(row)

    for stratum_key in sorted(strata.keys()):
        representative = choose_representative(strata[stratum_key], seed)
        tx_hash = representative.get("tx_hash") or ""
        if tx_hash in selected_hashes:
            continue
        selected.append(representative)
        selected_hashes.add(tx_hash)
        if len(selected) >= target_count:
            return sort_rows(selected)

    remaining = sorted(
        [row for row in rows if (row.get("tx_hash") or "") not in selected_hashes],
        key=lambda row: (
            stable_tiebreak(row.get("tx_hash") or "", seed),
            row.get("tx_hash") or "",
        ),
    )
    for row in remaining:
        selected.append(row)
        if len(selected) >= target_count:
            break
    return sort_rows(selected)


def trace_summary(trace_result: Any) -> Tuple[Optional[bool], Optional[int], Optional[str]]:
    if isinstance(trace_result, dict):
        failed = trace_result.get("failed")
        if failed is None and trace_result.get("error") is not None:
            failed = True
        gas = parse_int(trace_result.get("gasUsed"))
        if gas is None:
            gas = parse_int(trace_result.get("gas"))
        output = trace_result.get("returnValue")
        if output is None:
            output = trace_result.get("output")
        return failed, gas, lower_hex(output)
    return None, None, None


def save_trace(trace_dir: Path, dataset: str, tx_hash: str, payload: Any) -> str:
    dataset_dir = trace_dir / dataset
    dataset_dir.mkdir(parents=True, exist_ok=True)
    path = dataset_dir / f"{tx_hash}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
    return str(path)


def enrich_row(
    row: Dict[str, Any],
    rpc_client: RpcClient,
    code_block_tag: str,
    trace_method: str,
    trace_dir: Optional[Path],
) -> Dict[str, Any]:
    tx_hash = lower_hex(row.get("tx_hash") or row.get("sample_tx_hash"))
    if not tx_hash:
        enriched = dict(row)
        enriched["candidate_enrichment_status"] = "pending"
        return enriched

    tx = rpc_client.call("eth_getTransactionByHash", [tx_hash])
    receipt = rpc_client.call("eth_getTransactionReceipt", [tx_hash])
    if tx is None or receipt is None:
        enriched = dict(row)
        enriched["tx_hash"] = tx_hash
        enriched["candidate_enrichment_status"] = "pending"
        return enriched

    top_level_to = lower_hex(tx.get("to"))
    block_number = parse_int(receipt.get("blockNumber"))
    codehash = ""
    if top_level_to:
        block_tag: Any = "latest" if code_block_tag == "latest" or block_number is None else hex(block_number)
        code = rpc_client.call("eth_getCode", [top_level_to, block_tag])
        codehash = keccak_hex(code)

    input_hex = lower_hex(tx.get("input")) or "0x"
    enriched = dict(row)
    enriched.update(
        {
            "dataset": row.get("dataset") or row.get("sample_dataset") or "unknown",
            "tx_hash": tx_hash,
            "generated_at": now_iso(),
            "receipt_type": lower_hex(receipt.get("type") or tx.get("type")),
            "receipt_status": lower_hex(receipt.get("status")),
            "receipt_from": lower_hex(receipt.get("from")),
            "receipt_to": lower_hex(receipt.get("to")),
            "receipt_contract_address": lower_hex(receipt.get("contractAddress")),
            "receipt_gas_used": lower_hex(receipt.get("gasUsed")),
            "receipt_effective_gas_price": lower_hex(receipt.get("effectiveGasPrice") or tx.get("gasPrice")),
            "receipt_transaction_hash": lower_hex(receipt.get("transactionHash")),
            "receipt_transaction_index": lower_hex(receipt.get("transactionIndex")),
            "receipt_block_number": lower_hex(receipt.get("blockNumber")),
            "top_level_to": top_level_to,
            "top_level_from": lower_hex(tx.get("from")),
            "selector": input_selector(input_hex),
            "calldata_size": calldata_size(input_hex),
            "gas_limit": parse_int(tx.get("gas")),
            "gas_used": parse_int(receipt.get("gasUsed")),
            "status": parse_int(receipt.get("status")),
            "effective_gas_price": parse_int(receipt.get("effectiveGasPrice") or tx.get("gasPrice")),
            "tx_value": lower_hex(tx.get("value")),
            "tx_input": input_hex,
            "top_level_codehash": codehash,
            "top_level_template_hash": row.get("top_level_template_hash") or codehash,
            "top_level_template_hash_source": "codehash_fallback" if codehash else "",
            "candidate_enrichment_status": "done",
        }
    )

    if trace_method != "none" and trace_dir is not None:
        if trace_method == "debug_traceTransaction":
            trace_result = rpc_client.call(trace_method, [tx_hash, {}], kind="trace")
        else:
            trace_result = rpc_client.call(trace_method, [tx_hash], kind="trace")
        trace_failed, trace_gas, trace_return_value = trace_summary(trace_result)
        enriched["trace_path"] = save_trace(trace_dir, enriched["dataset"], tx_hash, trace_result)
        enriched["trace_source"] = trace_method
        enriched["trace_failed"] = trace_failed
        enriched["trace_gas"] = trace_gas
        enriched["trace_return_value"] = trace_return_value
    return enriched


def summarize_rows(dataset: str, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    unique_emitters: set[str] = set()
    unique_targets: set[str] = set()
    unique_codehashes: set[str] = set()
    unique_templates: set[str] = set()
    gas_values: List[int] = []
    calldata_values: List[int] = []

    pending_count = 0
    trace_failed = 0
    missing_selector = 0
    missing_codehash = 0
    missing_trace = 0

    for row in rows:
        for emitter in row.get("matched_emitters") or []:
            if emitter:
                unique_emitters.add(lower_hex(emitter) or "")

        target = lower_hex(row.get("top_level_to"))
        if target:
            unique_targets.add(target)

        codehash = lower_hex(row.get("top_level_codehash"))
        if codehash:
            unique_codehashes.add(codehash)
        else:
            missing_codehash += 1

        unique_templates.add(template_key(row))

        gas = numeric_gas(row)
        if gas is not None:
            gas_values.append(gas)

        size = parse_int(row.get("calldata_size"))
        if size is not None:
            calldata_values.append(size)

        if (row.get("candidate_enrichment_status") or "") != "done":
            pending_count += 1
        if row.get("trace_failed") is True:
            trace_failed += 1
        if not row.get("selector"):
            missing_selector += 1
        if not row.get("trace_path"):
            missing_trace += 1

    def percentile(values: Sequence[int], ratio: float) -> Optional[int]:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
        return ordered[index]

    return {
        "dataset": dataset,
        "row_count": len(rows),
        "pending_enrichment": pending_count,
        "trace_failed_true": trace_failed,
        "missing_selector": missing_selector,
        "missing_codehash": missing_codehash,
        "missing_trace_path": missing_trace,
        "unique_emitters": len(unique_emitters),
        "unique_top_level_to": len(unique_targets),
        "unique_codehashes": len(unique_codehashes),
        "unique_template_keys": len(unique_templates),
        "gas_p50": percentile(gas_values, 0.50),
        "gas_p90": percentile(gas_values, 0.90),
        "gas_p99": percentile(gas_values, 0.99),
        "calldata_p50": percentile(calldata_values, 0.50),
        "calldata_p90": percentile(calldata_values, 0.90),
    }


def percentile_value(values: Sequence[int], ratio: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def campaign_perf_summary(dataset: str, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    gas_values = [value for value in (numeric_gas(row) for row in rows) if value is not None]
    calldata_values = [value for value in (parse_int(row.get("calldata_size")) for row in rows) if value is not None]
    status_counter: CounterLike = CounterLike()
    selector_counter: CounterLike = CounterLike()
    template_counter: CounterLike = CounterLike()
    replay_ready = 0

    for row in rows:
        status_counter.add(str(row.get("status")))
        selector_counter.add(row.get("selector") or "<empty>")
        template_counter.add(template_key(row))
        if row.get("trace_path"):
            replay_ready += 1

    return {
        "dataset": dataset,
        "row_count": len(rows),
        "replay_ready_rows": replay_ready,
        "status_counts": status_counter.as_dict(),
        "top_selectors": selector_counter.top(5),
        "top_templates": template_counter.top(5),
        "unique_template_keys": len({template_key(row) for row in rows}),
        "gas_p50": percentile_value(gas_values, 0.50),
        "gas_p90": percentile_value(gas_values, 0.90),
        "gas_p99": percentile_value(gas_values, 0.99),
        "calldata_p50": percentile_value(calldata_values, 0.50),
        "calldata_p90": percentile_value(calldata_values, 0.90),
    }


class CounterLike:
    def __init__(self) -> None:
        self._counts: Dict[str, int] = {}

    def add(self, key: str) -> None:
        self._counts[key] = self._counts.get(key, 0) + 1

    def as_dict(self) -> Dict[str, int]:
        return dict(sorted(self._counts.items(), key=lambda kv: kv[0]))

    def top(self, limit: int) -> List[List[Any]]:
        return [[key, count] for key, count in sorted(self._counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def dataset_artifact_paths(output_root: Path, dataset: str) -> Dict[str, Path]:
    return {
        "candidate": output_root / "candidates" / f"{dataset}.jsonl",
        "pre_enrich": output_root / "working" / f"{dataset}_pre_enrich.jsonl",
        "enriched": output_root / "enriched" / f"{dataset}.jsonl",
        "perf": output_root / "perf" / f"{dataset}.jsonl",
        "report": output_root / "reports" / f"{dataset}.json",
    }


def run_collect_job(
    *,
    config: Dict[str, Any],
    dataset: str,
    from_block: int,
    to_block: int,
    output_path: Path,
    cache_dir: Path,
    chunk_size: int,
    page_size: int,
    max_transactions: int,
    max_etherscan_calls: int,
    sleep_seconds: float,
    timeout_seconds: float,
    txlist_sort: str,
    allow_missing_api_key: bool,
) -> Dict[str, Any]:
    dataset_config = resolve_dataset_config(config, dataset)
    api_key = os.environ.get(config["etherscan"]["api_key_env"], "")
    if not api_key and not allow_missing_api_key:
        raise SystemExit("missing ETHERSCAN_API_KEY; pass allow_missing_api_key or export the API key")

    budget = CallBudget(max_ordinary_calls=max_etherscan_calls, max_trace_calls=0)
    http_client = CachedHttpClient(
        cache_dir=cache_dir,
        sleep_seconds=sleep_seconds,
        timeout_seconds=timeout_seconds,
        budget=budget,
    )
    etherscan = EtherscanClient(
        http_client=http_client,
        base_url=config["etherscan"]["base_url"],
        chainid=int(config["etherscan"]["chainid"]),
        api_key=api_key,
    )

    candidates: Dict[str, Dict[str, Any]] = {}
    addresses = [lower_hex(item) for item in (dataset_config.get("addresses") or []) if lower_hex(item)]
    topics = [lower_hex(item) for item in (dataset_config.get("topics") or []) if lower_hex(item)]

    if dataset_config["mode"] == "logs":
        address_iter = addresses if addresses else [None]
        if not topics:
            raise SystemExit("log-based datasets require at least one topic0")

        for topic0 in topics:
            for address in address_iter:
                for start_block, end_block in iter_block_ranges(from_block, to_block, chunk_size):
                    page = 1
                    while True:
                        log_rows = etherscan.get_logs(
                            start_block,
                            end_block,
                            topic0=topic0 or "",
                            address=address,
                            page=page,
                            offset=page_size,
                        )
                        if not log_rows:
                            break
                        for log_row in log_rows:
                            candidate = candidate_from_log(dataset, log_row)
                            tx_hash = candidate["tx_hash"]
                            candidates[tx_hash] = merge_candidate_row(candidates.get(tx_hash), candidate)
                            if len(candidates) >= max_transactions:
                                break
                        if len(candidates) >= max_transactions or len(log_rows) < page_size:
                            break
                        page += 1
                    if len(candidates) >= max_transactions:
                        break
                if len(candidates) >= max_transactions:
                    break
            if len(candidates) >= max_transactions:
                break
    elif dataset_config["mode"] == "txlist":
        if not addresses:
            raise SystemExit(f"{dataset} requires configured seed addresses in the tx corpus config")
        for address in addresses:
            page = 1
            while True:
                tx_rows = etherscan.get_txlist(
                    address=address,
                    start_block=from_block,
                    end_block=to_block,
                    page=page,
                    offset=page_size,
                    sort=txlist_sort,
                )
                if not tx_rows:
                    break
                for tx_row in tx_rows:
                    candidate = candidate_from_txlist(dataset, address, tx_row)
                    tx_hash = candidate["tx_hash"]
                    candidates[tx_hash] = merge_candidate_row(candidates.get(tx_hash), candidate)
                    if len(candidates) >= max_transactions:
                        break
                if len(candidates) >= max_transactions or len(tx_rows) < page_size:
                    break
                page += 1
    else:
        raise SystemExit(f"unsupported dataset mode: {dataset_config['mode']}")

    rows = sort_rows(candidates.values())
    write_jsonl(output_path, rows)
    return {
        "dataset": dataset,
        "output": str(output_path),
        "candidate_rows": len(rows),
        "etherscan_calls": budget.summary()["ordinary_calls"],
    }


def run_enrich_job(
    *,
    input_path: Path,
    output_path: Path,
    rpc_url: str,
    cache_dir: Path,
    sleep_seconds: float,
    timeout_seconds: float,
    max_transactions: int,
    max_rpc_calls: Optional[int],
    max_trace_calls: int,
    code_block_tag: str,
    trace_method: str,
    trace_output_dir: Optional[Path],
    skip_done: bool,
    continue_on_error: bool,
) -> Dict[str, Any]:
    input_rows = read_jsonl(input_path)
    budget = CallBudget(
        max_ordinary_calls=max_rpc_calls,
        max_trace_calls=max_trace_calls,
    )
    http_client = CachedHttpClient(
        cache_dir=cache_dir,
        sleep_seconds=sleep_seconds,
        timeout_seconds=timeout_seconds,
        budget=budget,
    )
    rpc_client = RpcClient(http_client, rpc_url)

    output_rows: List[Dict[str, Any]] = []
    for row in input_rows[:max_transactions]:
        if skip_done and (row.get("candidate_enrichment_status") or "") == "done":
            output_rows.append(row)
            continue
        try:
            enriched = enrich_row(
                row=row,
                rpc_client=rpc_client,
                code_block_tag=code_block_tag,
                trace_method=trace_method,
                trace_dir=trace_output_dir,
            )
        except RuntimeError as exc:
            if not continue_on_error:
                raise
            enriched = dict(row)
            enriched["candidate_enrichment_status"] = "pending"
            enriched["enrichment_error"] = str(exc)
        output_rows.append(enriched)

    rows = sort_rows(output_rows)
    write_jsonl(output_path, rows)
    return {
        "input_rows": len(input_rows[:max_transactions]),
        "output_rows": len(rows),
        "rpc_calls": budget.summary()["ordinary_calls"],
        "trace_calls": budget.summary()["trace_calls"],
        "output": str(output_path),
    }


def run_sample_job(
    *,
    input_path: Path,
    output_path: Path,
    target_count: int,
    seed: int,
    require_done: bool,
    exclude_trace_failed: bool,
) -> Dict[str, Any]:
    rows = read_jsonl(input_path)
    filtered = []
    for row in rows:
        if require_done and (row.get("candidate_enrichment_status") or "") != "done":
            continue
        if exclude_trace_failed and row.get("trace_failed") is True:
            continue
        filtered.append(row)

    sampled = greedy_sample(filtered, target_count, seed)
    write_jsonl(output_path, sampled)
    return {
        "input_rows": len(rows),
        "eligible_rows": len(filtered),
        "sampled_rows": len(sampled),
        "unique_template_keys": len({template_key(row) for row in sampled}),
        "output": str(output_path),
    }


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def print_json_or_text(payload: Any, as_json: bool) -> None:
    if as_json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return
    if isinstance(payload, dict) and "datasets" in payload:
        for summary in payload["datasets"]:
            print(
                f"{summary['dataset']}: rows={summary['row_count']} pending={summary['pending_enrichment']} "
                f"trace_failed={summary['trace_failed_true']} missing_codehash={summary['missing_codehash']} "
                f"missing_selector={summary['missing_selector']}"
            )
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_report_existing(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*_transactions.jsonl"))
    summaries = []
    for path in files:
        rows = read_jsonl(path)
        dataset = rows[0].get("dataset") if rows else path.stem.replace("_transactions", "")
        summaries.append(summarize_rows(dataset, rows))
    print_json_or_text({"datasets": summaries}, args.json)
    return 0


def command_collect(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    summary = run_collect_job(
        config=config,
        dataset=args.dataset,
        from_block=args.from_block,
        to_block=args.to_block,
        output_path=Path(args.output),
        cache_dir=Path(args.cache_dir),
        chunk_size=args.chunk_size,
        page_size=args.page_size,
        max_transactions=args.max_transactions,
        max_etherscan_calls=args.max_etherscan_calls,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
        txlist_sort=args.txlist_sort,
        allow_missing_api_key=args.allow_missing_api_key,
    )
    print_json_or_text(summary, args.json)
    return 0


def command_enrich(args: argparse.Namespace) -> int:
    rpc_url = args.rpc_url or os.environ.get(args.rpc_url_env or "ETH_RPC_URL")
    if not rpc_url:
        raise SystemExit("missing RPC URL; pass --rpc-url or set ETH_RPC_URL")
    trace_dir = Path(args.trace_output_dir) if args.trace_output_dir else None
    summary = run_enrich_job(
        input_path=Path(args.input),
        output_path=Path(args.output),
        rpc_url=rpc_url,
        cache_dir=Path(args.cache_dir),
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
        max_transactions=args.max_transactions,
        max_rpc_calls=args.max_rpc_calls,
        max_trace_calls=args.max_trace_calls,
        code_block_tag=args.code_block_tag,
        trace_method=args.trace_method,
        trace_output_dir=trace_dir,
        skip_done=args.skip_done,
        continue_on_error=args.continue_on_error,
    )
    print_json_or_text(summary, args.json)
    return 0


def command_sample(args: argparse.Namespace) -> int:
    summary = run_sample_job(
        input_path=Path(args.input),
        output_path=Path(args.output),
        target_count=args.target_count,
        seed=args.seed,
        require_done=args.require_done,
        exclude_trace_failed=args.exclude_trace_failed,
    )
    print_json_or_text(summary, args.json)
    return 0


def estimate_budget_from_rows(
    rows: Sequence[Dict[str, Any]],
    trace_transactions: int,
    include_block_calls: bool,
    code_block_tag: str,
) -> Dict[str, Any]:
    tx_hashes: set[str] = set()
    code_keys: set[Tuple[str, str]] = set()
    block_numbers: set[int] = set()

    for row in rows:
        tx_hash = lower_hex(row.get("tx_hash") or row.get("sample_tx_hash"))
        if tx_hash:
            tx_hashes.add(tx_hash)

        address = lower_hex(row.get("top_level_to")) or lower_hex(row.get("receipt_to")) or lower_hex(row.get("sample_emitter_address"))
        if address:
            if row.get("top_level_codehash"):
                continue
            block_number = parse_int(row.get("receipt_block_number")) or parse_int(row.get("sample_block_number"))
            code_key = "latest" if code_block_tag == "latest" or block_number is None else str(block_number)
            code_keys.add((address, code_key))

        block_number = parse_int(row.get("receipt_block_number")) or parse_int(row.get("sample_block_number"))
        if block_number is not None:
            block_numbers.add(block_number)

    ordinary_calls = len(tx_hashes) * 2 + len(code_keys)
    if include_block_calls:
        ordinary_calls += len(block_numbers)

    return {
        "transactions": len(tx_hashes),
        "code_queries": len(code_keys),
        "block_queries": len(block_numbers) if include_block_calls else 0,
        "ordinary_rpc_calls": ordinary_calls,
        "trace_rpc_calls": trace_transactions,
        "total_rpc_calls": ordinary_calls + trace_transactions,
    }


def command_estimate_budget(args: argparse.Namespace) -> int:
    rows = read_jsonl(Path(args.input))
    summary = estimate_budget_from_rows(
        rows=rows,
        trace_transactions=args.trace_transactions,
        include_block_calls=args.include_block_calls,
        code_block_tag=args.code_block_tag,
    )
    print_json_or_text(summary, args.json)
    return 0


def selected_datasets(args: argparse.Namespace, plan: Dict[str, Any]) -> List[str]:
    available = [name for name, entry in plan["datasets"].items() if entry.get("enabled", True)]
    if not args.datasets:
        return available
    requested = [item.strip() for item in args.datasets.split(",") if item.strip()]
    unknown = sorted(set(requested) - set(plan["datasets"].keys()))
    if unknown:
        raise SystemExit(f"unknown campaign datasets: {', '.join(unknown)}")
    return [name for name in requested if plan["datasets"][name].get("enabled", True)]


def path_or_none(path: Optional[Path]) -> Optional[str]:
    return str(path) if path is not None else None


def command_campaign(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    plan, plan_base_dir = load_campaign_plan(args.plan)
    output_root = resolve_path(plan_base_dir, args.output_root or plan.get("output_root")) or Path("data/tx_corpus_campaign")
    cache_dir = resolve_path(plan_base_dir, plan.get("cache_dir")) or Path(".cache/tx_corpus")
    trace_output_dir = resolve_path(plan_base_dir, plan.get("trace_output_dir"))

    collect_defaults = plan.get("collect", {})
    enrich_defaults = plan.get("enrich", {})
    sample_defaults = plan.get("sample", {})

    campaign_summary: Dict[str, Any] = {
        "phase": args.phase,
        "dry_run": args.dry_run,
        "output_root": str(output_root),
        "datasets": [],
    }

    if not args.dry_run:
        (output_root / "manifests").mkdir(parents=True, exist_ok=True)

    for dataset in selected_datasets(args, plan):
        dataset_plan = plan["datasets"][dataset]
        artifacts = dataset_artifact_paths(output_root, dataset)
        input_path = resolve_path(plan_base_dir, dataset_plan.get("input_path"))
        source_path = input_path or artifacts["candidate"]
        dataset_summary: Dict[str, Any] = {
            "dataset": dataset,
            "input_path": path_or_none(input_path),
            "candidate_path": str(artifacts["candidate"]),
            "pre_enrich_path": str(artifacts["pre_enrich"]),
            "enriched_path": str(artifacts["enriched"]),
            "perf_path": str(artifacts["perf"]),
            "steps": [],
        }

        collect_max_transactions = int(dataset_plan.get("collect_max_transactions") or 0)
        enrich_enabled = bool(dataset_plan.get("enrich_enabled", True))
        pre_enrich_sample_count = dataset_plan.get("pre_enrich_sample_count")
        sample_target_count = int(dataset_plan.get("sample_target_count") or 0)
        dry_run_pre_enrich_rows: Optional[List[Dict[str, Any]]] = None

        if args.phase in ("collect", "all") and collect_max_transactions > 0 and input_path is None:
            from_block = dataset_plan.get("from_block")
            to_block = dataset_plan.get("to_block")
            if from_block is None or to_block is None:
                raise SystemExit(f"{dataset} requires from_block/to_block in the campaign plan")

            step = {
                "name": "collect",
                "from_block": from_block,
                "to_block": to_block,
                "max_transactions": collect_max_transactions,
                "output": str(artifacts["candidate"]),
            }
            if args.dry_run:
                dataset_summary["steps"].append(step)
            else:
                step["result"] = run_collect_job(
                    config=config,
                    dataset=dataset,
                    from_block=int(from_block),
                    to_block=int(to_block),
                    output_path=artifacts["candidate"],
                    cache_dir=cache_dir,
                    chunk_size=int(collect_defaults.get("chunk_size", 5000)),
                    page_size=int(collect_defaults.get("page_size", 1000)),
                    max_transactions=collect_max_transactions,
                    max_etherscan_calls=int(collect_defaults.get("max_etherscan_calls", 60)),
                    sleep_seconds=float(collect_defaults.get("sleep_seconds", 0.2)),
                    timeout_seconds=float(collect_defaults.get("timeout_seconds", 30.0)),
                    txlist_sort=str(collect_defaults.get("txlist_sort", "asc")),
                    allow_missing_api_key=bool(collect_defaults.get("allow_missing_api_key", False)),
                )
                dataset_summary["steps"].append(step)
            source_path = artifacts["candidate"]

        pre_enrich_source = source_path
        if enrich_enabled and pre_enrich_sample_count and args.phase in ("enrich", "all"):
            step = {
                "name": "pre_enrich_sample",
                "input": str(source_path),
                "output": str(artifacts["pre_enrich"]),
                "target_count": int(pre_enrich_sample_count),
            }
            if args.dry_run:
                if source_path.exists():
                    source_rows = read_jsonl(source_path)
                    estimated_input_rows = len(source_rows)
                    step["input_rows"] = estimated_input_rows
                    step["planned_rows"] = min(estimated_input_rows, int(pre_enrich_sample_count))
                    dry_run_pre_enrich_rows = greedy_sample(
                        source_rows,
                        int(pre_enrich_sample_count),
                        int(sample_defaults.get("seed", 0)),
                    )
                dataset_summary["steps"].append(step)
            else:
                sample_result = run_sample_job(
                    input_path=source_path,
                    output_path=artifacts["pre_enrich"],
                    target_count=int(pre_enrich_sample_count),
                    seed=int(sample_defaults.get("seed", 0)),
                    require_done=False,
                    exclude_trace_failed=False,
                )
                step["result"] = sample_result
                dataset_summary["steps"].append(step)
            pre_enrich_source = artifacts["pre_enrich"]

        if enrich_enabled and args.phase in ("enrich", "all"):
            step = {
                "name": "enrich",
                "input": str(pre_enrich_source),
                "output": str(artifacts["enriched"]),
                "max_rpc_calls": enrich_defaults.get("max_rpc_calls", 1200),
                "max_trace_calls": enrich_defaults.get("max_trace_calls", 0),
                "trace_method": enrich_defaults.get("trace_method", "none"),
            }
            if args.dry_run and dry_run_pre_enrich_rows is not None:
                trace_transactions = 0
                if step["trace_method"] != "none":
                    trace_transactions = len(dry_run_pre_enrich_rows)
                step["estimated_budget"] = estimate_budget_from_rows(
                    rows=dry_run_pre_enrich_rows,
                    trace_transactions=trace_transactions,
                    include_block_calls=False,
                    code_block_tag=str(enrich_defaults.get("code_block_tag", "latest")),
                )
            elif pre_enrich_source.exists():
                trace_transactions = 0
                if step["trace_method"] != "none":
                    trace_transactions = len(read_jsonl(pre_enrich_source))
                step["estimated_budget"] = estimate_budget_from_rows(
                    rows=read_jsonl(pre_enrich_source),
                    trace_transactions=trace_transactions,
                    include_block_calls=False,
                    code_block_tag=str(enrich_defaults.get("code_block_tag", "latest")),
                )
            if args.dry_run:
                dataset_summary["steps"].append(step)
            else:
                rpc_url = args.rpc_url or os.environ.get(args.rpc_url_env or "ETH_RPC_URL")
                if not rpc_url:
                    raise SystemExit("missing RPC URL; pass --rpc-url or set ETH_RPC_URL")
                step["result"] = run_enrich_job(
                    input_path=pre_enrich_source,
                    output_path=artifacts["enriched"],
                    rpc_url=rpc_url,
                    cache_dir=cache_dir,
                    sleep_seconds=float(enrich_defaults.get("sleep_seconds", 0.0)),
                    timeout_seconds=float(enrich_defaults.get("timeout_seconds", 30.0)),
                    max_transactions=int(dataset_plan.get("enrich_max_transactions") or 1_000_000),
                    max_rpc_calls=(None if enrich_defaults.get("max_rpc_calls") is None else int(enrich_defaults.get("max_rpc_calls"))),
                    max_trace_calls=int(enrich_defaults.get("max_trace_calls", 0)),
                    code_block_tag=str(enrich_defaults.get("code_block_tag", "latest")),
                    trace_method=str(enrich_defaults.get("trace_method", "none")),
                    trace_output_dir=trace_output_dir,
                    skip_done=bool(enrich_defaults.get("skip_done", True)),
                    continue_on_error=bool(enrich_defaults.get("continue_on_error", True)),
                )
                dataset_summary["steps"].append(step)

        if args.phase in ("sample", "all") and sample_target_count > 0:
            if enrich_enabled and (artifacts["enriched"].exists() or args.phase == "all"):
                sample_input = artifacts["enriched"]
            else:
                sample_input = source_path

            step = {
                "name": "sample",
                "input": str(sample_input),
                "output": str(artifacts["perf"]),
                "target_count": sample_target_count,
            }
            if args.dry_run:
                if sample_input.exists():
                    rows = read_jsonl(sample_input)
                    eligible_rows = rows
                    if sample_defaults.get("require_done", True):
                        eligible_rows = [row for row in eligible_rows if (row.get("candidate_enrichment_status") or "") == "done"]
                    if sample_defaults.get("exclude_trace_failed", True):
                        eligible_rows = [row for row in eligible_rows if row.get("trace_failed") is not True]
                    step["eligible_rows"] = len(eligible_rows)
                    step["planned_rows"] = min(len(eligible_rows), sample_target_count)
                elif args.phase == "all":
                    step["depends_on_enrich"] = True
                dataset_summary["steps"].append(step)
            else:
                step["result"] = run_sample_job(
                    input_path=sample_input,
                    output_path=artifacts["perf"],
                    target_count=sample_target_count,
                    seed=int(sample_defaults.get("seed", 0)),
                    require_done=bool(sample_defaults.get("require_done", True)),
                    exclude_trace_failed=bool(sample_defaults.get("exclude_trace_failed", True)),
                )
                dataset_summary["steps"].append(step)

        if not args.dry_run:
            write_json_file(artifacts["report"], dataset_summary)
        campaign_summary["datasets"].append(dataset_summary)

    if not args.dry_run:
        write_json_file(output_root / "manifests" / "campaign_summary.json", campaign_summary)
        resolved_plan = {
            "config_path": args.config,
            "campaign_plan_path": args.plan,
            "effective_output_root": str(output_root),
            "effective_cache_dir": str(cache_dir),
            "effective_trace_output_dir": path_or_none(trace_output_dir),
            "plan": plan,
        }
        write_json_file(output_root / "manifests" / "campaign_plan_resolved.json", resolved_plan)

    print_json_or_text(campaign_summary, args.json)
    return 0


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def command_analyze_campaign(args: argparse.Namespace) -> int:
    campaign_root = Path(args.campaign_root).resolve()
    perf_dir = campaign_root / "perf"
    if not perf_dir.exists():
        raise SystemExit(f"perf directory not found: {perf_dir}")

    manifests_dir = campaign_root / "manifests"
    reports_dir = campaign_root / "reports"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    dataset_summaries: List[Dict[str, Any]] = []
    replay_ready_manifest: List[Dict[str, Any]] = []
    stats_only_manifest: List[Dict[str, Any]] = []
    replay_hotset_manifest: List[Dict[str, Any]] = []

    for perf_path in sorted(perf_dir.glob("*.jsonl")):
        rows = read_jsonl(perf_path)
        dataset = perf_path.stem
        summary = campaign_perf_summary(dataset, rows)
        dataset_summaries.append(summary)

        replay_ready_rows = [row for row in rows if row.get("trace_path")]
        stats_only_rows = [row for row in rows if not row.get("trace_path")]
        hotset_rows = greedy_sample(replay_ready_rows, args.hotset_per_dataset, args.seed) if replay_ready_rows else []

        replay_ready_manifest.extend(
            {
                "dataset": dataset,
                "tx_hash": row.get("tx_hash"),
                "trace_path": row.get("trace_path"),
                "selector": row.get("selector"),
                "template_key": template_key(row),
                "gas_used": numeric_gas(row),
            }
            for row in replay_ready_rows
        )
        stats_only_manifest.extend(
            {
                "dataset": dataset,
                "tx_hash": row.get("tx_hash"),
                "selector": row.get("selector"),
                "template_key": template_key(row),
                "gas_used": numeric_gas(row),
                "reason": "missing_trace_path",
            }
            for row in stats_only_rows
        )
        replay_hotset_manifest.extend(
            {
                "dataset": dataset,
                "tx_hash": row.get("tx_hash"),
                "trace_path": row.get("trace_path"),
                "selector": row.get("selector"),
                "template_key": template_key(row),
                "gas_used": numeric_gas(row),
            }
            for row in hotset_rows
        )

    write_json_file(manifests_dir / "replay_ready_manifest.json", replay_ready_manifest)
    write_json_file(manifests_dir / "stats_only_manifest.json", stats_only_manifest)
    write_json_file(manifests_dir / "replay_hotset_manifest.json", replay_hotset_manifest)

    summary_rows = []
    for item in dataset_summaries:
        summary_rows.append(
            [
                item["dataset"],
                item["row_count"],
                item["replay_ready_rows"],
                item["unique_template_keys"],
                item["gas_p50"],
                item["gas_p90"],
                item["calldata_p50"],
                item["calldata_p90"],
            ]
        )

    markdown_lines = [
        "# Campaign Analysis",
        "",
        f"- Campaign root: `{campaign_root}`",
        f"- Generated at: `{now_iso()}`",
        f"- Replay-ready rows: `{len(replay_ready_manifest)}`",
        f"- Stats-only rows: `{len(stats_only_manifest)}`",
        f"- Replay hotset rows: `{len(replay_hotset_manifest)}`",
        "",
        "## Dataset Summary",
        "",
        markdown_table(
            ["Dataset", "Rows", "ReplayReady", "Templates", "GasP50", "GasP90", "CalldataP50", "CalldataP90"],
            summary_rows,
        ),
        "",
    ]

    for item in dataset_summaries:
        markdown_lines.extend(
            [
                f"## {item['dataset']}",
                "",
                f"- Rows: `{item['row_count']}`",
                f"- Replay-ready: `{item['replay_ready_rows']}`",
                f"- Unique template keys: `{item['unique_template_keys']}`",
                f"- Status counts: `{json.dumps(item['status_counts'], ensure_ascii=True, sort_keys=True)}`",
                f"- Top selectors: `{json.dumps(item['top_selectors'], ensure_ascii=True)}`",
                f"- Top templates: `{json.dumps(item['top_templates'], ensure_ascii=True)}`",
                "",
            ]
        )

    if stats_only_manifest:
        blocked = sorted({item["dataset"] for item in stats_only_manifest})
        markdown_lines.extend(
            [
                "## Replay Notes",
                "",
                f"- Stats-only datasets: `{', '.join(blocked)}`",
                "- These rows are usable for workload statistics, but not for replay until trace/state material is added.",
                "",
            ]
        )
    else:
        markdown_lines.extend(
            [
                "## Replay Notes",
                "",
                "- All perf rows are replay-ready.",
                "",
            ]
        )

    report_path = reports_dir / "campaign_analysis.md"
    report_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    payload = {
        "campaign_root": str(campaign_root),
        "report_path": str(report_path),
        "replay_ready_manifest": str(manifests_dir / "replay_ready_manifest.json"),
        "stats_only_manifest": str(manifests_dir / "stats_only_manifest.json"),
        "replay_hotset_manifest": str(manifests_dir / "replay_hotset_manifest.json"),
        "datasets": dataset_summaries,
    }
    print_json_or_text(payload, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect and sample transaction corpora for DTVM analysis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report-existing", help="Summarize a local JSONL corpus directory")
    report_parser.add_argument("--input-dir", default="tests/fulltrace_transactions")
    report_parser.add_argument("--json", action="store_true")
    report_parser.set_defaults(func=command_report_existing)

    collect_parser = subparsers.add_parser("collect", help="Collect candidate transactions from Etherscan")
    collect_parser.add_argument("--config")
    collect_parser.add_argument("--dataset", required=True)
    collect_parser.add_argument("--from-block", type=int, required=True)
    collect_parser.add_argument("--to-block", type=int, required=True)
    collect_parser.add_argument("--output", required=True)
    collect_parser.add_argument("--cache-dir", default=".cache/tx_corpus")
    collect_parser.add_argument("--chunk-size", type=int, default=5000)
    collect_parser.add_argument("--page-size", type=int, default=1000)
    collect_parser.add_argument("--max-transactions", type=int, default=200)
    collect_parser.add_argument("--max-etherscan-calls", type=int, default=100)
    collect_parser.add_argument("--sleep-seconds", type=float, default=0.2)
    collect_parser.add_argument("--timeout-seconds", type=float, default=30.0)
    collect_parser.add_argument("--txlist-sort", choices=("asc", "desc"), default="asc")
    collect_parser.add_argument("--allow-missing-api-key", action="store_true")
    collect_parser.add_argument("--json", action="store_true")
    collect_parser.set_defaults(func=command_collect)

    enrich_parser = subparsers.add_parser("enrich", help="Enrich candidate rows via JSON-RPC")
    enrich_parser.add_argument("--input", required=True)
    enrich_parser.add_argument("--output", required=True)
    enrich_parser.add_argument("--rpc-url")
    enrich_parser.add_argument("--rpc-url-env", default="ETH_RPC_URL")
    enrich_parser.add_argument("--cache-dir", default=".cache/tx_corpus")
    enrich_parser.add_argument("--sleep-seconds", type=float, default=0.0)
    enrich_parser.add_argument("--timeout-seconds", type=float, default=30.0)
    enrich_parser.add_argument("--max-transactions", type=int, default=1000000)
    enrich_parser.add_argument("--max-rpc-calls", type=int)
    enrich_parser.add_argument("--max-trace-calls", type=int, default=0)
    enrich_parser.add_argument("--code-block-tag", choices=("latest", "tx"), default="latest")
    enrich_parser.add_argument("--trace-method", default="none")
    enrich_parser.add_argument("--trace-output-dir")
    enrich_parser.add_argument("--skip-done", action="store_true")
    enrich_parser.add_argument("--continue-on-error", action="store_true")
    enrich_parser.add_argument("--json", action="store_true")
    enrich_parser.set_defaults(func=command_enrich)

    sample_parser = subparsers.add_parser("sample", help="Build a compact stratified performance subset")
    sample_parser.add_argument("--input", required=True)
    sample_parser.add_argument("--output", required=True)
    sample_parser.add_argument("--target-count", type=int, required=True)
    sample_parser.add_argument("--seed", type=int, default=0)
    sample_parser.add_argument("--require-done", action="store_true")
    sample_parser.add_argument("--exclude-trace-failed", action="store_true")
    sample_parser.add_argument("--json", action="store_true")
    sample_parser.set_defaults(func=command_sample)

    budget_parser = subparsers.add_parser("estimate-budget", help="Estimate free-RPC usage for an input JSONL")
    budget_parser.add_argument("--input", required=True)
    budget_parser.add_argument("--trace-transactions", type=int, default=0)
    budget_parser.add_argument("--include-block-calls", action="store_true")
    budget_parser.add_argument("--code-block-tag", choices=("latest", "tx"), default="latest")
    budget_parser.add_argument("--json", action="store_true")
    budget_parser.set_defaults(func=command_estimate_budget)

    campaign_parser = subparsers.add_parser("campaign", help="Run the fixed five-dataset collection/enrich/sample driver")
    campaign_parser.add_argument("--config")
    campaign_parser.add_argument("--plan")
    campaign_parser.add_argument("--output-root")
    campaign_parser.add_argument("--phase", choices=("collect", "enrich", "sample", "all"), default="all")
    campaign_parser.add_argument("--datasets", help="Comma-separated dataset subset")
    campaign_parser.add_argument("--rpc-url")
    campaign_parser.add_argument("--rpc-url-env", default="ETH_RPC_URL")
    campaign_parser.add_argument("--dry-run", action="store_true")
    campaign_parser.add_argument("--json", action="store_true")
    campaign_parser.set_defaults(func=command_campaign)

    analyze_parser = subparsers.add_parser("analyze-campaign", help="Summarize campaign perf outputs and build replay manifests")
    analyze_parser.add_argument("--campaign-root", required=True)
    analyze_parser.add_argument("--hotset-per-dataset", type=int, default=10)
    analyze_parser.add_argument("--seed", type=int, default=0)
    analyze_parser.add_argument("--json", action="store_true")
    analyze_parser.set_defaults(func=command_analyze_campaign)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
