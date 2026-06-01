#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median
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


def fmt_pct(value: float | None, digits: int = 2, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def key_for_row(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row["dataset"]),
        str(row["tx_hash"]).lower(),
        int(row.get("repetition", 0)),
    )


def phase_total(row: dict[str, Any], name: str) -> float | None:
    return (((row.get("statistics") or {}).get("phases") or {}).get(name) or {}).get(
        "total_ms"
    )


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(fmean(values))


def median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(median(values))


def pct_delta(off: float | None, on: float | None) -> float | None:
    if off in (None, 0) or on is None:
        return None
    return ((on - off) / off) * 100.0


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(col)}</th>" for col in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def dataset_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row["dataset"])] += 1
    return dict(sorted(counts.items()))


def build_payload(off_rows: list[dict[str, Any]], on_rows: list[dict[str, Any]]) -> dict[str, Any]:
    off_map = {key_for_row(row): row for row in off_rows}
    on_map = {key_for_row(row): row for row in on_rows}
    common_keys = sorted(set(off_map) & set(on_map))

    matched: list[tuple[tuple[str, str, int], dict[str, Any], dict[str, Any]]] = []
    mismatches: list[tuple[tuple[str, str, int], dict[str, Any], dict[str, Any]]] = []
    for key in common_keys:
        off_row = off_map[key]
        on_row = on_map[key]
        if off_row.get("returncode") == on_row.get("returncode"):
            matched.append((key, off_row, on_row))
        else:
            mismatches.append((key, off_row, on_row))

    def summarize_triplets(
        rows: list[tuple[tuple[str, str, int], dict[str, Any], dict[str, Any]]]
    ) -> dict[str, float | None]:
        off_wall = [off_row["wall_time_ms"] for _, off_row, _ in rows]
        on_wall = [on_row["wall_time_ms"] for _, _, on_row in rows]
        off_jit = [
            phase_total(off_row, "jit_compilation")
            for _, off_row, _ in rows
            if phase_total(off_row, "jit_compilation") is not None
        ]
        on_jit = [
            phase_total(on_row, "jit_compilation")
            for _, _, on_row in rows
            if phase_total(on_row, "jit_compilation") is not None
        ]
        off_stat = [
            (off_row.get("statistics") or {}).get("total_ms")
            for _, off_row, _ in rows
            if (off_row.get("statistics") or {}).get("total_ms") is not None
        ]
        on_stat = [
            (on_row.get("statistics") or {}).get("total_ms")
            for _, _, on_row in rows
            if (on_row.get("statistics") or {}).get("total_ms") is not None
        ]
        return {
            "off_wall_mean_ms": mean_or_none(off_wall),
            "on_wall_mean_ms": mean_or_none(on_wall),
            "wall_delta_pct": pct_delta(mean_or_none(off_wall), mean_or_none(on_wall)),
            "off_jit_mean_ms": mean_or_none(off_jit),
            "on_jit_mean_ms": mean_or_none(on_jit),
            "jit_delta_pct": pct_delta(mean_or_none(off_jit), mean_or_none(on_jit)),
            "off_stat_mean_ms": mean_or_none(off_stat),
            "on_stat_mean_ms": mean_or_none(on_stat),
            "stat_delta_pct": pct_delta(mean_or_none(off_stat), mean_or_none(on_stat)),
        }

    overall_all = summarize_triplets([(key, off_map[key], on_map[key]) for key in common_keys])
    overall_matched = summarize_triplets(matched)

    per_dataset: dict[str, Any] = {}
    for dataset in sorted({key[0] for key in common_keys}):
        dataset_rows = [item for item in matched if item[0][0] == dataset]
        off_dataset_all = [off_map[key] for key in common_keys if key[0] == dataset]
        on_dataset_all = [on_map[key] for key in common_keys if key[0] == dataset]
        same_jit_rows = 0
        for _, off_row, on_row in dataset_rows:
            if (
                phase_total(off_row, "jit_compilation") is not None
                and phase_total(on_row, "jit_compilation") is not None
            ):
                same_jit_rows += 1
        per_dataset[dataset] = {
            "total_runs": len(off_dataset_all),
            "matched_runs": len(dataset_rows),
            "mismatch_runs": len([item for item in mismatches if item[0][0] == dataset]),
            "off_jit_rows": len(
                [row for row in off_dataset_all if phase_total(row, "jit_compilation") is not None]
            ),
            "on_jit_rows": len(
                [row for row in on_dataset_all if phase_total(row, "jit_compilation") is not None]
            ),
            "same_jit_rows": same_jit_rows,
            **summarize_triplets(dataset_rows),
        }

    wall_regressions = []
    wall_improvements = []
    jit_regressions = []
    jit_improvements = []
    noise_examples = []
    for (dataset, tx_hash, _), off_row, on_row in matched:
        off_wall = float(off_row["wall_time_ms"])
        on_wall = float(on_row["wall_time_ms"])
        wall_delta = pct_delta(off_wall, on_wall)
        record = {
            "dataset": dataset,
            "tx_hash": tx_hash,
            "returncode": off_row["returncode"],
            "off_wall_ms": off_wall,
            "on_wall_ms": on_wall,
            "wall_delta_pct": wall_delta,
            "off_jit_ms": phase_total(off_row, "jit_compilation"),
            "on_jit_ms": phase_total(on_row, "jit_compilation"),
        }
        if wall_delta is not None:
            wall_regressions.append(record)
            wall_improvements.append(record)

        off_jit = phase_total(off_row, "jit_compilation")
        on_jit = phase_total(on_row, "jit_compilation")
        if off_jit not in (None, 0) and on_jit is not None:
            jit_delta = pct_delta(float(off_jit), float(on_jit))
            jit_record = {
                "dataset": dataset,
                "tx_hash": tx_hash,
                "returncode": off_row["returncode"],
                "off_jit_ms": float(off_jit),
                "on_jit_ms": float(on_jit),
                "jit_delta_pct": jit_delta,
            }
            if jit_delta is not None:
                jit_regressions.append(jit_record)
                jit_improvements.append(jit_record)

        off_stat = (off_row.get("statistics") or {}).get("total_ms")
        on_stat = (on_row.get("statistics") or {}).get("total_ms")
        if off_stat not in (None, 0) and on_stat not in (None, 0):
            noise_examples.append(
                {
                    "dataset": dataset,
                    "tx_hash": tx_hash,
                    "off_wall_ms": off_wall,
                    "on_wall_ms": on_wall,
                    "off_stat_ms": float(off_stat),
                    "on_stat_ms": float(on_stat),
                    "off_ratio": off_wall / float(off_stat),
                    "on_ratio": on_wall / float(on_stat),
                    "returncode": off_row["returncode"],
                }
            )

    wall_regressions.sort(key=lambda item: item["wall_delta_pct"] or 0.0, reverse=True)
    wall_improvements.sort(key=lambda item: item["wall_delta_pct"] or 0.0)
    jit_regressions.sort(key=lambda item: item["jit_delta_pct"] or 0.0, reverse=True)
    jit_improvements.sort(key=lambda item: item["jit_delta_pct"] or 0.0)
    noise_examples.sort(key=lambda item: max(item["off_ratio"], item["on_ratio"]), reverse=True)

    verifier_off = len(
        [row for row in off_rows if "Verifying Error" in str(row.get("stderr_tail") or "")]
    )
    verifier_on = len(
        [row for row in on_rows if "Verifying Error" in str(row.get("stderr_tail") or "")]
    )

    return {
        "sample_target": 200,
        "prepared_count": len(common_keys),
        "dataset_counts": dataset_counts(off_rows),
        "matched_count": len(matched),
        "mismatch_count": len(mismatches),
        "mismatches": [
            {
                "dataset": key[0],
                "tx_hash": key[1],
                "off": off_row.get("returncode"),
                "on": on_row.get("returncode"),
                "off_wall_ms": off_row.get("wall_time_ms"),
                "on_wall_ms": on_row.get("wall_time_ms"),
            }
            for key, off_row, on_row in mismatches
        ],
        "overall_all": overall_all,
        "overall_matched": overall_matched,
        "per_dataset": per_dataset,
        "wall_regressions": wall_regressions[:12],
        "wall_improvements": wall_improvements[:12],
        "jit_regressions": jit_regressions[:12],
        "jit_improvements": jit_improvements[:12],
        "noise_examples": noise_examples[:8],
        "verifier_off": verifier_off,
        "verifier_on": verifier_on,
    }


