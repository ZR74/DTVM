import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "tx_replay_perf_profile.py"

SPEC = importlib.util.spec_from_file_location("tx_replay_perf_profile", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_build_profile_command_rewrites_binary_and_benchmark_flags() -> None:
    command = [
        "./build/dtvm",
        "-m",
        "interpreter",
        "--format",
        "evm",
        "file.hex",
        "--enable-statistics",
        "--num-extra-executions",
        "3",
    ]
    updated = MODULE.build_profile_command(
        command, dtvm_path="./build_perf/dtvm", mode="multipass", extra_executions=5000
    )
    assert updated == [
        "./build_perf/dtvm",
        "-m",
        "multipass",
        "--format",
        "evm",
        "file.hex",
        "--benchmark",
        "--num-extra-compilations",
        "0",
        "--num-extra-executions",
        "5000",
    ]


def test_parse_perf_script_extracts_top_frame_categories() -> None:
    text = """
dtvm  1234 1.0:   100 cycles:P:
\t7fff0000 EVMBB0_MAIN_ENTRY_1+0x1 (/tmp/perf-1234.map)
\t55550000 COMPILER::evmGetSLoad(zen::runtime::EVMInstance*, intx::uint<256u> const&)+0x27 (/root/DTVM_zr/DTVM/build_perf/dtvm)

dtvm  1234 1.1:   100 cycles:P:
\t55550000 COMPILER::evmGetSLoad(zen::runtime::EVMInstance*, intx::uint<256u> const&)+0x27 (/root/DTVM_zr/DTVM/build_perf/dtvm)
\t7fff0000 EVMBB0_MAIN_ENTRY_1+0x1 (/tmp/perf-1234.map)

dtvm  1234 1.2:   100 cycles:P:
\t55550010 COMPILER::evmGetKeccak256(zen::runtime::EVMInstance*, unsigned long, unsigned long)+0x164 (/root/DTVM_zr/DTVM/build_perf/dtvm)

dtvm  1234 1.3:   100 cycles:P:
\t77770000 COMPILER::CgDeadCgInstructionElim::isDead(COMPILER::CgInstruction const*) const+0x1 (/root/DTVM_zr/DTVM/build_perf/dtvm)

dtvm  1234 1.4:   100 cycles:P:
\t88880000 [unknown] ([kernel.kallsyms])
"""
    parsed = MODULE.parse_perf_script(text)
    assert parsed["top_frame_samples"] == 5
    assert parsed["category_counts"] == {
        "compiler": 1,
        "evm_bb": 1,
        "evm_host": 1,
        "kernel": 1,
        "keccak": 1,
    }
    assert parsed["top_evm_bbs"] == {"EVMBB0_MAIN_ENTRY_1": 1}
    assert parsed["top_host_symbols"] == {"evmGetSLoad": 1}
    assert parsed["top_keccak_symbols"] == {"evmGetKeccak256": 1}


def test_aggregate_rows_builds_dataset_summary() -> None:
    rows = [
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x1",
            "parsed": {
                "top_frame_samples": 4,
                "category_counts": {"evm_bb": 1, "evm_host": 2, "compiler": 1},
                "top_symbols": {"EVMBB0_MAIN_ENTRY_1": 1, "COMPILER::evmGetSLoad(...)": 2},
                "top_dsos": {"/tmp/perf-1.map": 1, "/root/DTVM_zr/DTVM/build_perf/dtvm": 3},
                "top_evm_bbs": {"EVMBB0_MAIN_ENTRY_1": 1},
                "top_host_symbols": {"evmGetSLoad": 2},
                "top_keccak_symbols": {},
            },
        },
        {
            "dataset": "erc20_transfer",
            "tx_hash": "0x2",
            "parsed": {
                "top_frame_samples": 2,
                "category_counts": {"compiler": 2},
                "top_symbols": {"COMPILER::CgDeadCgInstructionElim::isDead(...)": 2},
                "top_dsos": {"/root/DTVM_zr/DTVM/build_perf/dtvm": 2},
                "top_evm_bbs": {},
                "top_host_symbols": {},
                "top_keccak_symbols": {},
            },
        },
    ]
    summary = MODULE.aggregate_rows(rows)
    assert summary["runs"] == 2
    assert summary["top_frame_samples"] == 6
    assert summary["category_counts"] == {"compiler": 3, "evm_bb": 1, "evm_host": 2}
    assert summary["datasets"]["erc20_transfer"]["runs"] == 2
    assert summary["datasets"]["erc20_transfer"]["top_host_symbols"] == {"evmGetSLoad": 2}
    assert summary["zero_execution_runs"] == [{"dataset": "erc20_transfer", "tx_hash": "0x2"}]


def test_remove_repo_jit_artifacts_cleans_generated_files(tmp_path: Path) -> None:
    original_root = MODULE.REPO_ROOT
    MODULE.REPO_ROOT = tmp_path
    try:
        dump_path = tmp_path / "jit-123.dump"
        so_path = tmp_path / "jitted-123-0.so"
        keep_path = tmp_path / "keep.txt"
        dump_path.write_text("", encoding="utf-8")
        so_path.write_text("", encoding="utf-8")
        keep_path.write_text("keep", encoding="utf-8")

        MODULE.remove_repo_jit_artifacts()

        assert not dump_path.exists()
        assert not so_path.exists()
        assert keep_path.exists()
    finally:
        MODULE.REPO_ROOT = original_root
