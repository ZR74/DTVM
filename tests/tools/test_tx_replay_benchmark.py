import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "tx_replay_benchmark.py"

SPEC = importlib.util.spec_from_file_location("tx_replay_benchmark", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_prepared(path: Path, dataset: str, tx_hash: str, command: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"dataset": dataset, "tx_hash": tx_hash, "command": command}
    path.write_text(json.dumps(payload), encoding="utf-8")


def run_tool(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_parse_statistics_output_extracts_phases() -> None:
    text = """
[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] Load:\t\t\t1 times, avg 0.100ms, total 0.100ms, 1.00%
[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] JIT Compilation:\t\t1 times, avg 1.500ms, total 1.500ms, 90.00%
[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] Instantiation:\t\t1 times, avg 0.150ms, total 0.150ms, 9.00%
[2026-05-18 16:03:18.272] [info] [statistics.cpp:132] Total:\t\t1.750ms
"""
    payload = MODULE.parse_statistics_output(text)
    assert payload["total_ms"] == 1.75
    assert payload["phases"]["load"]["total_ms"] == 0.1
    assert payload["phases"]["jit_compilation"]["avg_ms"] == 1.5
    assert payload["phases"]["instantiation"]["pct"] == 9.0


def test_override_command_mode_rewrites_existing_flag() -> None:
    command = ["./build/dtvm", "-m", "multipass", "--format", "evm", "file.hex"]
    updated = MODULE.override_command_mode(command, "interpreter")
    assert updated == ["./build/dtvm", "-m", "interpreter", "--format", "evm", "file.hex"]


def test_tool_runs_fake_prepared_tree_and_writes_summary(tmp_path: Path) -> None:
    helper = tmp_path / "fake_replay.py"
    helper.write_text(
        "\n".join(
            [
                "import sys",
                "import time",
                "exit_code = int(sys.argv[1])",
                "jit_ms = sys.argv[2]",
                "inst_ms = sys.argv[3]",
                "time.sleep(0.01)",
                "print('[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] Load:\\t\\t\\t1 times, avg 0.100ms, total 0.100ms, 1.00%')",
                "print(f'[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] JIT Compilation:\\t\\t1 times, avg {jit_ms}ms, total {jit_ms}ms, 90.00%')",
                "print(f'[2026-05-18 16:03:18.272] [info] [statistics.cpp:125] Instantiation:\\t\\t1 times, avg {inst_ms}ms, total {inst_ms}ms, 9.00%')",
                "print('[2026-05-18 16:03:18.272] [info] [statistics.cpp:132] Total:\\t\\t1.750ms')",
                "raise SystemExit(exit_code)",
            ]
        ),
        encoding="utf-8",
    )

    prepared_root = tmp_path / "prepared"
    write_prepared(
        prepared_root / "alpha" / "0x1" / "prepared.json",
        "alpha",
        "0x1",
        [sys.executable, str(helper), "0", "1.500", "0.150"],
    )
    write_prepared(
        prepared_root / "beta" / "0x2" / "prepared.json",
        "beta",
        "0x2",
        [sys.executable, str(helper), "5", "2.500", "0.250"],
    )

    output_dir = tmp_path / "out"
    payload = run_tool(
        "--prepared-root",
        str(prepared_root),
        "--output-dir",
        str(output_dir),
    )

    assert payload["summary"]["runs"] == 2
    assert payload["summary"]["exit_codes"] == {"0": 1, "5": 1}
    assert payload["summary"]["datasets"]["alpha"]["jit_compilation_ms"]["mean"] == 1.5
    assert payload["summary"]["datasets"]["beta"]["instantiation_ms"]["mean"] == 0.25
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "runs.jsonl").exists()
    assert (output_dir / "summary.md").exists()