def build_html(payload: dict[str, Any], benchmark_off: Path, benchmark_on: Path) -> str:
    mismatch_rows = [
        [
            html.escape(item["dataset"]),
            f"<code>{html.escape(item['tx_hash'])}</code>",
            html.escape(str(item["off"])),
            html.escape(str(item["on"])),
            fmt_ms(item["off_wall_ms"]),
            fmt_ms(item["on_wall_ms"]),
        ]
        for item in payload["mismatches"]
    ]
    dataset_rows = []
    for name, item in payload["per_dataset"].items():
        dataset_rows.append(
            [
                html.escape(name),
                str(item["matched_runs"]),
                str(item["mismatch_runs"]),
                str(item["off_jit_rows"]),
                str(item["on_jit_rows"]),
                fmt_pct(item["wall_delta_pct"]),
                fmt_pct(item["jit_delta_pct"]),
                fmt_pct(item["stat_delta_pct"]),
            ]
        )

    def perf_rows(items: list[dict[str, Any]], delta_key: str, off_key: str, on_key: str) -> list[list[str]]:
        return [
            [
                html.escape(item["dataset"]),
                f"<code>{html.escape(item['tx_hash'])}</code>",
                html.escape(str(item["returncode"])),
                fmt_ms(item[off_key]),
                fmt_ms(item[on_key]),
                fmt_pct(item[delta_key]),
            ]
            for item in items
        ]

    noise_rows = [
        [
            html.escape(item["dataset"]),
            f"<code>{html.escape(item['tx_hash'])}</code>",
            html.escape(str(item["returncode"])),
            fmt_ms(item["off_wall_ms"]),
            fmt_ms(item["off_stat_ms"]),
            f"{item['off_ratio']:.1f}x",
            fmt_ms(item["on_wall_ms"]),
            fmt_ms(item["on_stat_ms"]),
            f"{item['on_ratio']:.1f}x",
        ]
        for item in payload["noise_examples"]
    ]

    overall_all = payload["overall_all"]
    overall_matched = payload["overall_matched"]

    optimization_points = [
        "先清零剩余 4 条分叉交易。当前是 3 条 erc20_transfer 和 1 条 erc4337_bundle 在 SSA=ON 下变成 -6；这一步不完成，175 条全量数字都不能被解释成纯性能结论。",
        "把 SSA profitability gate 做得更细，而不是只看“能不能 lift”。erc20_transfer 与 erc4337_bundle 在 matched 子集上分别出现 JIT 平均 +11.64% 和 +6.17% 的回退，说明小而 call-heavy、merge-heavy 的图形并不天然适合 SSA。",
        "保留并放大对 deep-stack、straight-line 热路径的收益。uniswap_v3_swap 与 cow_settlement 在 matched 子集上 JIT 分别改善 7.37% 和 8.49%，说明 SSA 的正收益主要集中在 stack traffic 重、控制流相对规整的路径。",
        "限制 compile-time outlier。当前最差样本 JIT 回退仍可超过 2x，建议给 phi/merge repair、stack-state cloning、block rewrite 增加预算或 bailout 条件，避免少数图形把整个 compile budget 拉爆。",
        "把 fallback/非-JIT 视作第一类统计对象。171 条 matched 里只有 100 条在 on/off 两边都出现 JIT compilation phase，剩余 71 条两边都没有 JIT phase；说明相当一部分交易根本没有进入可比较的 SSA 编译路径。",
        "后续若要继续优化执行期，再单独做 execution-heavy 测量。当前很多最慢样本的 CLI wall 比 statistics total 大几十到上百倍，说明冷启动 wall 主要被进程/加载/状态准备淹没，单靠这组数字很难评价 SSA 对 steady-state 执行的真实收益。",
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DTVM SSA On/Off 175-Tx Performance Report</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --card: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d6d3cc;
      --good: #116149;
      --bad: #9f1239;
      --flat: #7c5e10;
      --accent: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(29,78,216,0.08), transparent 26%),
        radial-gradient(circle at left 20%, rgba(17,97,73,0.08), transparent 24%),
        var(--bg);
    }}
    .wrap {{ max-width: 1240px; margin: 0 auto; padding: 32px 24px 72px; }}
    h1, h2, h3 {{ margin: 0 0 12px; line-height: 1.15; }}
    h1 {{ font-size: 42px; letter-spacing: -0.03em; }}
    h2 {{ font-size: 24px; margin-top: 36px; }}
    h3 {{ font-size: 18px; margin-top: 24px; }}
    p, li {{ font-size: 15px; line-height: 1.6; }}
    .lede {{ max-width: 920px; color: var(--muted); font-size: 17px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 28px; }}
    .chip {{
      padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.75);
      border: 1px solid var(--line); font-size: 13px;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 16px; }}
    .card {{
      background: var(--card); border: 1px solid var(--line); border-radius: 18px;
      padding: 18px 18px 16px; box-shadow: 0 8px 26px rgba(0,0,0,0.03);
    }}
    .k {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
    .v {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
    .s {{ margin-top: 8px; font-size: 13px; color: var(--muted); }}
    .good {{ color: var(--good); }}
    .bad {{ color: var(--bad); }}
    .flat {{ color: var(--flat); }}
    table {{
      width: 100%; border-collapse: collapse; background: var(--card);
      border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
    }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #ece9e2; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ background: #faf7f0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
    tr:last-child td {{ border-bottom: none; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
    .two {{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px; }}
    .foot {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
    ul {{ padding-left: 18px; }}
    @media (max-width: 980px) {{
      .grid, .two {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 32px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>SSA On/Off Performance Report</h1>
    <p class="lede">基于当前分支的 prepared 主网交易 replay，对比 <code>ZEN_ENABLE_EVM_STACK_SSA_LIFT=OFF</code> 与 <code>ON</code> 的冷启动 benchmark。用户目标是 200 条，但当前仓库里实际可直接 replay 的样本只有 <strong>{payload['prepared_count']}</strong> 条，因此本报告严格以这 {payload['prepared_count']} 条为准。</p>
    <div class="chips">
      <div class="chip">Prepared target: {payload['prepared_count']} / {payload['sample_target']}</div>
      <div class="chip">Matched subset: {payload['matched_count']}</div>
      <div class="chip">Mismatches: {payload['mismatch_count']}</div>
      <div class="chip">Verifier errors: OFF {payload['verifier_off']} / ON {payload['verifier_on']}</div>
      <div class="chip"><code>{html.escape(str(benchmark_off))}</code></div>
      <div class="chip"><code>{html.escape(str(benchmark_on))}</code></div>
    </div>

    <h2>Executive Summary</h2>
    <div class="grid">
      <div class="card">
        <div class="k">All 175 Wall</div>
        <div class="v">{fmt_ms(overall_all['on_wall_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall_all['off_wall_mean_ms'])} / delta <span class="{'bad' if (overall_all['wall_delta_pct'] or 0) > 0 else 'good'}">{fmt_pct(overall_all['wall_delta_pct'])}</span></div>
      </div>
      <div class="card">
        <div class="k">All 175 JIT</div>
        <div class="v">{fmt_ms(overall_all['on_jit_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall_all['off_jit_mean_ms'])} / delta <span class="{'good' if (overall_all['jit_delta_pct'] or 0) < 0 else 'bad'}">{fmt_pct(overall_all['jit_delta_pct'])}</span></div>
      </div>
      <div class="card">
        <div class="k">Matched 171 Wall</div>
        <div class="v">{fmt_ms(overall_matched['on_wall_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall_matched['off_wall_mean_ms'])} / delta <span class="{'bad' if (overall_matched['wall_delta_pct'] or 0) > 0 else 'good'}">{fmt_pct(overall_matched['wall_delta_pct'])}</span></div>
      </div>
      <div class="card">
        <div class="k">Matched 171 JIT</div>
        <div class="v">{fmt_ms(overall_matched['on_jit_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall_matched['off_jit_mean_ms'])} / delta <span class="{'bad' if (overall_matched['jit_delta_pct'] or 0) > 0 else 'good'}">{fmt_pct(overall_matched['jit_delta_pct'])}</span></div>
      </div>
    </div>
    <p>一句话结论：<strong>SSA=ON 在 175 条 prepared replay 上还不是完全正确</strong>，因为仍有 4 条返回码从 OFF 基线分叉为 <code>-6</code>。如果只看行为一致的 171 条，SSA=ON 的平均冷启动 wall 基本持平（<strong>{fmt_pct(overall_matched['wall_delta_pct'])}</strong>），JIT compilation 反而略慢（<strong>{fmt_pct(overall_matched['jit_delta_pct'])}</strong>）。</p>

    <h2>Correctness Gate</h2>
    <p>这 4 条分叉样本说明当前 175 条全集上，SSA=ON 还不能被解释成单纯性能开关：</p>
    {render_table(['Dataset', 'Tx Hash', 'OFF RC', 'ON RC', 'OFF Wall', 'ON Wall'], mismatch_rows)}

    <h2>Dataset Split On Matched Subset</h2>
    <p>下面的表只统计返回码一致的子集，避免把错误退出误判成“更快”。</p>
    {render_table(['Dataset', 'Matched', 'Mismatches', 'OFF JIT Rows', 'ON JIT Rows', 'Wall Delta', 'JIT Delta', 'Stats Delta'], dataset_rows)}
    <p class="foot">方向解读：负值更好。这里可以清楚看到 <code>uniswap_v3_swap</code> 与 <code>cow_settlement</code> 的 JIT 更像是收益区，而 <code>erc20_transfer</code> / <code>erc4337_bundle</code> 更像是回退区。</p>

    <div class="two">
      <div>
        <h2>Top Wall Regressions</h2>
        {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF Wall', 'ON Wall', 'Delta'], perf_rows(payload['wall_regressions'], 'wall_delta_pct', 'off_wall_ms', 'on_wall_ms'))}
      </div>
      <div>
        <h2>Top Wall Improvements</h2>
        {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF Wall', 'ON Wall', 'Delta'], perf_rows(payload['wall_improvements'], 'wall_delta_pct', 'off_wall_ms', 'on_wall_ms'))}
      </div>
    </div>

    <div class="two">
      <div>
        <h2>Top JIT Regressions</h2>
        {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF JIT', 'ON JIT', 'Delta'], perf_rows(payload['jit_regressions'], 'jit_delta_pct', 'off_jit_ms', 'on_jit_ms'))}
      </div>
      <div>
        <h2>Top JIT Improvements</h2>
        {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF JIT', 'ON JIT', 'Delta'], perf_rows(payload['jit_improvements'], 'jit_delta_pct', 'off_jit_ms', 'on_jit_ms'))}
      </div>
    </div>

    <h2>Cold Benchmark Noise</h2>
    <p>很多最慢样本的 CLI wall 远大于 statistics total。也就是说，这组冷启动 benchmark 里，进程启动、输入装载、状态准备等固定开销远大于一笔 replay 自己的 JIT/instantiation 时间，SSA 信号会被明显稀释。</p>
    {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF Wall', 'OFF Stats', 'OFF Ratio', 'ON Wall', 'ON Stats', 'ON Ratio'], noise_rows)}
    <p class="foot">例如几条最慢的 Uniswap V3 样本，statistics total 只有 1-2 ms，但 CLI wall 已经接近 500-560 ms。这意味着它们并不适合直接拿来判断 SSA 的 steady-state 执行收益。</p>

    <h2>Optimization Directions For SSA=ON</h2>
    <ul>
      {''.join(f'<li>{html.escape(item)}</li>' for item in optimization_points)}
    </ul>

    <h2>Bottom Line</h2>
    <p>如果按 <strong>全量 175 条</strong> 看，SSA=ON 目前还处在“correctness blocker 尚未清零”的阶段，因此全量平均 wall <strong>{fmt_pct(overall_all['wall_delta_pct'])}</strong> 不能直接解读为性能退化或收益。只有切到 <strong>171 条 matched 子集</strong> 后，才得到更接近真实性能的结论：当前 SSA=ON 在这批主网交易上的冷启动收益非常有限，整体几乎持平，且不同 workload 的方向明显分化。</p>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render an HTML report for SSA on/off performance over the 175 prepared replay set."
    )
    parser.add_argument("--benchmark-off", type=Path, required=True)
    parser.add_argument("--benchmark-on", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    off_rows = load_jsonl(args.benchmark_off / "runs.jsonl")
    on_rows = load_jsonl(args.benchmark_on / "runs.jsonl")
    payload = build_payload(off_rows, on_rows)
    report = build_html(payload, args.benchmark_off, args.benchmark_on)
    args.output.write_text(report, encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "prepared_count": payload["prepared_count"],
        "matched_count": payload["matched_count"],
        "mismatch_count": payload["mismatch_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
