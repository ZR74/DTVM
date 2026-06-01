import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "tx_corpus.py"


def run_tool(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def test_report_existing_counts_attention(tmp_path: Path) -> None:
    rows = [
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x1",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "trace_path": "data/a.json.gz",
            "selector": "0xa9059cbb",
            "top_level_codehash": "0xabc",
            "gas_used": 50_000,
            "calldata_size": 68,
            "matched_emitters": ["0xtoken"],
            "top_level_to": "0xtoken",
        },
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x2",
            "candidate_enrichment_status": "pending",
            "trace_failed": True,
            "trace_path": "",
            "selector": "",
            "top_level_codehash": "",
            "gas_used": 200_000,
            "calldata_size": 132,
            "matched_emitters": ["0xtoken"],
            "top_level_to": "0xrouter",
        },
    ]
    write_jsonl(tmp_path / "erc20_transfer_transactions.jsonl", rows)

    payload = run_tool("report-existing", "--input-dir", str(tmp_path), "--json")
    assert payload["datasets"][0]["row_count"] == 2
    assert payload["datasets"][0]["pending_enrichment"] == 1
    assert payload["datasets"][0]["trace_failed_true"] == 1
    assert payload["datasets"][0]["missing_selector"] == 1
    assert payload["datasets"][0]["missing_codehash"] == 1
    assert payload["datasets"][0]["missing_trace_path"] == 1


def test_estimate_budget_uses_unique_address_block_pairs(tmp_path: Path) -> None:
    rows = [
        {"tx_hash": "0x1", "sample_block_number": 100, "sample_emitter_address": "0xaaa"},
        {"tx_hash": "0x2", "sample_block_number": 100, "sample_emitter_address": "0xaaa"},
        {"tx_hash": "0x3", "sample_block_number": 101, "sample_emitter_address": "0xbbb"},
    ]
    input_path = tmp_path / "candidates.jsonl"
    write_jsonl(input_path, rows)

    payload = run_tool(
        "estimate-budget",
        "--input",
        str(input_path),
        "--trace-transactions",
        "5",
        "--include-block-calls",
        "--json",
    )
    assert payload["transactions"] == 3
    assert payload["code_queries"] == 2
    assert payload["block_queries"] == 2
    assert payload["ordinary_rpc_calls"] == 10
    assert payload["trace_rpc_calls"] == 5
    assert payload["total_rpc_calls"] == 15


def test_sample_preserves_template_coverage(tmp_path: Path) -> None:
    rows = [
        {
            "dataset": "erc4337_bundle",
            "tx_hash": "0x1",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_codehash": "0xaaa",
            "top_level_template_hash": "0xaaa",
            "gas_used": 100_000,
            "calldata_size": 200,
        },
        {
            "dataset": "erc4337_bundle",
            "tx_hash": "0x2",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_codehash": "0xaaa",
            "top_level_template_hash": "0xaaa",
            "gas_used": 150_000,
            "calldata_size": 300,
        },
        {
            "dataset": "erc4337_bundle",
            "tx_hash": "0x3",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_codehash": "0xbbb",
            "top_level_template_hash": "0xbbb",
            "gas_used": 210_000,
            "calldata_size": 400,
        },
        {
            "dataset": "erc4337_bundle",
            "tx_hash": "0x4",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_codehash": "0xccc",
            "top_level_template_hash": "0xccc",
            "gas_used": 310_000,
            "calldata_size": 500,
        },
    ]
    input_path = tmp_path / "enriched.jsonl"
    output_path = tmp_path / "perf.jsonl"
    write_jsonl(input_path, rows)

    payload = run_tool(
        "sample",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--target-count",
        "3",
        "--require-done",
        "--exclude-trace-failed",
        "--json",
    )
    assert payload["sampled_rows"] == 3
    assert payload["unique_template_keys"] == 3

    sampled = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert {row["top_level_template_hash"] for row in sampled} == {"0xaaa", "0xbbb", "0xccc"}


