#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


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


def key_for_row(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["dataset"]), str(row["tx_hash"]).lower()


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(fmean(values))


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f} ms"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_benchmark_bundle(root: Path) -> dict[str, Any]:
    summary = load_json(root / "summary.json")
    rows = load_jsonl(root / "runs.jsonl")
    verifier_rows = []
    for row in rows:
        if "Verifying Error" in str(row.get("stderr_tail") or ""):
            verifier_rows.append(
                {
                    "dataset": str(row["dataset"]),
                    "tx_hash": str(row["tx_hash"]).lower(),
                    "returncode": row.get("returncode"),
                }
            )
    jit_values = []
    for row in rows:
        stats = row.get("statistics") or {}
        phases = stats.get("phases") or {}
        jit = (phases.get("jit_compilation") or {}).get("total_ms")
        if jit is not None:
            jit_values.append(float(jit))
    return {
        "root": root,
        "summary": summary["summary"],
        "rows": rows,
        "verifier_rows": verifier_rows,
        "overall_jit_mean_ms": mean_or_none(jit_values),
    }


def load_sample_bundle(root: Path) -> dict[str, Any]:
    rows = load_jsonl(root / "runs.jsonl")
    if not rows:
        raise ValueError(f"no rows found in {root}")
    row = rows[0]
    return {
        "root": root,
        "row": row,
        "stderr_tail": str(row.get("stderr_tail") or ""),
    }


def compare_returncodes(
    off_rows: list[dict[str, Any]], on_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    off_map = {key_for_row(row): row for row in off_rows}
    on_map = {key_for_row(row): row for row in on_rows}
    out = []
    for key in sorted(off_map.keys() & on_map.keys()):
        off_code = off_map[key].get("returncode")
        on_code = on_map[key].get("returncode")
        if off_code != on_code:
            out.append(
                {
                    "dataset": key[0],
                    "tx_hash": key[1],
                    "off": off_code,
                    "on": on_code,
                }
            )
    return out


def render_bar_rows(
    rows: list[dict[str, Any]],
    label_key: str,
    left_key: str,
    right_key: str,
    left_name: str,
    right_name: str,
    value_fmt=str,
) -> str:
    if not rows:
        return "<p class='small'>n/a</p>"
    max_value = max(max(float(row[left_key]), float(row[right_key])) for row in rows) or 1.0
    parts = []
    for row in rows:
        left = float(row[left_key])
        right = float(row[right_key])
        left_w = (left / max_value) * 100.0
        right_w = (right / max_value) * 100.0
        parts.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{html.escape(str(row[label_key]))}</div>"
            "<div class='bar-pair'>"
            f"<div class='bar-track'><div class='bar off' style='width:{left_w:.3f}%'></div></div>"
            f"<div class='bar-val'>{html.escape(left_name)} {html.escape(value_fmt(left))}</div>"
            f"<div class='bar-track'><div class='bar on' style='width:{right_w:.3f}%'></div></div>"
            f"<div class='bar-val'>{html.escape(right_name)} {html.escape(value_fmt(right))}</div>"
            "</div></div>"
        )
    return "".join(parts)


def sample_status(sample: dict[str, Any]) -> tuple[str, str]:
    row = sample["row"]
    rc = row.get("returncode")
    stderr_tail = sample["stderr_tail"]
    if rc == 0:
        return "ok", "sample command executed"
    if rc == 109 and "arguments were not expected" in stderr_tail:
        return "bad", "CLI parse failed before execution"
    if rc == -6:
        return "bad", "process aborted during execution"
    return "warn", f"unexpected rc={rc}"


