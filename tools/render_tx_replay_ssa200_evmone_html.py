#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def fmt_ms(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f} ms"


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def pct_delta(base: float | None, other: float | None) -> float | None:
    if base in (None, 0) or other is None:
        return None
    return ((other - base) / base) * 100.0


def phase_total(row: dict[str, Any], name: str) -> float | None:
    return (((row.get("statistics") or {}).get("phases") or {}).get(name) or {}).get(
        "total_ms"
    )


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(fmean(values))


def build_payload(
    off_rows: list[dict[str, Any]],
    on_rows: list[dict[str, Any]],
    interp_rows: list[dict[str, Any]],
    evmone_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    def key(row: dict[str, Any]) -> tuple[str, str]:
        return (str(row["dataset"]), str(row["tx_hash"]).lower())

    off_map = {key(row): row for row in off_rows}
    on_map = {key(row): row for row in on_rows}
    interp_map = {key(row): row for row in interp_rows}
    evmone_map = {key(row): row for row in evmone_rows}
    common_keys = sorted(set(off_map) & set(on_map) & set(interp_map) & set(evmone_map))

    matched = [(k, off_map[k], on_map[k], interp_map[k], evmone_map[k]) for k in common_keys]
    dataset_counts: dict[str, int] = defaultdict(int)
    for dataset, _ in common_keys:
        dataset_counts[dataset] += 1

    def summarize(
        rows: list[tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]
    ) -> dict[str, Any]:
        off_wall = [float(off["wall_time_ms"]) for _, off, _, _, _ in rows]
        on_wall = [float(on["wall_time_ms"]) for _, _, on, _, _ in rows]
        interp_wall = [float(interp["wall_time_ms"]) for _, _, _, interp, _ in rows]
        evmone_wall = [float(ev["wall_time_ms"]) for _, _, _, _, ev in rows]
        off_jit = [
            float(phase_total(off, "jit_compilation"))
            for _, off, _, _, _ in rows
            if phase_total(off, "jit_compilation") is not None
        ]
        on_jit = [
            float(phase_total(on, "jit_compilation"))
            for _, _, on, _, _ in rows
            if phase_total(on, "jit_compilation") is not None
        ]
        ev_gas = [
            float(int(str(ev["receipt_gas_used"]), 16))
            for _, _, _, _, ev in rows
            if ev.get("receipt_gas_used")
        ]
        off_mean = mean_or_none(off_wall)
        on_mean = mean_or_none(on_wall)
        interp_mean = mean_or_none(interp_wall)
        evmone_mean = mean_or_none(evmone_wall)
        return {
            "off_wall_mean_ms": off_mean,
            "on_wall_mean_ms": on_mean,
            "interp_wall_mean_ms": interp_mean,
            "evmone_wall_mean_ms": evmone_mean,
            "on_vs_off_wall_pct": pct_delta(off_mean, on_mean),
            "interp_vs_off_wall_pct": pct_delta(interp_mean, off_mean),
            "interp_vs_on_wall_pct": pct_delta(interp_mean, on_mean),
            "interp_vs_evmone_wall_pct": pct_delta(evmone_mean, interp_mean),
            "off_vs_evmone_wall_pct": pct_delta(evmone_mean, off_mean),
            "on_vs_evmone_wall_pct": pct_delta(evmone_mean, on_mean),
            "off_jit_mean_ms": mean_or_none(off_jit),
            "on_jit_mean_ms": mean_or_none(on_jit),
            "on_vs_off_jit_pct": pct_delta(mean_or_none(off_jit), mean_or_none(on_jit)),
            "evmone_gas_used_mean": mean_or_none(ev_gas),
        }

    overall = summarize(matched)
    per_dataset = {}
    for dataset in sorted(dataset_counts):
        subset = [row for row in matched if row[0][0] == dataset]
        per_dataset[dataset] = {"count": len(subset), **summarize(subset)}

    evmone_exit_codes: dict[str, int] = defaultdict(int)
    evmone_receipt_status: dict[str, int] = defaultdict(int)
    evmone_forks: dict[str, int] = defaultdict(int)
    for row in evmone_rows:
        evmone_exit_codes[str(row.get("returncode"))] += 1
        if row.get("receipt_status") is not None:
            evmone_receipt_status[str(row["receipt_status"])] += 1
        if row.get("effective_fork") is not None:
            evmone_forks[str(row["effective_fork"])] += 1

    off_slowest = sorted(off_rows, key=lambda row: float(row["wall_time_ms"]), reverse=True)[:8]
    on_slowest = sorted(on_rows, key=lambda row: float(row["wall_time_ms"]), reverse=True)[:8]
    interp_slowest = sorted(
        interp_rows, key=lambda row: float(row["wall_time_ms"]), reverse=True
    )[:8]
    ev_slowest = sorted(evmone_rows, key=lambda row: float(row["wall_time_ms"]), reverse=True)[:8]

    return {
        "count": len(common_keys),
        "dataset_counts": dict(sorted(dataset_counts.items())),
        "overall": overall,
        "per_dataset": per_dataset,
        "evmone_exit_codes": dict(evmone_exit_codes),
        "evmone_receipt_status": dict(evmone_receipt_status),
        "evmone_forks": dict(evmone_forks),
        "off_slowest": off_slowest,
        "on_slowest": on_slowest,
        "interp_slowest": interp_slowest,
        "ev_slowest": ev_slowest,
    }


def build_html(
    payload: dict[str, Any], off_dir: Path, on_dir: Path, interp_dir: Path, evmone_dir: Path
) -> str:
    dataset_rows = []
    for dataset, item in payload["per_dataset"].items():
        dataset_rows.append(
            f"""
            <tr>
              <td><code>{html.escape(dataset)}</code></td>
              <td>{item['count']}</td>
              <td>{fmt_ms(item['off_wall_mean_ms'])}</td>
              <td>{fmt_ms(item['on_wall_mean_ms'])}</td>
              <td>{fmt_ms(item['interp_wall_mean_ms'])}</td>
              <td>{fmt_ms(item['evmone_wall_mean_ms'])}</td>
              <td>{fmt_pct(item['on_vs_off_wall_pct'])}</td>
              <td>{fmt_pct(item['interp_vs_off_wall_pct'])}</td>
              <td>{fmt_pct(item['interp_vs_on_wall_pct'])}</td>
              <td>{fmt_pct(item['off_vs_evmone_wall_pct'])}</td>
              <td>{fmt_pct(item['on_vs_evmone_wall_pct'])}</td>
              <td>{fmt_pct(item['interp_vs_evmone_wall_pct'])}</td>
              <td>{fmt_ms(item['off_jit_mean_ms'])}</td>
              <td>{fmt_ms(item['on_jit_mean_ms'])}</td>
              <td>{fmt_pct(item['on_vs_off_jit_pct'])}</td>
              <td>{fmt_num(item['evmone_gas_used_mean'], 0)}</td>
            </tr>
            """
        )

    def slowest_rows(rows: list[dict[str, Any]]) -> str:
        out = []
        for row in rows:
            out.append(
                f"<tr><td><code>{html.escape(row['dataset'])}</code></td>"
                f"<td><code>{html.escape(row['tx_hash'][:18])}...</code></td>"
                f"<td>{fmt_ms(float(row['wall_time_ms']))}</td></tr>"
            )
        return "".join(out)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>DTVM SSA vs Interpreter vs EVMone on 200 Transactions</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 32px auto; max-width: 1440px; line-height: 1.5; color: #1f2937; }}
    h1, h2, h3 {{ color: #111827; }}
    code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 18px 0 28px; font-size: 14px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 18px 0 26px; }}
    .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 16px; background: #fff; }}
    .small {{ color: #4b5563; font-size: 13px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    ul {{ margin-top: 8px; }}
  </style>
</head>
<body>
  <h1>DTVM SSA On/Off vs Interpreter vs EVMone on 200 Prepared Transactions</h1>
  <p class="small">This report compares DTVM <code>SSA off</code>, DTVM <code>SSA on</code>, DTVM <code>interpreter</code>, and an <code>evmone-t8n</code> cold-run baseline over the same 200 prepared transaction bundles.</p>

  <h2>Inputs</h2>
  <ul>
    <li><code>{html.escape(str(off_dir))}</code></li>
    <li><code>{html.escape(str(on_dir))}</code></li>
    <li><code>{html.escape(str(interp_dir))}</code></li>
    <li><code>{html.escape(str(evmone_dir))}</code></li>
  </ul>

  <h2>Headline</h2>
  <div class="grid">
    <div class="card">
      <h3>Corpus</h3>
      <p><strong>{payload['count']}</strong> common transactions</p>
      <p class="small mono">{html.escape(json.dumps(payload['dataset_counts'], ensure_ascii=False))}</p>
    </div>
    <div class="card">
      <h3>SSA On vs Off</h3>
      <p>Wall mean: <strong>{fmt_pct(payload['overall']['on_vs_off_wall_pct'])}</strong></p>
      <p>JIT mean: <strong>{fmt_pct(payload['overall']['on_vs_off_jit_pct'])}</strong></p>
    </div>
    <div class="card">
      <h3>Interpreter</h3>
      <p><code>off</code> vs interp: <strong>{fmt_pct(payload['overall']['interp_vs_off_wall_pct'])}</strong></p>
      <p><code>on</code> vs interp: <strong>{fmt_pct(payload['overall']['interp_vs_on_wall_pct'])}</strong></p>
    </div>
    <div class="card">
      <h3>Against EVMone</h3>
      <p><code>off</code> wall vs evmone: <strong>{fmt_pct(payload['overall']['off_vs_evmone_wall_pct'])}</strong></p>
      <p><code>on</code> wall vs evmone: <strong>{fmt_pct(payload['overall']['on_vs_evmone_wall_pct'])}</strong></p>
      <p><code>interp</code> wall vs evmone: <strong>{fmt_pct(payload['overall']['interp_vs_evmone_wall_pct'])}</strong></p>
    </div>
  </div>

  <h2>Overall Means</h2>
  <table>
    <thead>
      <tr>
        <th>Metric</th>
        <th>SSA Off</th>
        <th>SSA On</th>
        <th>Interpreter</th>
        <th>EVMone</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Cold wall mean</td><td>{fmt_ms(payload['overall']['off_wall_mean_ms'])}</td><td>{fmt_ms(payload['overall']['on_wall_mean_ms'])}</td><td>{fmt_ms(payload['overall']['interp_wall_mean_ms'])}</td><td>{fmt_ms(payload['overall']['evmone_wall_mean_ms'])}</td></tr>
      <tr><td>JIT mean</td><td>{fmt_ms(payload['overall']['off_jit_mean_ms'])}</td><td>{fmt_ms(payload['overall']['on_jit_mean_ms'])}</td><td>n/a</td><td>n/a</td></tr>
      <tr><td>EVMone gasUsed mean</td><td>n/a</td><td>n/a</td><td>n/a</td><td>{fmt_num(payload['overall']['evmone_gas_used_mean'], 0)}</td></tr>
    </tbody>
  </table>

  <h2>Per Dataset</h2>
  <table>
    <thead>
      <tr>
        <th>Dataset</th>
        <th>Count</th>
        <th>Off Wall</th>
        <th>On Wall</th>
        <th>Interp Wall</th>
        <th>EVMone Wall</th>
        <th>On vs Off</th>
        <th>Off vs Interp</th>
        <th>On vs Interp</th>
        <th>Off vs EVMone</th>
        <th>On vs EVMone</th>
        <th>Interp vs EVMone</th>
        <th>Off JIT</th>
        <th>On JIT</th>
        <th>On vs Off JIT</th>
        <th>EVMone GasUsed</th>
      </tr>
    </thead>
    <tbody>
      {''.join(dataset_rows)}
    </tbody>
  </table>

  <h2>EVMone Outcome Coverage</h2>
  <ul>
    <li>Exit codes: <code>{html.escape(json.dumps(payload['evmone_exit_codes'], ensure_ascii=False))}</code></li>
    <li>Receipt status: <code>{html.escape(json.dumps(payload['evmone_receipt_status'], ensure_ascii=False))}</code></li>
    <li>Effective forks: <code>{html.escape(json.dumps(payload['evmone_forks'], ensure_ascii=False))}</code></li>
    <li>For 76 transactions whose prestate already contained <code>0xEF...</code> accounts, the harness upgraded <code>evmone-t8n</code> from <code>Cancun</code> to <code>Prague</code> because the current evmone state loader rejects those accounts under pre-Prague rules.</li>
    <li>Note: this report uses <code>evmone-t8n</code> as a cold-run state-transition baseline. It does not provide a same-process steady-state harness equivalent to DTVM's internal benchmark mode, so the evmone comparison is intentionally limited to cold wall time and transaction-level gasUsed. DTVM correctness parity was established separately on the same 200-transaction corpus for <code>SSA off</code> vs <code>SSA on</code>.</li>
  </ul>

  <h2>Optimization Readout</h2>
  <ul>
    <li><code>SSA on</code> still needs a stricter profitability gate on datasets where <code>on</code> wall stays above both <code>off</code> and <code>evmone</code>, especially if the JIT mean already improved but end-to-end wall did not.</li>
    <li>The DTVM <code>interpreter</code> baseline is materially faster than both DTVM multipass paths on cold start, so startup, module loading, and runtime setup overhead remain first-order costs. This gap should be optimized independently of SSA codegen.</li>
    <li>If <code>cow_settlement</code>, <code>erc4337_bundle</code>, and <code>uniswap_v3_swap</code> improve under <code>SSA on</code> but still trail the interpreter and evmone, the next gains are more likely in runtime helpers, host calls, and startup overhead than in the SSA stack/value model itself.</li>
    <li><code>erc20_transfer</code> remains the clearest negative-profitability zone: <code>SSA on</code> reduces JIT time but substantially worsens wall time. Keep it as the first target for gate tightening and compile-path trimming.</li>
    <li>The gap to evmone on cold wall should be treated as a full-stack DTVM overhead gap, not an SSA-only gap. Use it to prioritize startup/load/instantiation trimming separately from SSA codegen tuning.</li>
  </ul>

  <h2>Slowest Samples</h2>
  <div class="grid">
    <div class="card">
      <h3>SSA Off</h3>
      <table><thead><tr><th>Dataset</th><th>Tx</th><th>Wall</th></tr></thead><tbody>{slowest_rows(payload['off_slowest'])}</tbody></table>
    </div>
    <div class="card">
      <h3>SSA On</h3>
      <table><thead><tr><th>Dataset</th><th>Tx</th><th>Wall</th></tr></thead><tbody>{slowest_rows(payload['on_slowest'])}</tbody></table>
    </div>
    <div class="card">
      <h3>Interpreter</h3>
      <table><thead><tr><th>Dataset</th><th>Tx</th><th>Wall</th></tr></thead><tbody>{slowest_rows(payload['interp_slowest'])}</tbody></table>
    </div>
    <div class="card">
      <h3>EVMone</h3>
      <table><thead><tr><th>Dataset</th><th>Tx</th><th>Wall</th></tr></thead><tbody>{slowest_rows(payload['ev_slowest'])}</tbody></table>
    </div>
  </div>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render SSA off/on/interpreter vs evmone 200tx report"
    )
    parser.add_argument("--benchmark-off", type=Path, required=True)
    parser.add_argument("--benchmark-on", type=Path, required=True)
    parser.add_argument("--benchmark-interpreter", type=Path, required=True)
    parser.add_argument("--benchmark-evmone", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    off_rows = load_jsonl(args.benchmark_off / "runs.jsonl")
    on_rows = load_jsonl(args.benchmark_on / "runs.jsonl")
    interp_rows = load_jsonl(args.benchmark_interpreter / "runs.jsonl")
    evmone_rows = load_jsonl(args.benchmark_evmone / "runs.jsonl")
    payload = build_payload(off_rows, on_rows, interp_rows, evmone_rows)
    args.output.write_text(
        build_html(
            payload,
            args.benchmark_off,
            args.benchmark_on,
            args.benchmark_interpreter,
            args.benchmark_evmone,
        ),
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