def test_campaign_dry_run_reports_pre_enrich_budget(tmp_path: Path) -> None:
    input_rows = [
        {"dataset": "erc4337_bundle", "tx_hash": "0x1", "sample_block_number": 100, "sample_emitter_address": "0xaaa"},
        {"dataset": "erc4337_bundle", "tx_hash": "0x2", "sample_block_number": 101, "sample_emitter_address": "0xbbb"},
        {"dataset": "erc4337_bundle", "tx_hash": "0x3", "sample_block_number": 102, "sample_emitter_address": "0xccc"},
    ]
    input_path = tmp_path / "erc4337_bundle_transactions.jsonl"
    write_jsonl(input_path, input_rows)

    plan = {
        "output_root": str(tmp_path / "out"),
        "datasets": {
            "erc20_transfer": {"enabled": False},
            "uniswap_v3_swap": {"enabled": False},
            "erc4337_bundle": {
                "enabled": True,
                "input_path": str(input_path),
                "pre_enrich_sample_count": 2,
                "sample_target_count": 1,
            },
            "cow_settlement": {"enabled": False},
            "uniswapx_reactor": {"enabled": False},
        },
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    payload = run_tool("campaign", "--plan", str(plan_path), "--phase", "enrich", "--dry-run", "--json")
    dataset = payload["datasets"][0]
    assert dataset["dataset"] == "erc4337_bundle"
    assert dataset["steps"][0]["name"] == "pre_enrich_sample"
    assert dataset["steps"][0]["planned_rows"] == 2
    assert dataset["steps"][1]["name"] == "enrich"
    assert dataset["steps"][1]["estimated_budget"]["transactions"] == 2


def test_campaign_sample_phase_writes_perf_subset(tmp_path: Path) -> None:
    input_rows = [
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x1",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_template_hash": "0xaaa",
        },
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x2",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_template_hash": "0xbbb",
        },
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x3",
            "candidate_enrichment_status": "done",
            "trace_failed": False,
            "top_level_template_hash": "0xccc",
        },
    ]
    input_path = tmp_path / "erc20_transfer_transactions.jsonl"
    write_jsonl(input_path, input_rows)

    plan = {
        "output_root": str(tmp_path / "out"),
        "datasets": {
            "erc20_transfer": {
                "enabled": True,
                "input_path": str(input_path),
                "sample_target_count": 2,
            },
            "uniswap_v3_swap": {"enabled": False},
            "erc4337_bundle": {"enabled": False},
            "cow_settlement": {"enabled": False},
            "uniswapx_reactor": {"enabled": False},
        },
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    payload = run_tool("campaign", "--plan", str(plan_path), "--phase", "sample", "--json")
    dataset = payload["datasets"][0]
    perf_path = Path(dataset["perf_path"])
    assert perf_path.exists()
    sampled = [json.loads(line) for line in perf_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(sampled) == 2
    assert (tmp_path / "out" / "manifests" / "campaign_summary.json").exists()


def test_analyze_campaign_writes_manifests_and_report(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    perf_dir = campaign_root / "perf"
    perf_dir.mkdir(parents=True)
    rows = [
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x1",
            "trace_path": "data/trace1.json.gz",
            "selector": "0xa9059cbb",
            "top_level_template_hash": "0xaaa",
            "gas_used": 100_000,
            "status": 1,
            "calldata_size": 68,
        },
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x2",
            "trace_path": "",
            "selector": "0xa9059cbb",
            "top_level_template_hash": "0xbbb",
            "gas_used": 200_000,
            "status": 1,
            "calldata_size": 68,
        },
    ]
    write_jsonl(perf_dir / "erc20_transfer.jsonl", rows)

    payload = run_tool(
        "analyze-campaign",
        "--campaign-root",
        str(campaign_root),
        "--hotset-per-dataset",
        "1",
        "--json",
    )
    assert payload["datasets"][0]["dataset"] == "erc20_transfer"
    assert payload["datasets"][0]["replay_ready_rows"] == 1
    assert Path(payload["report_path"]).exists()

    replay_ready = json.loads(Path(payload["replay_ready_manifest"]).read_text(encoding="utf-8"))
    stats_only = json.loads(Path(payload["stats_only_manifest"]).read_text(encoding="utf-8"))
    replay_hotset = json.loads(Path(payload["replay_hotset_manifest"]).read_text(encoding="utf-8"))

    assert len(replay_ready) == 1
    assert len(stats_only) == 1
    assert len(replay_hotset) == 1