def render_html(payload: dict[str, Any]) -> str:
    bench_off = payload["bench_off"]
    bench_on = payload["bench_on"]
    mismatches = payload["mismatches"]
    mismatch_by_dataset = payload["mismatch_by_dataset"]
    verifier_by_dataset = payload["verifier_by_dataset"]
    dataset_wall_rows = payload["dataset_wall_rows"]
    sample_perf_off = payload["sample_perf_off"]
    sample_perf_on_stale = payload["sample_perf_on_stale"]
    sample_perf_on_fresh = payload["sample_perf_on_fresh"]

    perf_status_rows = []
    for label, sample in [
        ("SSA=OFF perf build sample", sample_perf_off),
        ("SSA=ON perf build sample (stale dir)", sample_perf_on_stale),
        ("SSA=ON perf build sample (fresh dir)", sample_perf_on_fresh),
    ]:
        status, note = sample_status(sample)
        perf_status_rows.append(
            {
                "label": label,
                "status": status,
                "note": note,
                "rc": sample["row"].get("returncode"),
                "wall_time_ms": sample["row"].get("wall_time_ms"),
                "path": short_path(sample["root"]),
            }
        )

    top_mismatches = mismatches[:12]
    top_verifiers = bench_on["verifier_rows"][:12]
    perf_parse_excerpt = sample_perf_on_fresh["stderr_tail"].strip().splitlines()[:2]

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>DTVM SSA On/Off Real Transaction Status - 2026-05-19</title>
    <style>
      :root {{
        --bg: #f4efe7;
        --paper: #fffdf8;
        --ink: #1f1d1a;
        --muted: #6a635a;
        --line: #ddd2c4;
        --off: #2f6f5e;
        --on: #c95a3d;
        --warn: #a67c00;
        --bad: #b42318;
        --ok: #18794e;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background:
          radial-gradient(circle at top left, #efe3d2 0, transparent 24rem),
          linear-gradient(180deg, #f5f0e8, #efe7dc 55%, #ebe1d5 100%);
        color: var(--ink);
        font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      }}
      .page {{
        max-width: 1220px;
        margin: 0 auto;
        padding: 32px 20px 72px;
      }}
      .hero {{
        display: grid;
        gap: 18px;
        grid-template-columns: 2fr 1fr;
        margin-bottom: 22px;
      }}
      .panel {{
        background: rgba(255, 253, 248, 0.9);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow: 0 10px 30px rgba(49, 37, 22, 0.06);
      }}
      h1, h2, h3 {{ margin: 0 0 12px; font-weight: 700; }}
      h1 {{ font-size: 42px; line-height: 1.05; }}
      h2 {{ font-size: 22px; }}
      h3 {{ font-size: 18px; }}
      p {{ margin: 0 0 12px; line-height: 1.55; }}
      ul {{ margin: 0; padding-left: 20px; line-height: 1.55; }}
      li + li {{ margin-top: 6px; }}
      .lede {{
        font-size: 18px;
        color: var(--muted);
        max-width: 54rem;
      }}
      .callout {{
        background: #fff3f0;
        border-left: 6px solid var(--bad);
        padding: 14px 16px;
        border-radius: 12px;
      }}
      .metrics {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0 26px;
      }}
      .metric {{
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 16px 18px;
      }}
      .metric .k {{
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .metric .v {{
        margin-top: 8px;
        font-size: 34px;
        line-height: 1;
      }}
      .metric .s {{
        margin-top: 8px;
        color: var(--muted);
        font-size: 14px;
      }}
      .grid2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
        margin-bottom: 18px;
      }}
      .grid1 {{
        display: grid;
        gap: 18px;
        margin-bottom: 18px;
      }}
      .small {{
        color: var(--muted);
        font-size: 14px;
      }}
      .mono {{
        font-family: "SFMono-Regular", ui-monospace, "Cascadia Code", "Liberation Mono", monospace;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }}
      th, td {{
        text-align: left;
        padding: 10px 8px;
        border-bottom: 1px solid var(--line);
        vertical-align: top;
      }}
      th {{
        color: var(--muted);
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      .status {{
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
      }}
      .status.ok {{ background: #e8f7ef; color: var(--ok); }}
      .status.warn {{ background: #fff5d6; color: var(--warn); }}
      .status.bad {{ background: #fde7e3; color: var(--bad); }}
      .bar-row + .bar-row {{ margin-top: 14px; }}
      .bar-label {{ font-size: 14px; margin-bottom: 6px; }}
      .bar-pair {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto;
        gap: 8px;
        align-items: center;
      }}
      .bar-track {{
        height: 12px;
        background: #efe7dc;
        border-radius: 999px;
        overflow: hidden;
      }}
      .bar {{
        height: 100%;
        border-radius: 999px;
      }}
      .bar.off {{ background: var(--off); }}
      .bar.on {{ background: var(--on); }}
      .bar-val {{ font-size: 13px; color: var(--muted); white-space: nowrap; }}
      .foot {{
        margin-top: 12px;
        color: var(--muted);
        font-size: 13px;
      }}
      code {{
        font-family: "SFMono-Regular", ui-monospace, "Cascadia Code", "Liberation Mono", monospace;
        background: #f2ece4;
        padding: 2px 4px;
        border-radius: 6px;
      }}
      @media (max-width: 920px) {{
        .hero, .grid2, .metrics {{
          grid-template-columns: 1fr;
        }}
        h1 {{ font-size: 32px; }}
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <div class="panel">
          <h1>SSA On vs Off</h1>
          <p class="lede">基于以太坊主网 40 条 prepared replay 的当前状态检查，截止 <strong>2026 年 5 月 19 日</strong>，<code>ZEN_ENABLE_EVM_STACK_SSA_LIFT=ON</code> 仍然会改变真实交易行为结果，因此这轮实验不能被解释为“纯性能开关”对比。</p>
          <div class="callout">
            <p><strong>结论先行：</strong>SSA=ON 当前更像 correctness blocker，而不是性能优化项。返回码分叉、verifier error、以及 perf build 不稳定，已经先于任何 wall time / hotspot 结论。</p>
          </div>
        </div>
        <div class="panel">
          <h2>证据边界</h2>
          <ul>
            <li>SSA=OFF 全量基线使用 2026-05-19 的 40 条历史 benchmark 工件。</li>
            <li>SSA=OFF 当前代码 spot-check 了 6 条高风险交易，<strong>6/6</strong> 与历史 off 返回码一致。</li>
            <li>SSA=ON 使用 2026-05-19 当前 <code>build_ssa</code> 的 40 条全量 benchmark。</li>
            <li>SSA=ON perf build 没有得到可用的 steady-state profiling 数据，只能报告失败形态。</li>
          </ul>
        </div>
      </section>

      <section class="metrics">
        <div class="metric">
          <div class="k">Returncode Mismatches</div>
          <div class="v">{len(mismatches)} / 40</div>
          <div class="s">历史 off 40 条 vs 当前 on 40 条</div>
        </div>
        <div class="metric">
          <div class="k">Verifier Error Rows</div>
          <div class="v">{len(bench_on["verifier_rows"])} / 40</div>
          <div class="s">SSA=ON 当前 benchmark 命中 verifier error</div>
        </div>
        <div class="metric">
          <div class="k">Spot-check Mismatches</div>
          <div class="v">5 / 6</div>
          <div class="s">当前 off spot-check vs 当前 on 对照</div>
        </div>
        <div class="metric">
          <div class="k">Stable SSA=ON Perf Samples</div>
          <div class="v">0 / 2</div>
          <div class="s">旧 perf 目录与 fresh perf 目录都不可用</div>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Raw Cold-Start Numbers</h2>
          <p>下面两组 wall/JIT 数字只保留为“原始观测”，不能解释成速度提升，因为行为结果已经分叉。</p>
          <table>
            <thead>
              <tr><th>Metric</th><th>SSA=OFF</th><th>SSA=ON</th></tr>
            </thead>
            <tbody>
              <tr><td>Mean wall time</td><td>{fmt_ms(bench_off["summary"]["wall_time_ms"]["mean"])}</td><td>{fmt_ms(bench_on["summary"]["wall_time_ms"]["mean"])}</td></tr>
              <tr><td>Mean JIT compilation</td><td>{fmt_ms(bench_off["overall_jit_mean_ms"])}</td><td>{fmt_ms(bench_on["overall_jit_mean_ms"])}</td></tr>
              <tr><td>Exit codes</td><td class="mono">{html.escape(json.dumps(bench_off["summary"]["exit_codes"], sort_keys=True))}</td><td class="mono">{html.escape(json.dumps(bench_on["summary"]["exit_codes"], sort_keys=True))}</td></tr>
            </tbody>
          </table>
          <p class="foot">SSA=ON 的 raw 平均 wall 看起来更低，但这主要是因为它提前以 <code>1/2/7/8</code> 等非 off 基线返回码结束；不能视为真实加速。</p>
        </div>

        <div class="panel">
          <h2>Mismatch By Dataset</h2>
          {render_bar_rows(mismatch_by_dataset, "dataset", "off_count", "on_count", "off mismatches", "on mismatches", lambda v: f"{int(v)} tx")}
          <p class="foot">这里左右条形都画成同一个 mismatch 数，只是为了让分布更直观看出来。ERC-4337 bundle 的 8/10 全量分叉最明显，Uniswap V3 与 CoW 也不是局部问题。</p>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Mean Wall By Dataset</h2>
          {render_bar_rows(dataset_wall_rows, "dataset", "off_wall_ms", "on_wall_ms", "off", "on", fmt_ms)}
          <p class="foot">左边是历史 off 40 条，全量右边是当前 on 40 条。只作为现象记录，不作为有效性能增益。</p>
        </div>

        <div class="panel">
          <h2>Verifier Error Coverage</h2>
          <table>
            <thead>
              <tr><th>Dataset</th><th>Verifier Rows</th><th>Coverage</th></tr>
            </thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(name)}</td><td>{count}</td><td>{fmt_pct((count/10.0)*100.0)}</td></tr>" for name, count in verifier_by_dataset.items())}
            </tbody>
          </table>
          <p class="foot">最坏点不只是在 non-zero 返回码上。这里还有 16 条 verifier error，其中一部分最终仍返回 <code>0</code>，说明 “执行成功” 和 “IR 合法” 已经脱钩。</p>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Representative Mismatches</h2>
          <table>
            <thead>
              <tr><th>Dataset</th><th>Tx</th><th>OFF</th><th>ON</th></tr>
            </thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(row['dataset'])}</td><td class='mono'>{html.escape(row['tx_hash'][:18])}...</td><td>{row['off']}</td><td>{row['on']}</td></tr>" for row in top_mismatches)}
            </tbody>
          </table>
        </div>

        <div class="panel">
          <h2>Representative Verifier Rows</h2>
          <table>
            <thead>
              <tr><th>Dataset</th><th>Tx</th><th>Return</th></tr>
            </thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(row['dataset'])}</td><td class='mono'>{html.escape(row['tx_hash'][:18])}...</td><td>{row['returncode']}</td></tr>" for row in top_verifiers)}
            </tbody>
          </table>
        </div>
      </section>

      <section class="grid1">
        <div class="panel">
          <h2>Perf Build Health</h2>
          <table>
            <thead>
              <tr><th>Build</th><th>Status</th><th>RC</th><th>Wall</th><th>Artifact</th><th>Note</th></tr>
            </thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(row['label'])}</td><td><span class='status {row['status']}'>{row['status']}</span></td><td>{row['rc']}</td><td>{fmt_ms(row['wall_time_ms'])}</td><td class='mono'>{html.escape(row['path'])}</td><td>{html.escape(row['note'])}</td></tr>" for row in perf_status_rows)}
            </tbody>
          </table>
          <p class="foot">含义很直接：当前没有一条可拿来做 SSA on steady-state hotspot profiling 的稳定 perf 路径。</p>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Perf Failure Notes</h2>
          <ul>
            <li>旧的 <code>build_perf_ssa</code> 样本在同一条 <code>uniswap_v3_swap</code> 上直接返回 <code>-6</code>，未留下有用 stderr。</li>
            <li>全新 clean 的 <code>build_perf_ssa_fresh</code> 样本返回 <code>109</code>，在开始执行前就触发 CLI parse error。</li>
            <li>相同 prepared command 在 <code>build_perf</code>（SSA=OFF）上能正常执行并返回 <code>0</code>。</li>
          </ul>
          <p class="small mono">{html.escape(" | ".join(perf_parse_excerpt))}</p>
        </div>

        <div class="panel">
          <h2>Interpretation</h2>
          <ul>
            <li>SSA=ON 当前首先是 correctness regression：40 条里有 24 条返回码与 off 基线不同，且 16 条出现 verifier error。</li>
            <li>性能数字不能脱离行为结果阅读。哪怕 raw wall/JIT 看起来下降，也更可能只是更早失败、不同 fallback 路径、或 compile-time fault symptom。</li>
            <li>perf-enabled SSA 路径连最小单样本都不稳定，说明“execution hotspot profiling”这一步必须等 correctness gate 过了再继续。</li>
          </ul>
        </div>
      </section>

      <section class="grid1">
        <div class="panel">
          <h2>Recommended Next Steps</h2>
          <ul>
            <li>先把 SSA 当前真实交易上的 verifier 问题清零，尤其是 phi placement / incoming count 相关错误；目标是 40 条 prepared replay 与 off 基线返回码完全一致。</li>
            <li>单独修 perf-enabled SSA build 的执行路径，至少让 <code>build_perf_ssa</code> 与 <code>build_perf_ssa_fresh</code> 都能稳定跑通同一条 prepared replay，再谈 x500 / x5000 profiling。</li>
            <li>只有在 “零返回码分叉 + 零 verifier error + perf build 可执行” 三个条件都满足之后，才重新生成 SSA on/off 的性能对比 HTML。</li>
          </ul>
        </div>
      </section>

      <section class="grid1">
        <div class="panel">
          <h2>Artifact Paths</h2>
          <ul class="mono">
            <li>{html.escape(short_path(bench_off["root"]))}</li>
            <li>{html.escape(short_path(bench_on["root"]))}</li>
            <li>{html.escape(short_path(payload["spotcheck_off"]["root"]))}</li>
            <li>{html.escape(short_path(sample_perf_off["root"]))}</li>
            <li>{html.escape(short_path(sample_perf_on_stale["root"]))}</li>
            <li>{html.escape(short_path(sample_perf_on_fresh["root"]))}</li>
          </ul>
        </div>
      </section>
    </div>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render an HTML status report for SSA on/off replay behavior."
    )
    parser.add_argument("--benchmark-off", required=True)
    parser.add_argument("--benchmark-on", required=True)
    parser.add_argument("--spotcheck-off", required=True)
    parser.add_argument("--perf-off-sample", required=True)
    parser.add_argument("--perf-on-stale-sample", required=True)
    parser.add_argument("--perf-on-fresh-sample", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bench_off = load_benchmark_bundle(Path(args.benchmark_off))
    bench_on = load_benchmark_bundle(Path(args.benchmark_on))
    spotcheck_off = load_sample_bundle(Path(args.spotcheck_off))
    perf_off_sample = load_sample_bundle(Path(args.perf_off_sample))
    perf_on_stale_sample = load_sample_bundle(Path(args.perf_on_stale_sample))
    perf_on_fresh_sample = load_sample_bundle(Path(args.perf_on_fresh_sample))

    mismatches = compare_returncodes(bench_off["rows"], bench_on["rows"])
    mismatch_counter = Counter(row["dataset"] for row in mismatches)
    mismatch_by_dataset = [
        {"dataset": name, "off_count": count, "on_count": count}
        for name, count in sorted(mismatch_counter.items())
    ]

    verifier_counter = Counter(row["dataset"] for row in bench_on["verifier_rows"])
    verifier_by_dataset = dict(sorted(verifier_counter.items()))

    off_datasets = bench_off["summary"]["datasets"]
    on_datasets = bench_on["summary"]["datasets"]
    dataset_names = sorted(set(off_datasets.keys()) | set(on_datasets.keys()))
    dataset_wall_rows = []
    for name in dataset_names:
        off_wall = ((off_datasets.get(name) or {}).get("wall_time_ms") or {}).get("mean") or 0.0
        on_wall = ((on_datasets.get(name) or {}).get("wall_time_ms") or {}).get("mean") or 0.0
        dataset_wall_rows.append(
            {"dataset": name, "off_wall_ms": float(off_wall), "on_wall_ms": float(on_wall)}
        )

    payload = {
        "bench_off": bench_off,
        "bench_on": bench_on,
        "spotcheck_off": spotcheck_off,
        "sample_perf_off": perf_off_sample,
        "sample_perf_on_stale": perf_on_stale_sample,
        "sample_perf_on_fresh": perf_on_fresh_sample,
        "mismatches": mismatches,
        "mismatch_by_dataset": mismatch_by_dataset,
        "verifier_by_dataset": verifier_by_dataset,
        "dataset_wall_rows": dataset_wall_rows,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(payload), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
