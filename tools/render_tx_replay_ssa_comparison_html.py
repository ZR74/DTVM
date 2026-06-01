#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean_or_none(values: Iterable[float | None]) -> float | None:
    data = [float(v) for v in values if v is not None]
    if not data:
        return None
    return float(fmean(data))


def pct_delta(off: float | None, on: float | None) -> float | None:
    if off in (None, 0) or on is None:
        return None
    return ((on - off) / off) * 100.0


def better_delta(off: float | None, on: float | None) -> float | None:
    raw = pct_delta(off, on)
    if raw is None:
        return None
    return -raw


def pp_delta(off: float | None, on: float | None) -> float | None:
    if off is None or on is None:
        return None
    return on - off


def fmt_ms(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f} ms"


def fmt_us(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f} us"


def fmt_pct(value: float | None, digits: int = 2, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    if signed:
        return f"{value:+.{digits}f}%"
    return f"{value:.{digits}f}%"


def fmt_pp(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f} pp"


def fmt_num(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,}"


def status_class(delta: float | None, lower_is_better: bool = True) -> str:
    if delta is None:
        return "flat"
    if lower_is_better:
        if delta <= -2.0:
            return "good"
        if delta >= 2.0:
            return "bad"
        return "flat"
    if delta >= 2.0:
        return "good"
    if delta <= -2.0:
        return "bad"
    return "flat"


def better_status(improvement: float | None) -> str:
    if improvement is None:
        return "flat"
    if improvement >= 2.0:
        return "good"
    if improvement <= -2.0:
        return "bad"
    return "flat"


def bar_width(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / max_value) * 100.0))


def key_for_row(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["dataset"]), str(row["tx_hash"]).lower()


def summarize_exit_codes(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row.get(field))] += 1
    return dict(sorted(counts.items()))


def compare_return_codes(
    off_rows: list[dict[str, Any]],
    on_rows: list[dict[str, Any]],
    field: str,
) -> list[dict[str, Any]]:
    off_map = {key_for_row(row): row for row in off_rows}
    on_map = {key_for_row(row): row for row in on_rows}
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(off_map) & set(on_map)):
        off_code = off_map[key].get(field)
        on_code = on_map[key].get(field)
        if off_code != on_code:
            mismatches.append(
                {
                    "dataset": key[0],
                    "tx_hash": key[1],
                    "off": off_code,
                    "on": on_code,
                }
            )
    return mismatches


def load_benchmark_bundle(root: Path) -> dict[str, Any]:
    summary = load_json(root / "summary.json")
    rows = load_jsonl(root / "runs.jsonl")
    verifier_rows = []
    for row in rows:
        stderr_tail = str(row.get("stderr_tail") or "")
        if "Verifying Error" in stderr_tail:
            verifier_rows.append(
                {
                    "dataset": str(row["dataset"]),
                    "tx_hash": str(row["tx_hash"]).lower(),
                }
            )
    return {
        "root": root,
        "summary": summary["summary"],
        "rows": rows,
        "verifier_rows": verifier_rows,
    }


def load_perf_bundle(root: Path) -> dict[str, Any]:
    summary = load_json(root / "summary.json")
    rows = load_jsonl(root / "runs.jsonl")
    verifier_rows = []
    for stderr_path in sorted(root.glob("*/*/dtvm.stderr.log")):
        text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if "Verifying Error" not in text:
            continue
        verifier_rows.append(
            {
                "dataset": stderr_path.parts[-3],
                "tx_hash": stderr_path.parts[-2].lower(),
            }
        )
    return {
        "root": root,
        "summary": summary["summary"],
        "rows": rows,
        "verifier_rows": verifier_rows,
    }


