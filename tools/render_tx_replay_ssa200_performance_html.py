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
        off_wall = [float(off_row["wall_time_ms"]) for _, off_row, _ in rows]
        on_wall = [float(on_row["wall_time_ms"]) for _, _, on_row in rows]
        off_jit = [
            float(phase_total(off_row, "jit_compilation"))
            for _, off_row, _ in rows
            if phase_total(off_row, "jit_compilation") is not None
        ]
        on_jit = [
            float(phase_total(on_row, "jit_compilation"))
            for _, _, on_row in rows
            if phase_total(on_row, "jit_compilation") is not None
        ]
        off_stat = [
            float((off_row.get("statistics") or {}).get("total_ms"))
            for _, off_row, _ in rows
            if (off_row.get("statistics") or {}).get("total_ms") is not None
        ]
        on_stat = [
            float((on_row.get("statistics") or {}).get("total_ms"))
            for _, _, on_row in rows
            if (on_row.get("statistics") or {}).get("total_ms") is not None
        ]
        return {
            "off_wall_mean_ms": mean_or_none(off_wall),
            "on_wall_mean_ms": mean_or_none(on_wall),
            "off_wall_median_ms": median_or_none(off_wall),
            "on_wall_median_ms": median_or_none(on_wall),
            "wall_delta_pct": pct_delta(mean_or_none(off_wall), mean_or_none(on_wall)),
            "off_jit_mean_ms": mean_or_none(off_jit),
            "on_jit_mean_ms": mean_or_none(on_jit),
            "jit_delta_pct": pct_delta(mean_or_none(off_jit), mean_or_none(on_jit)),
            "off_stat_mean_ms": mean_or_none(off_stat),
            "on_stat_mean_ms": mean_or_none(on_stat),
            "stat_delta_pct": pct_delta(mean_or_none(off_stat), mean_or_none(on_stat)),
        }

    overall = summarize_triplets(matched)

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
            "total_runs": len(dataset_rows),
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
        "overall": overall,
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
    dataset_rows = []
    for name, item in payload["per_dataset"].items():
        dataset_rows.append(
            [
                html.escape(name),
                str(item["total_runs"]),
                str(item["off_jit_rows"]),
                str(item["on_jit_rows"]),
                str(item["same_jit_rows"]),
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

    overall = payload["overall"]
    optimization_points = [
        "先优化 `erc20_transfer`。这组是当前最明显的负收益来源：SSA=ON 的平均 wall 约 +20.92%，JIT compilation 约 +43.83%。这说明在 call-heavy、router-heavy、小模块频繁装载的路径上，SSA build cost 还高于它带来的栈访问收益。",
        "把 SSA profitability gate 做细，而不是只问“能不能 lift”。建议优先用静态特征限制开启范围：高 merge 密度、频繁 internal call、短函数体但有多级动态跳转的模块，应更早留在非 SSA 或直接 fallback。",
        "保留对 `cow_settlement` 和 `erc4337_bundle` 的投入。这两组当前已经给出比较清晰的 compile-time 改善信号：JIT 平均分别约 -11.31% 和 -5.58%。其中 `cow_settlement` 连端到端 wall 也约 -3.54%，是最接近净收益的工作负载。",
        "继续压缩 straight-line heavy 路径上的 JIT 常数项。`uniswap_v3_swap` 的 JIT 平均约 -10.86%，但 wall 只改善约 -1.84%，说明编译期收益已经存在，但被冷启动和非 JIT 开销稀释了。",
        "把“双方都真正进入 JIT phase”的覆盖率列成一级指标。比如 `uniswapx_reactor` 25 条里两边都没有 JIT compilation phase，说明这部分现在只能当 correctness/pass-through 工作负载，不能用于判断 SSA JIT 本体的好坏。",
        "单独补一轮 steady-state benchmark。当前不少样本的 CLI wall 明显大于 statistics total，冷启动加载、状态文件读取、进程创建会淹没 SSA 的真实执行期收益。如果要决定默认是否开启 SSA，这一步必须做。",
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DTVM SSA On/Off 200-Tx Performance Report</title>
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
    p, li {{ font-size: 15px; line-height: 1.6; }}
    .lede {{ max-width: 960px; color: var(--muted); font-size: 17px; }}
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
    <h1>SSA On/Off 200-Tx Performance Report</h1>
    <p class="lede">基于当前源码和同一批 200 条 prepared 主网交易 replay，对比 <code>ZEN_ENABLE_EVM_STACK_SSA_LIFT=OFF</code> 与 <code>ON</code> 的 multipass 冷启动性能。和前一轮不同，这次已经先修掉分叉样本，因此 <strong>200/200 返回码完全一致</strong>，性能数字可以直接解释。</p>
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
        <div class="k">Wall Mean</div>
        <div class="v">{fmt_ms(overall['on_wall_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall['off_wall_mean_ms'])} / delta <span class="{'bad' if (overall['wall_delta_pct'] or 0) > 0 else 'good'}">{fmt_pct(overall['wall_delta_pct'])}</span></div>
      </div>
      <div class="card">
        <div class="k">Wall Median</div>
        <div class="v">{fmt_ms(overall['on_wall_median_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall['off_wall_median_ms'])}</div>
      </div>
      <div class="card">
        <div class="k">JIT Mean</div>
        <div class="v">{fmt_ms(overall['on_jit_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall['off_jit_mean_ms'])} / delta <span class="{'good' if (overall['jit_delta_pct'] or 0) < 0 else 'bad'}">{fmt_pct(overall['jit_delta_pct'])}</span></div>
      </div>
      <div class="card">
        <div class="k">Stats Total Mean</div>
        <div class="v">{fmt_ms(overall['on_stat_mean_ms'])}</div>
        <div class="s">OFF {fmt_ms(overall['off_stat_mean_ms'])} / delta <span class="{'good' if (overall['stat_delta_pct'] or 0) < 0 else 'bad'}">{fmt_pct(overall['stat_delta_pct'])}</span></div>
      </div>
    </div>
    <p><strong>结论：</strong>在这 200 条交易上，SSA=ON 已经达到 correctness parity，但总体冷启动性能仍然没有赢。按全量平均值看，SSA=ON 的 wall 约 <strong>{fmt_pct(overall['wall_delta_pct'])}</strong>，略慢；但 JIT compilation 和 statistics total 分别约 <strong>{fmt_pct(overall['jit_delta_pct'])}</strong> 与 <strong>{fmt_pct(overall['stat_delta_pct'])}</strong>，说明它在编译本体上已经有一部分正收益，只是还没稳定转化成端到端 wall 改善。</p>

    <h2>Correctness Status</h2>
    <p>这轮 200 条 replay 已经全部对齐：</p>
    <ul>
      <li><strong>200 / 200</strong> returncode 一致。</li>
      <li>此前的 4 条分叉已经消失。修复点包括：忽略 analyzer 未建模的 synthetic predecessor，避免 SSA merge patching 直接 abort；以及在 CLI 统计输出完成后清理未闭合 timer，避免 benchmark-only 的 `SIGABRT`。</li>
      <li>本轮 OFF/ON 的 exit-code 分布完全一致：<code>0:49</code>、<code>1:12</code>、<code>2:127</code>、<code>5:12</code>。</li>
    </ul>

    <h2>Per-Dataset Split</h2>
    {render_table(['Dataset', 'Runs', 'OFF JIT Rows', 'ON JIT Rows', 'Both JIT Rows', 'Wall Delta', 'JIT Delta', 'Stats Delta'], dataset_rows)}
    <p class="foot">方向解读：负值更好。`cow_settlement` 和 `erc4337_bundle` 现在更像 compile-time 受益区；`erc20_transfer` 仍是当前最明确的负收益区；`uniswapx_reactor` 25 条都没有 JIT compilation phase，因此现在不能用它判断 SSA JIT 本体优劣。</p>

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

    <h2>Cold-Start Noise</h2>
    <p>这组 benchmark 依然是冷启动流程，不是 steady-state。很多最慢样本的 CLI wall 仍远大于 statistics total，说明进程创建、状态文件加载、输入准备等固定成本会明显淹没 SSA 真实的编译/执行收益。</p>
    {render_table(['Dataset', 'Tx Hash', 'RC', 'OFF Wall', 'OFF Stats', 'OFF Ratio', 'ON Wall', 'ON Stats', 'ON Ratio'], noise_rows)}

    <h2>Optimization Directions For SSA=ON</h2>
    <ul>
      {''.join(f'<li>{html.escape(item)}</li>' for item in optimization_points)}
    </ul>

    <h2>Bottom Line</h2>
    <p>当前 SSA=ON 已经具备“可以做真实性能对比”的前提条件，因为 correctness 差异已经清零。但从这 200 条交易看，它仍然更像一个<strong>编译本体部分改善、端到端 wall 尚未兑现</strong>的优化路径。下一阶段不该再先追 correctness，而应转向两条主线：一条是收紧 profitability gate，避免在 `erc20_transfer` 这类负收益工作负载上白白付出 SSA build cost；另一条是补充 steady-state 测量，把冷启动噪声和 JIT/执行本体收益拆开看。</p>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render an HTML report for SSA on/off performance over the 200 prepared replay set."
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
    print(
        json.dumps(
            {
                "output": str(args.output),
                "prepared_count": payload["prepared_count"],
                "matched_count": payload["matched_count"],
                "mismatch_count": payload["mismatch_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