def benchmark_dataset_metrics(bundle: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    datasets = bundle["summary"]["datasets"]
    out: dict[str, dict[str, float | None]] = {}
    for name, payload in datasets.items():
        out[name] = {
            "wall_mean_ms": payload["wall_time_ms"]["mean"],
            "wall_p95_ms": payload["wall_time_ms"]["p95"],
            "jit_mean_ms": payload["jit_compilation_ms"]["mean"],
            "stat_mean_ms": payload["statistics_total_ms"]["mean"],
        }
    return out


def benchmark_overall_metrics(bundle: dict[str, Any]) -> dict[str, float | None]:
    rows = bundle["rows"]
    jit_values = []
    stat_values = []
    for row in rows:
        stats = row.get("statistics") or {}
        phases = stats.get("phases") or {}
        jit = ((phases.get("jit_compilation") or {}).get("total_ms"))
        if jit is not None:
            jit_values.append(float(jit))
        total_ms = stats.get("total_ms")
        if total_ms is not None:
            stat_values.append(float(total_ms))
    return {
        "wall_mean_ms": bundle["summary"]["wall_time_ms"]["mean"],
        "wall_p95_ms": bundle["summary"]["wall_time_ms"]["p95"],
        "jit_mean_ms": mean_or_none(jit_values),
        "stat_mean_ms": mean_or_none(stat_values),
    }


def perf_dataset_metrics(bundle: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in bundle["rows"]:
        by_dataset[str(row["dataset"])].append(row)
    out: dict[str, dict[str, float | None]] = {}
    for name, rows in sorted(by_dataset.items()):
        extra_exec = rows[0].get("extra_executions") or 0
        us_per_exec = [
            (float(row["profile_window_ms"]) * 1000.0) / extra_exec
            for row in rows
            if extra_exec
        ]
        out[name] = {
            "profile_mean_ms": mean_or_none(float(row["profile_window_ms"]) for row in rows),
            "total_wall_mean_ms": mean_or_none(float(row["total_wall_ms"]) for row in rows),
            "us_per_exec": mean_or_none(us_per_exec),
            "execution_sample_pct": mean_or_none(
                (
                    float(row["execution_sample_pct"]) * 100.0
                    if row.get("execution_sample_pct") is not None
                    else None
                )
                for row in rows
            ),
        }
    return out


def build_category_table(
    off_summary: dict[str, Any],
    on_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    keys = sorted(
        set(off_summary["category_pct"].keys()) | set(on_summary["category_pct"].keys())
    )
    rows = []
    for key in keys:
        off_v = float(off_summary["category_pct"].get(key, 0.0))
        on_v = float(on_summary["category_pct"].get(key, 0.0))
        rows.append(
            {
                "name": key,
                "off": off_v,
                "on": on_v,
                "delta_pp": on_v - off_v,
            }
        )
    rows.sort(key=lambda row: abs(row["delta_pp"]), reverse=True)
    return rows


def top_delta_rows(
    off_map: dict[str, int],
    off_total: int,
    on_map: dict[str, int],
    on_total: int,
    limit: int,
) -> list[dict[str, Any]]:
    keys = set(off_map) | set(on_map)
    rows = []
    for key in keys:
        off_count = int(off_map.get(key, 0))
        on_count = int(on_map.get(key, 0))
        off_share = (off_count / off_total * 100.0) if off_total else 0.0
        on_share = (on_count / on_total * 100.0) if on_total else 0.0
        rows.append(
            {
                "name": key,
                "off_count": off_count,
                "on_count": on_count,
                "off_share": off_share,
                "on_share": on_share,
                "delta_pp": on_share - off_share,
            }
        )
    rows.sort(
        key=lambda row: (
            abs(row["delta_pp"]),
            row["on_count"] + row["off_count"],
        ),
        reverse=True,
    )
    return rows[:limit]


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def dominant_category(summary: dict[str, Any]) -> tuple[str, float]:
    items = summary["category_pct"].items()
    name, value = max(items, key=lambda item: item[1])
    return str(name), float(value)


def perf_overall_metrics(bundle: dict[str, Any]) -> dict[str, float | None]:
    rows = bundle["rows"]
    if not rows:
        return {
            "profile_mean_ms": None,
            "total_wall_mean_ms": None,
            "us_per_exec": None,
            "execution_sample_pct": None,
        }
    extra_exec = rows[0].get("extra_executions") or 0
    return {
        "profile_mean_ms": mean_or_none(float(row["profile_window_ms"]) for row in rows),
        "total_wall_mean_ms": mean_or_none(float(row["total_wall_ms"]) for row in rows),
        "us_per_exec": mean_or_none(
            (float(row["profile_window_ms"]) * 1000.0) / extra_exec
            for row in rows
            if extra_exec
        ),
        "execution_sample_pct": mean_or_none(
            (
                float(row["execution_sample_pct"]) * 100.0
                if row.get("execution_sample_pct") is not None
                else None
            )
            for row in rows
        ),
    }


def render_stacked_bar(values: dict[str, float]) -> str:
    order = [
        ("evm_bb", "seg-evm"),
        ("evm_host", "seg-host"),
        ("keccak", "seg-keccak"),
        ("memory", "seg-memory"),
        ("kernel", "seg-kernel"),
        ("unknown", "seg-unknown"),
        ("other", "seg-other"),
        ("compiler", "seg-compiler"),
        ("profiling_overhead", "seg-prof"),
    ]
    parts = []
    for key, css in order:
        value = float(values.get(key, 0.0))
        if value <= 0:
            continue
        parts.append(
            f'<div class="stack-seg {css}" style="width:{value:.4f}%"><span>{html.escape(key)} {value:.2f}%</span></div>'
        )
    return "".join(parts)


def render_metric_card(label: str, value: str, sub: str, status: str = "flat") -> str:
    return (
        f'<div class="metric-card {status}">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-sub">{html.escape(sub)}</div>'
        "</div>"
    )


def render_delta_chip(value: float | None, unit: str = "%") -> str:
    if value is None:
        return '<span class="chip flat">n/a</span>'
    if unit == "%":
        text = fmt_pct(value, signed=True)
    elif unit == "pp":
        text = fmt_pp(value)
    else:
        text = f"{value:+.2f}{unit}"
    return f'<span class="chip {better_status(-value) if unit == "%" else status_class(value, lower_is_better=False)}">{html.escape(text)}</span>'


def render_rows_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    thead = "".join(f"<th>{html.escape(title)}</th>" for _, title in columns)
    body_rows = []
    for row in rows:
        tds = "".join(f"<td>{row[key]}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{tds}</tr>")
    return (
        '<table class="data-table"><thead><tr>'
        + thead
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def render_html(payload: dict[str, Any]) -> str:
    bench_off = payload["bench_off"]
    bench_on = payload["bench_on"]
    perf_off = payload["perf_off"]
    perf_on = payload["perf_on"]

    cold_improvement = better_delta(
        bench_off["overall"]["wall_mean_ms"],
        bench_on["overall"]["wall_mean_ms"],
    )
    jit_improvement = better_delta(
        bench_off["overall"]["jit_mean_ms"],
        bench_on["overall"]["jit_mean_ms"],
    )
    exec_improvement = better_delta(
        perf_off["overall"]["us_per_exec"],
        perf_on["overall"]["us_per_exec"],
    )

    dominant_off_name, dominant_off_pct = dominant_category(perf_off["summary"])
    dominant_on_name, dominant_on_pct = dominant_category(perf_on["summary"])
    benchmark_comparable = (
        not payload["benchmark_returncode_mismatches"]
        and payload["benchmark_verifier_off"] == 0
        and payload["benchmark_verifier_on"] == 0
    )
    perf_comparable = (
        not payload["perf_returncode_mismatches"]
        and payload["perf_verifier_off"] == 0
        and payload["perf_verifier_on"] == 0
    )

    if benchmark_comparable:
        hero_cold_value = fmt_pct(cold_improvement, signed=True)
        hero_cold_sub = (
            f"SSA=OFF {fmt_ms(bench_off['overall']['wall_mean_ms'])} -> "
            f"SSA=ON {fmt_ms(bench_on['overall']['wall_mean_ms'])}"
        )
        hero_cold_status = better_status(cold_improvement)
        hero_cold_jit_value = fmt_pct(jit_improvement, signed=True)
        hero_cold_jit_sub = (
            f"SSA=OFF {fmt_ms(bench_off['overall']['jit_mean_ms'])} -> "
            f"SSA=ON {fmt_ms(bench_on['overall']['jit_mean_ms'])}"
        )
        hero_cold_jit_status = better_status(jit_improvement)
    else:
        hero_cold_value = "NOT COMPARABLE"
        hero_cold_sub = (
            f"raw OFF {fmt_ms(bench_off['overall']['wall_mean_ms'])} / "
            f"raw ON {fmt_ms(bench_on['overall']['wall_mean_ms'])}; "
            f"mismatches {len(payload['benchmark_returncode_mismatches'])}"
        )
        hero_cold_status = "bad"
        hero_cold_jit_value = "NOT COMPARABLE"
        hero_cold_jit_sub = (
            f"raw OFF {fmt_ms(bench_off['overall']['jit_mean_ms'])} / "
            f"raw ON {fmt_ms(bench_on['overall']['jit_mean_ms'])}; "
            f"verifier {payload['benchmark_verifier_on']}"
        )
        hero_cold_jit_status = "bad"

    if perf_comparable:
        hero_exec_value = fmt_pct(exec_improvement, signed=True)
        hero_exec_sub = (
            f"SSA=OFF {fmt_us(perf_off['overall']['us_per_exec'])} -> "
            f"SSA=ON {fmt_us(perf_on['overall']['us_per_exec'])}"
        )
        hero_exec_status = better_status(exec_improvement)
    else:
        hero_exec_value = "NOT COMPARABLE"
        hero_exec_sub = (
            f"raw OFF {fmt_us(perf_off['overall']['us_per_exec'])} / "
            f"raw ON {fmt_us(perf_on['overall']['us_per_exec'])}; "
            f"mismatches {len(payload['perf_returncode_mismatches'])}"
        )
        hero_exec_status = "bad"

    cold_dataset_max = max(
        max(item["off_wall"], item["on_wall"]) for item in payload["cold_dataset_rows"]
    )
    exec_dataset_max = max(
        max(item["off_us"], item["on_us"]) for item in payload["exec_dataset_rows"]
    )

    category_table_rows = []
    for row in payload["category_rows"]:
        category_table_rows.append(
            {
                "name": html.escape(row["name"]),
                "off": fmt_pct(row["off"]),
                "on": fmt_pct(row["on"]),
                "delta": fmt_pp(row["delta_pp"]),
            }
        )

    host_rows = []
    for row in payload["host_delta_rows"]:
        host_rows.append(
            {
                "name": html.escape(row["name"]),
                "off": fmt_pct(row["off_share"]),
                "on": fmt_pct(row["on_share"]),
                "delta": fmt_pp(row["delta_pp"]),
            }
        )

    keccak_rows = []
    for row in payload["keccak_delta_rows"]:
        keccak_rows.append(
            {
                "name": html.escape(row["name"]),
                "off": fmt_pct(row["off_share"]),
                "on": fmt_pct(row["on_share"]),
                "delta": fmt_pp(row["delta_pp"]),
            }
        )

    bb_rows = []
    for row in payload["bb_delta_rows"]:
        bb_rows.append(
            {
                "name": html.escape(row["name"]),
                "off": fmt_pct(row["off_share"]),
                "on": fmt_pct(row["on_share"]),
                "delta": fmt_pp(row["delta_pp"]),
            }
        )

    mismatch_rows = []
    for row in payload["benchmark_returncode_mismatches"] + payload["perf_returncode_mismatches"]:
        mismatch_rows.append(
            {
                "kind": "benchmark" if row in payload["benchmark_returncode_mismatches"] else "perf",
                "dataset": html.escape(row["dataset"]),
                "tx_hash": f'<code>{html.escape(row["tx_hash"][:14])}...</code>',
                "off": html.escape(str(row["off"])),
                "on": html.escape(str(row["on"])),
            }
        )

    observations = payload["observations"]
    limitations = payload["limitations"]
    dataset_tags = "".join(
        f'<span class="tag">{html.escape(name)} x {count}</span>'
        for name, count in payload["dataset_counts"]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DTVM SSA On/Off Real Transaction Comparison</title>
    <style>
      :root {{
        --bg: #f4efe7;
        --panel: rgba(255, 255, 255, 0.88);
        --panel-strong: #fffdf9;
        --ink: #1f2937;
        --muted: #5f6b7d;
        --line: rgba(31, 41, 55, 0.12);
        --teal: #0f766e;
        --cyan: #0891b2;
        --orange: #d97706;
        --red: #c2410c;
        --olive: #5b6b2d;
        --gold: #b7791f;
        --sky: #2563eb;
        --slate: #475569;
        --shadow: 0 20px 44px rgba(29, 41, 55, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", "Source Sans 3", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(14, 116, 144, 0.10), transparent 28%),
          radial-gradient(circle at top right, rgba(217, 119, 6, 0.11), transparent 25%),
          linear-gradient(180deg, #fbf7ef 0%, #f3ede3 55%, #ede5d8 100%);
      }}
      .page {{
        width: min(1240px, calc(100vw - 36px));
        margin: 0 auto;
        padding: 34px 0 64px;
      }}
      .hero {{
        position: relative;
        overflow: hidden;
        padding: 34px 36px 32px;
        color: #fff;
        border-radius: 28px;
        box-shadow: var(--shadow);
        background:
          linear-gradient(135deg, rgba(15, 118, 110, 0.96), rgba(30, 41, 59, 0.96)),
          linear-gradient(90deg, rgba(255,255,255,0.08), rgba(255,255,255,0));
      }}
      .hero::after {{
        content: "";
        position: absolute;
        right: -70px;
        top: -88px;
        width: 260px;
        height: 260px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.20), transparent 70%);
      }}
      .eyebrow {{
        letter-spacing: 0.16em;
        font-size: 12px;
        text-transform: uppercase;
        opacity: 0.82;
      }}
      h1 {{
        margin: 10px 0 10px;
        font-family: "Space Grotesk", "Avenir Next", "IBM Plex Sans", sans-serif;
        font-size: clamp(34px, 4vw, 54px);
        line-height: 0.98;
      }}
      .hero p {{
        margin: 0;
        max-width: 900px;
        line-height: 1.68;
        color: rgba(255,255,255,0.86);
      }}
      .tag-row, .pill-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }}
      .pill-row {{
        margin-top: 18px;
      }}
      .pill {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 999px;
        font-size: 13px;
        color: #fff;
        background: rgba(255,255,255,0.11);
        border: 1px solid rgba(255,255,255,0.14);
      }}
      .metrics {{
        display: grid;
        gap: 14px;
        margin-top: 20px;
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }}
      .metric-card {{
        border-radius: 18px;
        padding: 16px 16px 15px;
        background: rgba(255,255,255,0.11);
        border: 1px solid rgba(255,255,255,0.15);
      }}
      .metric-label {{
        font-size: 13px;
        color: rgba(255,255,255,0.76);
      }}
      .metric-value {{
        margin-top: 8px;
        font-size: 31px;
        font-weight: 700;
      }}
      .metric-sub {{
        margin-top: 6px;
        font-size: 13px;
        color: rgba(255,255,255,0.75);
        line-height: 1.5;
      }}
      .good .metric-value {{ color: #c7f9d4; }}
      .bad .metric-value {{ color: #ffd0c2; }}
      .flat .metric-value {{ color: #fff7d6; }}
      .section-head {{
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: flex-end;
        margin-top: 34px;
      }}
      .section-head h2 {{
        margin: 0;
        font-family: "Space Grotesk", "Avenir Next", "IBM Plex Sans", sans-serif;
        font-size: 26px;
      }}
      .section-head p {{
        margin: 6px 0 0;
        color: var(--muted);
        line-height: 1.6;
      }}
      .tag {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        border: 1px solid rgba(31,41,55,0.08);
        background: #f5ead8;
        color: var(--ink);
        font-size: 12px;
      }}
      .grid-2, .grid-3, .grid-4 {{
        display: grid;
        gap: 16px;
        margin-top: 16px;
      }}
      .grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .grid-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
      .panel {{
        background: var(--panel);
        border: 1px solid rgba(255,255,255,0.68);
        border-radius: 22px;
        box-shadow: var(--shadow);
        padding: 22px;
        margin-top: 16px;
      }}
      .panel h3 {{
        margin: 0 0 12px;
        font-size: 18px;
      }}
      .small {{
        color: var(--muted);
        font-size: 13px;
        line-height: 1.6;
      }}
      .list {{
        margin: 0;
        padding-left: 18px;
        line-height: 1.7;
      }}
      .list li + li {{
        margin-top: 6px;
      }}
      .chip {{
        display: inline-flex;
        align-items: center;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid rgba(31,41,55,0.08);
      }}
      .chip.good {{ background: rgba(16, 185, 129, 0.12); color: #0f766e; }}
      .chip.bad {{ background: rgba(239, 68, 68, 0.10); color: #b91c1c; }}
      .chip.flat {{ background: rgba(148, 163, 184, 0.13); color: #475569; }}
      .paths code {{
        display: block;
        padding: 9px 10px;
        border-radius: 12px;
        background: #f7f3ec;
        border: 1px solid rgba(31,41,55,0.06);
        margin-top: 8px;
        word-break: break-all;
      }}
      .bars {{
        display: grid;
        gap: 14px;
      }}
      .bar-row {{
        display: grid;
        grid-template-columns: 170px 1fr 1fr 110px;
        gap: 12px;
        align-items: center;
      }}
      .bar-label {{
        font-weight: 600;
      }}
      .dual-bar {{
        position: relative;
        height: 14px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.14);
        overflow: hidden;
      }}
      .dual-bar .off {{
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        background: linear-gradient(90deg, rgba(37, 99, 235, 0.88), rgba(56, 189, 248, 0.90));
      }}
      .dual-bar .on {{
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        background: linear-gradient(90deg, rgba(217, 119, 6, 0.86), rgba(245, 158, 11, 0.94));
        opacity: 0.92;
      }}
      .bar-stat {{
        font-size: 13px;
        color: var(--muted);
      }}
      .stack {{
        display: flex;
        overflow: hidden;
        min-height: 18px;
        border-radius: 999px;
        background: rgba(148,163,184,0.12);
        border: 1px solid rgba(31,41,55,0.06);
      }}
      .stack-seg {{
        position: relative;
        min-width: 0;
      }}
      .stack-seg span {{
        position: absolute;
        left: 8px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 11px;
        color: rgba(255,255,255,0.92);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: calc(100% - 12px);
      }}
      .seg-evm {{ background: #2563eb; }}
      .seg-host {{ background: #0f766e; }}
      .seg-keccak {{ background: #b7791f; }}
      .seg-memory {{ background: #9333ea; }}
      .seg-kernel {{ background: #475569; }}
      .seg-unknown {{ background: #64748b; }}
      .seg-other {{ background: #d97706; }}
      .seg-compiler {{ background: #dc2626; }}
      .seg-prof {{ background: #0891b2; }}
      .dataset-card {{
        padding: 18px;
        border-radius: 20px;
        background: var(--panel-strong);
        border: 1px solid rgba(31,41,55,0.08);
      }}
      .dataset-card h4 {{
        margin: 0 0 8px;
        font-size: 18px;
      }}
      .dataset-card .numbers {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0 12px;
      }}
      .data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }}
      .data-table th {{
        text-align: left;
        color: var(--muted);
        font-weight: 600;
        padding: 10px 10px;
        border-bottom: 1px solid var(--line);
      }}
      .data-table td {{
        padding: 10px 10px;
        border-bottom: 1px solid rgba(31,41,55,0.08);
        vertical-align: top;
      }}
      .footnote {{
        margin-top: 14px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.6;
      }}
      @media (max-width: 1000px) {{
        .metrics, .grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .grid-3 {{ grid-template-columns: 1fr; }}
        .grid-2 {{ grid-template-columns: 1fr; }}
        .bar-row {{
          grid-template-columns: 1fr;
        }}
      }}
      @media (max-width: 720px) {{
        .page {{ width: min(100vw - 18px, 1240px); padding-top: 18px; }}
        .hero {{ padding: 24px 20px 22px; border-radius: 22px; }}
        .metrics {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <div class="eyebrow">DTVM / EVM Multipass / Real Transaction Replay</div>
        <h1>SSA On vs Off</h1>
        <p>
          基于当前分支的 40 条 Ethereum Mainnet prepared replay，对比
          <code>ZEN_ENABLE_EVM_STACK_SSA_LIFT=OFF</code> 与
          <code>ON</code> 的真实交易执行行为。报告将冷启动路径和
          execution-only 路径分开看，避免把 JIT 编译成本与 steady-state
          执行热点混在一起。
        </p>
        <div class="pill-row">
          <span class="pill">40 prepared replays</span>
          <span class="pill">4 datasets</span>
          <span class="pill">execution warmup + perf attach</span>
          <span class="pill">same code, single flag delta</span>
        </div>
        <div class="metrics">
          {render_metric_card(
              "Cold Mean Wall",
              hero_cold_value,
              hero_cold_sub,
              hero_cold_status,
          )}
          {render_metric_card(
              "Cold JIT Mean",
              hero_cold_jit_value,
              hero_cold_jit_sub,
              hero_cold_jit_status,
          )}
          {render_metric_card(
              "Execution us / Iter",
              hero_exec_value,
              hero_exec_sub,
              hero_exec_status,
          )}
          {render_metric_card(
              "Behavior Match",
              "OK" if not mismatch_rows else "DIFF",
              f"benchmark mismatches: {len(payload['benchmark_returncode_mismatches'])}, perf mismatches: {len(payload['perf_returncode_mismatches'])}",
              "good" if not mismatch_rows else "bad",
          )}
        </div>
      </section>

      <div class="section-head">
        <div>
          <h2>Scope</h2>
          <p>本次对比仅覆盖当前 40 条热集 prepared replay；当前数据集中不包含 UniswapX Reactor。</p>
        </div>
      </div>
      <section class="panel">
        <div class="tag-row">{dataset_tags}</div>
        <div class="grid-2">
          <div>
            <h3>Experiment Setup</h3>
            <ul class="list">
              <li>冷启动基线: fresh process + <code>--enable-statistics</code>，观测 wall time / JIT compilation / statistics total。</li>
              <li>execution-only 基线: 先 warmup，再附加 <code>perf</code>，每笔 replay 额外执行 {fmt_num(payload['perf_extra_executions'])} 次，观测 <code>profile_window_ms</code> 与热点分布。</li>
              <li>比较对象只改动一个开关: <code>ZEN_ENABLE_EVM_STACK_SSA_LIFT</code>。</li>
              <li>当前代码上下文已经包含此前的 internal-call journal 相关优化；本报告不再与更早版本混比。</li>
            </ul>
          </div>
          <div class="paths">
            <h3>Artifacts</h3>
            <code>{html.escape(payload['bench_off_path'])}</code>
            <code>{html.escape(payload['bench_on_path'])}</code>
            <code>{html.escape(payload['perf_off_path'])}</code>
            <code>{html.escape(payload['perf_on_path'])}</code>
          </div>
        </div>
      </section>

      <div class="section-head">
        <div>
          <h2>Correctness</h2>
          <p>先确认 SSA 开关没有改变这 40 条真实交易的行为结果，再讨论性能。</p>
        </div>
      </div>
      <section class="panel">
        <div class="grid-2">
          <div>
            <h3>Benchmark Return Codes</h3>
            <p class="small">SSA=OFF {html.escape(str(payload['benchmark_exit_codes_off']))}<br/>SSA=ON {html.escape(str(payload['benchmark_exit_codes_on']))}</p>
          </div>
          <div>
            <h3>Perf Return Codes</h3>
            <p class="small">SSA=OFF {html.escape(str(payload['perf_exit_codes_off']))}<br/>SSA=ON {html.escape(str(payload['perf_exit_codes_on']))}</p>
          </div>
        </div>
        <div class="grid-2">
          <div>
            <h3>Verifier Errors</h3>
            <p class="small">
              benchmark: OFF {fmt_num(payload['benchmark_verifier_off'])} / ON {fmt_num(payload['benchmark_verifier_on'])}<br/>
              perf: OFF {fmt_num(payload['perf_verifier_off'])} / ON {fmt_num(payload['perf_verifier_on'])}
            </p>
          </div>
          <div>
            <h3>Interpretation</h3>
            <p class="small">
              verifier error 不只是日志噪音。它意味着 SSA 路径生成了无效 IR，性能回退和 wall time 膨胀需要优先按正确性问题看待。
            </p>
          </div>
        </div>
        {"<h3>Mismatched Transactions</h3>" + render_rows_table(mismatch_rows, [('kind', 'Kind'), ('dataset', 'Dataset'), ('tx_hash', 'Tx'), ('off', 'OFF'), ('on', 'ON')]) if mismatch_rows else '<p class="small">本轮未发现 SSA on/off 导致的返回码差异，至少在这 40 条 prepared replay 上行为一致。</p>'}
      </section>

      <div class="section-head">
        <div>
          <h2>Cold Path</h2>
          <p>这一部分反映 fresh process 下的冷启动成本，核心看 SSA 是否改变 JIT 编译成本与整笔 replay wall time。</p>
        </div>
      </div>
      <section class="panel">
        <div class="grid-4">
          {render_metric_card("Mean Wall", fmt_ms(bench_on['overall']['wall_mean_ms']), f"OFF {fmt_ms(bench_off['overall']['wall_mean_ms'])} / delta {fmt_pct(cold_improvement, signed=True)}", better_status(cold_improvement) if benchmark_comparable else "bad")}
          {render_metric_card("P95 Wall", fmt_ms(bench_on['overall']['wall_p95_ms']), f"OFF {fmt_ms(bench_off['overall']['wall_p95_ms'])}", better_status(better_delta(bench_off['overall']['wall_p95_ms'], bench_on['overall']['wall_p95_ms'])) if benchmark_comparable else "bad")}
          {render_metric_card("Mean JIT", fmt_ms(bench_on['overall']['jit_mean_ms']), f"OFF {fmt_ms(bench_off['overall']['jit_mean_ms'])} / delta {fmt_pct(jit_improvement, signed=True)}", better_status(jit_improvement) if benchmark_comparable else "bad")}
          {render_metric_card("Mean Stats Total", fmt_ms(bench_on['overall']['stat_mean_ms']), f"OFF {fmt_ms(bench_off['overall']['stat_mean_ms'])}", better_status(better_delta(bench_off['overall']['stat_mean_ms'], bench_on['overall']['stat_mean_ms'])) if benchmark_comparable else "bad")}
        </div>
        <h3>Per-dataset Mean Wall Time</h3>
        <div class="bars">
          {''.join(
              f'''<div class="bar-row">
                <div class="bar-label">{html.escape(row["dataset"])}</div>
                <div class="dual-bar"><div class="off" style="width:{bar_width(row["off_wall"], cold_dataset_max):.2f}%"></div></div>
                <div class="dual-bar"><div class="on" style="width:{bar_width(row["on_wall"], cold_dataset_max):.2f}%"></div></div>
                <div class="bar-stat">{fmt_pct(row["improvement"], signed=True)}</div>
              </div>'''
              for row in payload["cold_dataset_rows"]
          )}
        </div>
        <p class="footnote">左列为 SSA=OFF，右列为 SSA=ON。右侧 delta 以 wall time 下降为正收益。</p>
      </section>

      <div class="section-head">
        <div>
          <h2>Execution Path</h2>
          <p>execution-only 路径看 steady-state，优先观察每次额外执行的平均耗时，以及热点从 EVM BB / host / keccak / memory 等类别如何迁移。</p>
        </div>
      </div>
      <section class="panel">
        <div class="grid-4">
          {render_metric_card("Mean us / Exec", fmt_us(perf_on['overall']['us_per_exec']), f"OFF {fmt_us(perf_off['overall']['us_per_exec'])} / delta {fmt_pct(exec_improvement, signed=True)}", better_status(exec_improvement))}
          {render_metric_card("Mean Profile Window", fmt_ms(perf_on['overall']['profile_mean_ms']), f"OFF {fmt_ms(perf_off['overall']['profile_mean_ms'])}", better_status(better_delta(perf_off['overall']['profile_mean_ms'], perf_on['overall']['profile_mean_ms'])))}
          {render_metric_card("Execution Sample Share", fmt_pct(perf_on['overall']['execution_sample_pct']), f"OFF {fmt_pct(perf_off['overall']['execution_sample_pct'])}", better_status(better_delta(perf_off['overall']['execution_sample_pct'], perf_on['overall']['execution_sample_pct'])))}
          {render_metric_card("Dominant Category", dominant_on_name, f"OFF {dominant_off_name} {dominant_off_pct:.2f}% / ON {dominant_on_name} {dominant_on_pct:.2f}%", "flat")}
        </div>
        <div class="grid-2">
          <div>
            <h3>SSA=OFF Category Split</h3>
            <div class="stack">{render_stacked_bar(perf_off['summary']['category_pct'])}</div>
          </div>
          <div>
            <h3>SSA=ON Category Split</h3>
            <div class="stack">{render_stacked_bar(perf_on['summary']['category_pct'])}</div>
          </div>
        </div>
        <h3>Per-dataset Execution Cost</h3>
        <div class="bars">
          {''.join(
              f'''<div class="bar-row">
                <div class="bar-label">{html.escape(row["dataset"])}</div>
                <div class="dual-bar"><div class="off" style="width:{bar_width(row["off_us"], exec_dataset_max):.2f}%"></div></div>
                <div class="dual-bar"><div class="on" style="width:{bar_width(row["on_us"], exec_dataset_max):.2f}%"></div></div>
                <div class="bar-stat">{fmt_pct(row["improvement"], signed=True)}</div>
              </div>'''
              for row in payload["exec_dataset_rows"]
          )}
        </div>
      </section>

      <div class="section-head">
        <div>
          <h2>Dataset Breakdown</h2>
          <p>按交易类型拆开后，更容易看出 SSA 更偏向帮助哪类路径。</p>
        </div>
      </div>
      <section class="grid-2">
        {''.join(
            f'''<article class="dataset-card">
              <h4>{html.escape(row["dataset"])}</h4>
              <div class="numbers">
                <span class="chip {better_status(row["cold_improvement"])}">cold {fmt_pct(row["cold_improvement"], signed=True)}</span>
                <span class="chip {better_status(row["exec_improvement"])}">exec {fmt_pct(row["exec_improvement"], signed=True)}</span>
                <span class="chip flat">evm_bb {fmt_pp(row["evm_bb_delta"])}</span>
                <span class="chip flat">keccak {fmt_pp(row["keccak_delta"])}</span>
              </div>
              <p class="small">
                cold wall: OFF {fmt_ms(row["cold_off"])} / ON {fmt_ms(row["cold_on"])}<br/>
                exec us/iter: OFF {fmt_us(row["exec_off"])} / ON {fmt_us(row["exec_on"])}<br/>
                top category: OFF {html.escape(row["dom_off_name"])} {row["dom_off_pct"]:.2f}% / ON {html.escape(row["dom_on_name"])} {row["dom_on_pct"]:.2f}%
              </p>
            </article>'''
            for row in payload["dataset_summary_rows"]
        )}
      </section>

      <div class="section-head">
        <div>
          <h2>Hotspot Deltas</h2>
          <p>这里看 SSA 是否真的把样本从 EVM 基本块、host helper 或 keccak 上搬走。</p>
        </div>
      </div>
      <section class="panel">
        <div class="grid-2">
          <div>
            <h3>Category Delta</h3>
            {render_rows_table(category_table_rows, [('name', 'Category'), ('off', 'OFF'), ('on', 'ON'), ('delta', 'Delta')])}
          </div>
          <div>
            <h3>Host Symbol Delta</h3>
            {render_rows_table(host_rows, [('name', 'Host Symbol'), ('off', 'OFF'), ('on', 'ON'), ('delta', 'Delta')])}
          </div>
        </div>
        <div class="grid-2">
          <div>
            <h3>Keccak Symbol Delta</h3>
            {render_rows_table(keccak_rows, [('name', 'Keccak Symbol'), ('off', 'OFF'), ('on', 'ON'), ('delta', 'Delta')])}
          </div>
          <div>
            <h3>EVM BB Delta</h3>
            {render_rows_table(bb_rows, [('name', 'EVM BB'), ('off', 'OFF'), ('on', 'ON'), ('delta', 'Delta')])}
          </div>
        </div>
      </section>

      <div class="section-head">
        <div>
          <h2>Takeaways</h2>
          <p>这部分是把数字翻译成工程判断，重点看 SSA 值不值得在当前真实交易负载里默认开启。</p>
        </div>
      </div>
      <section class="grid-2">
        <article class="panel">
          <h3>Observations</h3>
          <ul class="list">
            {''.join(f"<li>{html.escape(item)}</li>" for item in observations)}
          </ul>
        </article>
        <article class="panel">
          <h3>Limitations</h3>
          <ul class="list">
            {''.join(f"<li>{html.escape(item)}</li>" for item in limitations)}
          </ul>
        </article>
      </section>
    </main>
  </body>
</html>
"""


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    bench_off = load_benchmark_bundle(args.benchmark_off)
    bench_on = load_benchmark_bundle(args.benchmark_on)
    perf_off = load_perf_bundle(args.perf_off)
    perf_on = load_perf_bundle(args.perf_on)

    bench_off_metrics = benchmark_dataset_metrics(bench_off)
    bench_on_metrics = benchmark_dataset_metrics(bench_on)
    perf_off_metrics = perf_dataset_metrics(perf_off)
    perf_on_metrics = perf_dataset_metrics(perf_on)

    bench_off_overall = benchmark_overall_metrics(bench_off)
    bench_on_overall = benchmark_overall_metrics(bench_on)
    perf_off_overall = perf_overall_metrics(perf_off)
    perf_on_overall = perf_overall_metrics(perf_on)

    dataset_names = sorted(
        set(bench_off_metrics) | set(bench_on_metrics) | set(perf_off_metrics) | set(perf_on_metrics)
    )
    cold_dataset_rows = []
    exec_dataset_rows = []
    dataset_summary_rows = []
    dataset_counts = Counter(row["dataset"] for row in bench_off["rows"])

    for name in dataset_names:
        cold_off = float(bench_off_metrics[name]["wall_mean_ms"])
        cold_on = float(bench_on_metrics[name]["wall_mean_ms"])
        exec_off = float(perf_off_metrics[name]["us_per_exec"])
        exec_on = float(perf_on_metrics[name]["us_per_exec"])
        cold_impr = better_delta(cold_off, cold_on)
        exec_impr = better_delta(exec_off, exec_on)

        cold_dataset_rows.append(
            {
                "dataset": name,
                "off_wall": cold_off,
                "on_wall": cold_on,
                "improvement": cold_impr,
            }
        )
        exec_dataset_rows.append(
            {
                "dataset": name,
                "off_us": exec_off,
                "on_us": exec_on,
                "improvement": exec_impr,
            }
        )

        perf_off_dataset_summary = perf_off["summary"]["datasets"][name]
        perf_on_dataset_summary = perf_on["summary"]["datasets"][name]
        dom_off_name, dom_off_pct = dominant_category(perf_off_dataset_summary)
        dom_on_name, dom_on_pct = dominant_category(perf_on_dataset_summary)
        dataset_summary_rows.append(
            {
                "dataset": name,
                "cold_off": cold_off,
                "cold_on": cold_on,
                "cold_improvement": cold_impr,
                "exec_off": exec_off,
                "exec_on": exec_on,
                "exec_improvement": exec_impr,
                "evm_bb_delta": pp_delta(
                    perf_off_dataset_summary["category_pct"].get("evm_bb", 0.0),
                    perf_on_dataset_summary["category_pct"].get("evm_bb", 0.0),
                ),
                "keccak_delta": pp_delta(
                    perf_off_dataset_summary["category_pct"].get("keccak", 0.0),
                    perf_on_dataset_summary["category_pct"].get("keccak", 0.0),
                ),
                "dom_off_name": dom_off_name,
                "dom_off_pct": dom_off_pct,
                "dom_on_name": dom_on_name,
                "dom_on_pct": dom_on_pct,
            }
        )

    benchmark_returncode_mismatches = compare_return_codes(
        bench_off["rows"], bench_on["rows"], "returncode"
    )
    perf_returncode_mismatches = compare_return_codes(
        perf_off["rows"], perf_on["rows"], "dtvm_returncode"
    )

    category_rows = build_category_table(perf_off["summary"], perf_on["summary"])
    top_frame_off = int(perf_off["summary"]["top_frame_samples"])
    top_frame_on = int(perf_on["summary"]["top_frame_samples"])
    host_delta_rows = top_delta_rows(
        perf_off["summary"]["top_host_symbols"],
        top_frame_off,
        perf_on["summary"]["top_host_symbols"],
        top_frame_on,
        limit=10,
    )
    keccak_delta_rows = top_delta_rows(
        perf_off["summary"]["top_keccak_symbols"],
        top_frame_off,
        perf_on["summary"]["top_keccak_symbols"],
        top_frame_on,
        limit=10,
    )
    bb_delta_rows = top_delta_rows(
        perf_off["summary"]["top_evm_bbs"],
        top_frame_off,
        perf_on["summary"]["top_evm_bbs"],
        top_frame_on,
        limit=12,
    )

    best_dataset = max(dataset_summary_rows, key=lambda row: row["exec_improvement"])
    worst_dataset = min(dataset_summary_rows, key=lambda row: row["exec_improvement"])
    exec_impr = better_delta(perf_off_overall["us_per_exec"], perf_on_overall["us_per_exec"])
    cold_impr = better_delta(bench_off_overall["wall_mean_ms"], bench_on_overall["wall_mean_ms"])
    jit_impr = better_delta(bench_off_overall["jit_mean_ms"], bench_on_overall["jit_mean_ms"])
    keccak_off = float(perf_off["summary"]["category_pct"].get("keccak", 0.0))
    keccak_on = float(perf_on["summary"]["category_pct"].get("keccak", 0.0))
    evm_off = float(perf_off["summary"]["category_pct"].get("evm_bb", 0.0))
    evm_on = float(perf_on["summary"]["category_pct"].get("evm_bb", 0.0))
    host_off = float(perf_off["summary"]["category_pct"].get("evm_host", 0.0))
    host_on = float(perf_on["summary"]["category_pct"].get("evm_host", 0.0))
    host_hot_names = set(perf_on["summary"].get("top_host_symbols", {}).keys())

    observations: list[str] = []
    if not benchmark_returncode_mismatches and not perf_returncode_mismatches:
        observations.append("本轮 40 条 prepared replay 未观察到 SSA on/off 的返回码差异，至少从返回码层面看行为一致。")
    else:
        observations.append(
            f"发现返回码差异: benchmark {len(benchmark_returncode_mismatches)} 条, perf {len(perf_returncode_mismatches)} 条；性能数字需要先让位于正确性排查。"
        )
    if bench_on["verifier_rows"] or perf_on["verifier_rows"]:
        observations.append(
            f"SSA=ON 触发 verifier error: benchmark {len(bench_on['verifier_rows'])} 条, perf {len(perf_on['verifier_rows'])} 条。这说明当前 SSA 路径在真实交易上存在 IR 合法性问题。"
        )
    elif bench_off["verifier_rows"] or perf_off["verifier_rows"]:
        observations.append(
            f"SSA=OFF 也出现 verifier error: benchmark {len(bench_off['verifier_rows'])} 条, perf {len(perf_off['verifier_rows'])} 条，需要单独排查实验噪音。"
        )
    if exec_impr is not None:
        if not perf_returncode_mismatches and not perf_on["verifier_rows"]:
            if exec_impr >= 2.0:
                observations.append(
                    f"steady-state 执行平均提升 {exec_impr:.2f}%，说明 SSA 在这组真实交易上对执行路径有可见收益。"
                )
            elif exec_impr <= -2.0:
                observations.append(
                    f"steady-state 执行平均回退 {-exec_impr:.2f}%，说明 SSA 带来的前端优化没有在真实交易上转化为净收益。"
                )
            else:
                observations.append(
                    f"steady-state 执行变化仅 {exec_impr:.2f}%，整体接近持平，说明真实交易热点不主要受 EVM 栈读写支配。"
                )
        else:
            observations.append(
                f"raw steady-state us/iter 从 {perf_off_overall['us_per_exec']:.2f} 增长到 {perf_on_overall['us_per_exec']:.2f}，但由于 perf 路径已有 {len(perf_returncode_mismatches)} 条返回码差异和 {len(perf_on['verifier_rows'])} 条 verifier error，这组时间只能按故障症状解读。"
            )
    if cold_impr is not None and jit_impr is not None:
        if not benchmark_returncode_mismatches and not bench_on["verifier_rows"]:
            observations.append(
                f"冷启动 wall time 变化 {cold_impr:.2f}%，JIT compilation 变化 {jit_impr:.2f}%。如果两者方向相反，说明 SSA 的执行收益被冷启动编译成本抵消。"
            )
        else:
            observations.append(
                f"raw 冷启动 wall time 从 {bench_off_overall['wall_mean_ms']:.2f} ms 变到 {bench_on_overall['wall_mean_ms']:.2f} ms，但 benchmark 已有 {len(benchmark_returncode_mismatches)} 条返回码差异和 {len(bench_on['verifier_rows'])} 条 verifier error，这组时间不能当作正常加速。"
            )
    observations.append(
        f"执行收益最好的数据集是 {best_dataset['dataset']} ({best_dataset['exec_improvement']:.2f}%)，最弱的是 {worst_dataset['dataset']} ({worst_dataset['exec_improvement']:.2f}%)。"
    )
    if max(keccak_off, keccak_on) >= 25.0:
        observations.append(
            f"keccak 仍占据 {max(keccak_off, keccak_on):.2f}% 级别的样本份额，说明 hash-heavy 路径会天然稀释 SSA 对纯 EVM BB 的收益。"
        )
    if max(host_off, host_on) >= 20.0:
        observations.append(
            f"host helper 仍是显著热点（最高 {max(host_off, host_on):.2f}%），说明内部调用、SLOAD/SSTORE、calldata/memory helper 仍然是更直接的优化抓手。"
        )
    if any(
        name.startswith("EVMByteCodeVisitor") or name.startswith("EVMMirBuilder")
        for name in host_hot_names
    ):
        observations.append(
            "SSA=ON 的所谓 evm_host 热点，实际上被 EVM frontend / MIR builder 符号占满，说明当前分类桶里混入了编译前端工作；这本质上是 compile-time explosion，而不是 host call 变慢。"
        )
    if evm_on < evm_off:
        observations.append(
            f"EVM basic block 样本占比从 {evm_off:.2f}% 降到 {evm_on:.2f}%，这和 SSA 预期方向一致: 少做一部分 runtime stack 读写。"
        )
    else:
        observations.append(
            f"EVM basic block 样本占比没有下降（OFF {evm_off:.2f}% / ON {evm_on:.2f}%），说明 SSA 优化效应可能被 host/hash 路径盖住，或带来了额外编译/寄存器压力。"
        )

    limitations = [
        "当前 hotset 只覆盖 4 类交易，各 10 条；不包含 UniswapX Reactor，因此不能把结论外推成五类全覆盖。",
        "execution-only 指标来自 perf attach 窗口，适合做 on/off 相对比较，但绝对数值包含 perf 采样开销。",
        "冷启动 benchmark 仍带有 --enable-statistics，因此 wall time 中包含统计采样本身的额外成本。",
        "这是一组主网真实交易 prepared replay，不是链上全量样本；对长尾 bytecode 结构的代表性有限。",
    ]

    return {
        "bench_off": {"summary": bench_off["summary"], "overall": bench_off_overall},
        "bench_on": {"summary": bench_on["summary"], "overall": bench_on_overall},
        "perf_off": {"summary": perf_off["summary"], "overall": perf_off_overall},
        "perf_on": {"summary": perf_on["summary"], "overall": perf_on_overall},
        "bench_off_path": short_path(args.benchmark_off),
        "bench_on_path": short_path(args.benchmark_on),
        "perf_off_path": short_path(args.perf_off),
        "perf_on_path": short_path(args.perf_on),
        "dataset_counts": sorted(dataset_counts.items()),
        "benchmark_exit_codes_off": summarize_exit_codes(bench_off["rows"], "returncode"),
        "benchmark_exit_codes_on": summarize_exit_codes(bench_on["rows"], "returncode"),
        "perf_exit_codes_off": summarize_exit_codes(perf_off["rows"], "dtvm_returncode"),
        "perf_exit_codes_on": summarize_exit_codes(perf_on["rows"], "dtvm_returncode"),
        "benchmark_returncode_mismatches": benchmark_returncode_mismatches,
        "perf_returncode_mismatches": perf_returncode_mismatches,
        "benchmark_verifier_off": len(bench_off["verifier_rows"]),
        "benchmark_verifier_on": len(bench_on["verifier_rows"]),
        "perf_verifier_off": len(perf_off["verifier_rows"]),
        "perf_verifier_on": len(perf_on["verifier_rows"]),
        "perf_extra_executions": perf_off["rows"][0].get("extra_executions")
        if perf_off["rows"]
        else None,
        "cold_dataset_rows": cold_dataset_rows,
        "exec_dataset_rows": exec_dataset_rows,
        "dataset_summary_rows": dataset_summary_rows,
        "category_rows": category_rows,
        "host_delta_rows": host_delta_rows,
        "keccak_delta_rows": keccak_delta_rows,
        "bb_delta_rows": bb_delta_rows,
        "observations": observations,
        "limitations": limitations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a static HTML report comparing DTVM SSA on/off replay artifacts."
    )
    parser.add_argument("--benchmark-off", type=Path, required=True)
    parser.add_argument("--benchmark-on", type=Path, required=True)
    parser.add_argument("--perf-off", type=Path, required=True)
    parser.add_argument("--perf-on", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    html_text = render_html(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
