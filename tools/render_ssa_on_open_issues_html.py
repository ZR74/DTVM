#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_RE = re.compile(r"\[Verifying Error:\d+\]\s*(.*)")


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


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "无"
    return f"{value:.2f} ms"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "无"
    return f"{value:.1f}%"


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(fmean(values))


def load_benchmark_bundle(root: Path) -> dict[str, Any]:
    summary = load_json(root / "summary.json")
    rows = load_jsonl(root / "runs.jsonl")
    verifier_rows = []
    verifier_messages: Counter[str] = Counter()
    for row in rows:
        stderr_tail = str(row.get("stderr_tail") or "")
        messages = [m.group(1).strip() for m in VERIFY_RE.finditer(stderr_tail)]
        if messages:
            verifier_rows.append(
                {
                    "dataset": str(row["dataset"]),
                    "tx_hash": str(row["tx_hash"]).lower(),
                    "returncode": row.get("returncode"),
                    "messages": messages,
                }
            )
            for msg in messages:
                verifier_messages[msg] += 1
    jit_values: list[float] = []
    for row in rows:
        phases = ((row.get("statistics") or {}).get("phases") or {})
        jit = (phases.get("jit_compilation") or {}).get("total_ms")
        if jit is not None:
            jit_values.append(float(jit))
    return {
        "root": root,
        "summary": summary["summary"],
        "rows": rows,
        "verifier_rows": verifier_rows,
        "verifier_messages": verifier_messages,
        "overall_jit_mean_ms": mean_or_none(jit_values),
    }


def load_sample_bundle(root: Path) -> dict[str, Any]:
    rows = load_jsonl(root / "runs.jsonl")
    if not rows:
        raise ValueError(f"no rows found in {root}")
    row = rows[0]
    stderr_tail = str(row.get("stderr_tail") or "")
    return {
        "root": root,
        "row": row,
        "stderr_tail": stderr_tail,
        "messages": [m.group(1).strip() for m in VERIFY_RE.finditer(stderr_tail)],
    }


def build_issue_payload(
    bench_off: dict[str, Any],
    bench_on: dict[str, Any],
    off_spot: dict[str, Any],
    on_phi_sample: dict[str, Any],
    perf_off_sample: dict[str, Any],
    perf_on_stale_sample: dict[str, Any],
    perf_on_fresh_sample: dict[str, Any],
) -> dict[str, Any]:
    off_map = {key_for_row(row): row for row in bench_off["rows"]}
    on_map = {key_for_row(row): row for row in bench_on["rows"]}

    mismatches: list[dict[str, Any]] = []
    non_verifier_mismatches: list[dict[str, Any]] = []
    for key in sorted(off_map.keys() & on_map.keys()):
        off_row = off_map[key]
        on_row = on_map[key]
        if off_row.get("returncode") == on_row.get("returncode"):
            continue
        item = {
            "dataset": key[0],
            "tx_hash": key[1],
            "off": off_row.get("returncode"),
            "on": on_row.get("returncode"),
            "on_verifier": "Verifying Error" in str(on_row.get("stderr_tail") or ""),
            "on_wall_ms": float(on_row["wall_time_ms"]),
            "on_jit_ms": (
                ((on_row.get("statistics") or {}).get("phases") or {})
                .get("jit_compilation", {})
                .get("total_ms")
            ),
        }
        mismatches.append(item)
        if not item["on_verifier"]:
            non_verifier_mismatches.append(item)

    mismatch_by_dataset = Counter(row["dataset"] for row in mismatches)
    verifier_by_dataset = Counter(row["dataset"] for row in bench_on["verifier_rows"])
    non_verifier_mismatch_by_dataset = Counter(
        row["dataset"] for row in non_verifier_mismatches
    )

    verifier_rc0 = [
        row for row in bench_on["verifier_rows"] if row.get("returncode") == 0
    ]
    verifier_nonzero = [
        row for row in bench_on["verifier_rows"] if row.get("returncode") != 0
    ]

    jit_buckets = {
        "gt_1s": [],
        "gt_5s": [],
        "gt_10s": [],
        "gt_30s": [],
    }
    jit_bucket_by_dataset: dict[str, dict[str, int]] = defaultdict(
        lambda: {"gt_1s": 0, "gt_5s": 0, "gt_10s": 0, "gt_30s": 0}
    )
    slowest_rows = []
    for row in bench_on["rows"]:
        phases = ((row.get("statistics") or {}).get("phases") or {})
        jit = (phases.get("jit_compilation") or {}).get("total_ms")
        if jit is not None:
            jit = float(jit)
            if jit > 1000.0:
                jit_buckets["gt_1s"].append(row)
                jit_bucket_by_dataset[row["dataset"]]["gt_1s"] += 1
            if jit > 5000.0:
                jit_buckets["gt_5s"].append(row)
                jit_bucket_by_dataset[row["dataset"]]["gt_5s"] += 1
            if jit > 10000.0:
                jit_buckets["gt_10s"].append(row)
                jit_bucket_by_dataset[row["dataset"]]["gt_10s"] += 1
            if jit > 30000.0:
                jit_buckets["gt_30s"].append(row)
                jit_bucket_by_dataset[row["dataset"]]["gt_30s"] += 1
        slowest_rows.append(
            {
                "dataset": row["dataset"],
                "tx_hash": row["tx_hash"],
                "returncode": row.get("returncode"),
                "wall_time_ms": float(row["wall_time_ms"]),
                "jit_ms": jit,
                "verifier": "Verifying Error" in str(row.get("stderr_tail") or ""),
            }
        )
    slowest_rows.sort(key=lambda row: row["wall_time_ms"], reverse=True)

    off_spot_rows = load_jsonl(off_spot["root"] / "runs.jsonl")
    off_spot_ok = 0
    for row in off_spot_rows:
        key = (row["dataset"], row["tx_hash"])
        if key in off_map and off_map[key].get("returncode") == row.get("returncode"):
            off_spot_ok += 1

    return {
        "bench_off": bench_off,
        "bench_on": bench_on,
        "off_spot": off_spot,
        "on_phi_sample": on_phi_sample,
        "perf_off_sample": perf_off_sample,
        "perf_on_stale_sample": perf_on_stale_sample,
        "perf_on_fresh_sample": perf_on_fresh_sample,
        "mismatches": mismatches,
        "mismatch_by_dataset": mismatch_by_dataset,
        "non_verifier_mismatches": non_verifier_mismatches,
        "non_verifier_mismatch_by_dataset": non_verifier_mismatch_by_dataset,
        "verifier_by_dataset": verifier_by_dataset,
        "verifier_rc0": verifier_rc0,
        "verifier_nonzero": verifier_nonzero,
        "jit_buckets": {key: len(value) for key, value in jit_buckets.items()},
        "jit_bucket_by_dataset": jit_bucket_by_dataset,
        "slowest_rows": slowest_rows[:10],
        "off_spot_ok": off_spot_ok,
    }


def perf_status_label(sample: dict[str, Any]) -> tuple[str, str]:
    rc = sample["row"].get("returncode")
    stderr_tail = sample["stderr_tail"]
    if rc == 0:
        return "ok", "同一条 prepared command 可以正常执行"
    if rc == 109 and "arguments were not expected" in stderr_tail:
        return "bad", "尚未开始执行就触发了 CLI 参数解析失败"
    if rc == -6:
        return "bad", "执行过程中进程直接 abort"
    return "warn", f"出现了未归类的返回码 rc={rc}"


def render_issue_card(
    priority: str,
    title: str,
    impact: str,
    why: str,
    fix_target: str,
) -> str:
    return (
        "<div class='issue-card'>"
        f"<div class='issue-head'><span class='priority'>{html.escape(priority)}</span>"
        f"<h3>{html.escape(title)}</h3></div>"
        f"<p><strong>如何体现：</strong>{html.escape(impact)}</p>"
        f"<p><strong>说明：</strong>{html.escape(why)}</p>"
        f"<p><strong>修复目标：</strong>{html.escape(fix_target)}</p>"
        "</div>"
    )


def render_bar_table(
    rows: list[tuple[str, int]],
    total_per_dataset: int = 10,
    css_class: str = "bar-main",
) -> str:
    if not rows:
        return "<p class='small'>暂无数据</p>"
    out = []
    for name, count in rows:
        width = (count / total_per_dataset) * 100.0
        out.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{html.escape(name)}</div>"
            "<div class='bar-track'>"
            f"<div class='bar {css_class}' style='width:{width:.2f}%'></div>"
            "</div>"
            f"<div class='bar-text'>{count}/{total_per_dataset}</div>"
            "</div>"
        )
    return "".join(out)


def render_html(payload: dict[str, Any]) -> str:
    bench_off = payload["bench_off"]
    bench_on = payload["bench_on"]
    mismatch_rows = payload["mismatches"]
    non_ver_rows = payload["non_verifier_mismatches"]
    verifier_rows = bench_on["verifier_rows"]
    verifier_msg_counts = bench_on["verifier_messages"]
    dominant_verifier = next(iter(verifier_msg_counts.items()), ("无", 0))
    phi_sample_msgs = payload["on_phi_sample"]["messages"]

    mismatch_bars = render_bar_table(
        sorted(payload["mismatch_by_dataset"].items()), css_class="bar-main"
    )
    verifier_bars = render_bar_table(
        sorted(payload["verifier_by_dataset"].items()), css_class="bar-warn"
    )
    non_ver_bars = render_bar_table(
        sorted(payload["non_verifier_mismatch_by_dataset"].items()),
        css_class="bar-bad",
    )

    perf_rows = []
    for label, sample in [
        ("SSA=OFF 的 perf 构建", payload["perf_off_sample"]),
        ("SSA=ON 的 perf 构建（旧目录）", payload["perf_on_stale_sample"]),
        ("SSA=ON 的 perf 构建（fresh 目录）", payload["perf_on_fresh_sample"]),
    ]:
        status, note = perf_status_label(sample)
        status_text = {"ok": "正常", "bad": "失败", "warn": "异常"}.get(status, status)
        perf_rows.append(
            {
                "label": label,
                "status": status,
                "status_text": status_text,
                "note": note,
                "rc": sample["row"].get("returncode"),
                "wall_ms": sample["row"].get("wall_time_ms"),
                "artifact": short_path(sample["root"]),
            }
        )

    issue_cards = [
        render_issue_card(
            "P0",
            "SSA=ON 改变真实交易行为结果",
            f"40 条里有 {len(mismatch_rows)} 条交易的 returncode 与 off 基线不同；ERC-4337 是 8/10，CoW 是 6/10，ERC20 是 5/10，Uniswap V3 也是 5/10。",
            "这说明 SSA 现在不是单纯影响性能，而是在改写真实交易的执行结果。只要这件事没修完，任何 wall time 或 perf 数字都没有解释价值。",
            "目标是让这 40 条 prepared replay 在 SSA=ON 与 off 基线下得到完全一致的 returncode。",
        ),
        render_issue_card(
            "P0",
            "SSA phi 构造 / 修复仍会生成无效 MIR",
            f"当前全量基准回放里有 {len(verifier_rows)} 条 verifier 报错；最主要的报错是“{dominant_verifier[0]}”，一共出现了 {dominant_verifier[1]} 次。抽样还看到了 phi 没有连续放在 block 起始处。",
            "这不是普通日志噪音，而是 MIR 已经不合法。只要 predecessor 集合、incoming 数量和 phi 排布三者对不上，后面的 lowering 和执行结果都不能相信。",
            "优先修复 SSA phi 的 predecessor 统计、phi incoming 修补，以及 block rewrite 之后的 phi 连续性。",
        ),
        render_issue_card(
            "P0",
            "存在 “verifier error 但最终 returncode=0” 的静默成功风险",
            f"{len(payload['verifier_rc0'])} 条交易在 SSA=ON 下出现 verifier error，但最终仍返回 0。",
            "这比直接失败更危险，因为表面上看像是成功执行，实际上中间 IR 已经坏了，后面很容易把错误样本当成有效结果。",
            "在问题修完前，建议把 verifier failure 直接提升成 hard failure，避免坏样本混进成功样本。",
        ),
        render_issue_card(
            "P0",
            "不是所有分叉都能用 verifier error 解释",
            f"24 条分叉里有 {len(non_ver_rows)} 条根本没有 verifier error；其中 ERC-4337 bundle 单独就占了 8 条，而且统一表现为 off=2、on=8。",
            "这说明除了 phi/verifier 这一类 bug 之外，至少还存在第二类独立问题，更像是语义分叉或状态码映射出了问题，已经在 bundle / settlement 路径上稳定复现。",
            "需要把 ERC-4337、CoW、Uniswap 这批没有 verifier error 的分叉单独拿出来排查，优先看 exit-code mapping、异常传播和 fallback/host 交互路径。",
        ),
        render_issue_card(
            "P1",
            "perf-enabled SSA 路径还不可用",
            "同一条 prepared replay 在 SSA=OFF 的 perf 构建上可以执行，但 SSA=ON 的旧 perf 目录会 -6 abort，而新的 fresh perf 目录则会在 10ms 内以 109 直接报 CLI 参数解析失败。",
            "这意味着现在根本拿不到可信的 SSA steady-state hotspot profile；任何 profiling 结论都会先被构建或运行时故障污染。",
            "先让 perf-enabled SSA build 和普通 Release build 都能稳定执行同一条 prepared command，再回到 x500 / x5000 的 execution hotspot profiling。",
        ),
        render_issue_card(
            "P1",
            "部分交易在 SSA=ON 下出现明显 compile-time explosion 症状",
            f"SSA=ON 当前有 {payload['jit_buckets']['gt_5s']} 条交易的 JIT 超过 5 秒，{payload['jit_buckets']['gt_10s']} 条超过 10 秒，{payload['jit_buckets']['gt_30s']} 条超过 30 秒；最坏样本 JIT 到了 151.7 秒。",
            "这还不能直接解释成单纯的性能退化，因为很多样本本身已经分叉或 verifier fail；但它至少说明 SSA 前端和 phi 修复链路在真实交易上会明显放大编译成本。",
            "等正确性问题修完后，优先回看 Uniswap V3 和 ERC20 上的 SSA 前端、CFG 改写、phi 修复以及 JIT suitability 门槛。",
        ),
    ]

    slow_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['dataset'])}</td>"
        f"<td class='mono'>{html.escape(row['tx_hash'][:18])}...</td>"
        f"<td>{row['returncode']}</td>"
        f"<td>{fmt_ms(row['wall_time_ms'])}</td>"
        f"<td>{fmt_ms(row['jit_ms'])}</td>"
        f"<td>{'是' if row['verifier'] else '否'}</td>"
        "</tr>"
        for row in payload["slowest_rows"]
    )

    mismatch_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['dataset'])}</td>"
        f"<td class='mono'>{html.escape(row['tx_hash'][:18])}...</td>"
        f"<td>{row['off']}</td>"
        f"<td>{row['on']}</td>"
        f"<td>{'是' if row['on_verifier'] else '否'}</td>"
        "</tr>"
        for row in mismatch_rows[:14]
    )

    non_ver_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['dataset'])}</td>"
        f"<td class='mono'>{html.escape(row['tx_hash'][:18])}...</td>"
        f"<td>{row['off']}</td>"
        f"<td>{row['on']}</td>"
        f"<td>{fmt_ms(row['on_jit_ms'])}</td>"
        "</tr>"
        for row in non_ver_rows[:12]
    )

    perf_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['label'])}</td>"
        f"<td><span class='chip {row['status']}'>{row['status_text']}</span></td>"
        f"<td>{row['rc']}</td>"
        f"<td>{fmt_ms(row['wall_ms'])}</td>"
        f"<td class='mono'>{html.escape(row['artifact'])}</td>"
        f"<td>{html.escape(row['note'])}</td>"
        "</tr>"
        for row in perf_rows
    )

    jit_bucket_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(ds)}</td>"
        f"<td>{vals['gt_1s']}</td>"
        f"<td>{vals['gt_5s']}</td>"
        f"<td>{vals['gt_10s']}</td>"
        f"<td>{vals['gt_30s']}</td>"
        "</tr>"
        for ds, vals in sorted(payload["jit_bucket_by_dataset"].items())
    )

    phi_sample_html = "".join(
        f"<li class='mono'>{html.escape(msg)}</li>" for msg in phi_sample_msgs[:4]
    )

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>DTVM SSA 开启后的待修复问题 - 2026-05-19</title>
    <style>
      :root {{
        --bg: #f3ede4;
        --paper: #fffdf9;
        --ink: #1d1c19;
        --muted: #6d665c;
        --line: #ddd1c1;
        --p0: #b42318;
        --p1: #9a6700;
        --good: #16794a;
        --warn: #a36a00;
        --bad: #b42318;
        --blue: #2d6a9f;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        font-family: "Baskerville", "Iowan Old Style", "Palatino Linotype", serif;
        background:
          radial-gradient(circle at top right, #eee1cf 0, transparent 26rem),
          linear-gradient(180deg, #f6f1e8, #ece4d8 100%);
      }}
      .page {{
        max-width: 1260px;
        margin: 0 auto;
        padding: 32px 20px 80px;
      }}
      .hero {{
        display: grid;
        grid-template-columns: 1.7fr 1fr;
        gap: 18px;
        margin-bottom: 18px;
      }}
      .panel {{
        background: rgba(255, 253, 249, 0.92);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px 22px;
        box-shadow: 0 10px 28px rgba(31, 24, 16, 0.06);
      }}
      h1, h2, h3 {{ margin: 0 0 12px; }}
      h1 {{ font-size: 42px; line-height: 1.05; }}
      h2 {{ font-size: 22px; }}
      h3 {{ font-size: 18px; }}
      p {{ margin: 0 0 12px; line-height: 1.56; }}
      ul {{ margin: 0; padding-left: 18px; line-height: 1.56; }}
      li + li {{ margin-top: 6px; }}
      .lede {{
        font-size: 18px;
        color: var(--muted);
        max-width: 52rem;
      }}
      .callout {{
        background: #fff1ef;
        border-left: 6px solid var(--p0);
        border-radius: 12px;
        padding: 14px 16px;
      }}
      .metrics {{
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0;
      }}
      .metric {{
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 15px 16px;
      }}
      .metric .k {{
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .metric .v {{
        margin-top: 8px;
        font-size: 30px;
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
      .grid3 {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 18px;
        margin-bottom: 18px;
      }}
      .issues {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
        margin-bottom: 18px;
      }}
      .issue-card {{
        background: #fffdfa;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px 18px 14px;
      }}
      .issue-head {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
      }}
      .priority {{
        display: inline-flex;
        min-width: 42px;
        height: 28px;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        background: #fff1ef;
        color: var(--p0);
      }}
      .bar-row {{
        display: grid;
        grid-template-columns: 120px 1fr 56px;
        gap: 10px;
        align-items: center;
      }}
      .bar-row + .bar-row {{ margin-top: 12px; }}
      .bar-label {{ font-size: 14px; }}
      .bar-track {{
        height: 14px;
        background: #eee5d8;
        border-radius: 999px;
        overflow: hidden;
      }}
      .bar {{
        height: 100%;
        border-radius: 999px;
      }}
      .bar-main {{ background: var(--p0); }}
      .bar-warn {{ background: var(--p1); }}
      .bar-bad {{ background: var(--blue); }}
      .bar-text {{ color: var(--muted); font-size: 13px; }}
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
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      .chip {{
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
      }}
      .chip.ok {{ background: #e8f7ee; color: var(--good); }}
      .chip.warn {{ background: #fff3d8; color: var(--warn); }}
      .chip.bad {{ background: #fde7e3; color: var(--bad); }}
      .small {{ color: var(--muted); font-size: 14px; }}
      .mono {{
        font-family: "SFMono-Regular", ui-monospace, "Cascadia Code", "Liberation Mono", monospace;
      }}
      .foot {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
      code {{
        font-family: "SFMono-Regular", ui-monospace, "Cascadia Code", "Liberation Mono", monospace;
        background: #f2ece3;
        border-radius: 6px;
        padding: 2px 4px;
      }}
      @media (max-width: 980px) {{
        .hero, .grid2, .grid3, .issues, .metrics {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 34px; }}
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <div class="panel">
          <h1>SSA=ON 待修复问题</h1>
          <p class="lede">这份报告只回答一个问题：在当前 DTVM 上，<code>ZEN_ENABLE_EVM_STACK_SSA_LIFT=ON</code> 还存在哪些明确待修复的问题，它们在 40 条真实主网交易 replay 上如何体现。</p>
          <div class="callout">
            <p><strong>一句话结论：</strong>SSA=ON 当前至少同时存在两类 P0 问题：一类是 <strong>phi / verifier 相关的无效 MIR</strong>，另一类是 <strong>没有 verifier error 但仍然发生的语义或状态码分叉</strong>。在这两类问题清零之前，SSA 还不能被视为可上线的性能优化项。</p>
          </div>
        </div>
        <div class="panel">
          <h2>证据边界</h2>
          <ul>
            <li>off 基线：<code>{html.escape(short_path(bench_off['root']))}</code> 的 40 条全量基准回放。</li>
            <li>off 当前 spot-check：6 条高风险交易，<strong>{payload['off_spot_ok']}/6</strong> 与历史 off 返回码一致。</li>
            <li>on 当前全量：<code>{html.escape(short_path(bench_on['root']))}</code> 的 40 条全量基准回放。</li>
            <li>额外抽样：<code>{html.escape(short_path(payload['on_phi_sample']['root']))}</code> 提供了 phi 连续性问题的直接日志证据。</li>
          </ul>
        </div>
      </section>

      <section class="metrics">
        <div class="metric">
          <div class="k">返回码分叉</div>
          <div class="v">{len(mismatch_rows)} / 40</div>
          <div class="s">SSA=ON 与 off 基线的行为不一致</div>
        </div>
        <div class="metric">
          <div class="k">Verifier 报错</div>
          <div class="v">{len(verifier_rows)} / 40</div>
          <div class="s">当前 SSA=ON 基准回放命中了 verifier</div>
        </div>
        <div class="metric">
          <div class="k">非 verifier 分叉</div>
          <div class="v">{len(non_ver_rows)} / 40</div>
          <div class="s">不是 verifier 报错导致的分叉</div>
        </div>
        <div class="metric">
          <div class="k">报错但返回 0</div>
          <div class="v">{len(payload['verifier_rc0'])} / 40</div>
          <div class="s">存在静默成功风险</div>
        </div>
        <div class="metric">
          <div class="k">可用的 perf SSA</div>
          <div class="v">0 / 2</div>
          <div class="s">perf-enabled SSA 样本目前不可用</div>
        </div>
      </section>

      <section class="issues">
        {''.join(issue_cards)}
      </section>

      <section class="grid3">
        <div class="panel">
          <h2>按数据集看分叉</h2>
          {mismatch_bars}
          <p class="foot">ERC-4337 bundle 的 8/10 分叉最整齐，说明这类问题不是随机波动，而是稳定路径问题。</p>
        </div>
        <div class="panel">
          <h2>按数据集看 verifier</h2>
          {verifier_bars}
          <p class="foot">verifier 问题集中在 CoW / ERC20 / Uniswap V3。ERC-4337 没有 verifier error，但仍大量分叉。</p>
        </div>
        <div class="panel">
          <h2>按数据集看非 verifier 分叉</h2>
          {non_ver_bars}
          <p class="foot">这部分是第二类独立 bug 的直接证据，尤其是 ERC-4337 统一从 off=2 变成 on=8。</p>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Verifier 直接证据</h2>
          <p><strong>全量里最主要的错误：</strong><code>{html.escape(dominant_verifier[0])}</code>，在当前 40 条基准回放里一共出现了 {dominant_verifier[1]} 次。</p>
          <p><strong>抽样补充证据：</strong>除了 incoming count 不匹配之外，还观测到了 phi 排布错误：</p>
          <ul>
            {phi_sample_html}
          </ul>
          <p class="foot">这说明 SSA phi 的问题不是单点报错，而是至少覆盖 incoming count 和 block-start contiguity 两个层面。</p>
        </div>

        <div class="panel">
          <h2>静默成功风险</h2>
          <p>以下交易在 SSA=ON 下出现了 verifier error，但最终仍然给出了 <code>returncode=0</code>：</p>
          <table>
            <thead><tr><th>数据集</th><th>交易哈希</th></tr></thead>
            <tbody>
              {"".join(f"<tr><td>{html.escape(row['dataset'])}</td><td class='mono'>{html.escape(row['tx_hash'])}</td></tr>" for row in payload['verifier_rc0'])}
            </tbody>
          </table>
          <p class="foot">这类样本最危险，因为如果只看 returncode，会被误判成“成功执行”。</p>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>代表性分叉样本</h2>
          <table>
            <thead>
              <tr><th>数据集</th><th>交易哈希</th><th>OFF</th><th>ON</th><th>ON 是否 verifier</th></tr>
            </thead>
            <tbody>
              {mismatch_rows_html}
            </tbody>
          </table>
        </div>

        <div class="panel">
          <h2>纯非 verifier 分叉样本</h2>
          <table>
            <thead>
              <tr><th>数据集</th><th>交易哈希</th><th>OFF</th><th>ON</th><th>ON 的 JIT</th></tr>
            </thead>
            <tbody>
              {non_ver_rows_html}
            </tbody>
          </table>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>编译期开销症状</h2>
          <table>
            <thead>
              <tr><th>数据集</th><th>JIT &gt;1s</th><th>&gt;5s</th><th>&gt;10s</th><th>&gt;30s</th></tr>
            </thead>
            <tbody>
              {jit_bucket_rows_html}
            </tbody>
          </table>
          <p class="foot">当前 SSA=ON 有 {payload['jit_buckets']['gt_1s']} 条交易的 JIT 超过 1 秒，{payload['jit_buckets']['gt_30s']} 条超过 30 秒，最重集中在 Uniswap V3。</p>
        </div>

        <div class="panel">
          <h2>最慢 10 条当前 SSA=ON 样本</h2>
          <table>
            <thead>
              <tr><th>数据集</th><th>交易哈希</th><th>返回码</th><th>总耗时</th><th>JIT</th><th>是否 verifier</th></tr>
            </thead>
            <tbody>
              {slow_rows_html}
            </tbody>
          </table>
        </div>
      </section>

      <section class="grid2">
        <div class="panel">
          <h2>Perf 路径现状</h2>
          <table>
            <thead>
              <tr><th>构建</th><th>状态</th><th>返回码</th><th>耗时</th><th>工件路径</th><th>含义</th></tr>
            </thead>
            <tbody>
              {perf_rows_html}
            </tbody>
          </table>
        </div>

        <div class="panel">
          <h2>修复优先顺序</h2>
          <ol>
            <li>先把 SSA phi/verifier 问题清零，特别是 predecessor/incoming count 与 phi contiguity。</li>
            <li>然后单独排查非 verifier 分叉，优先 ERC-4337 bundle 的 <code>2 -&gt; 8</code> 稳定分叉。</li>
            <li>把 verifier error 直接变成 hard failure，避免坏样本混进成功结果。</li>
            <li>修 perf-enabled SSA build，让相同 prepared command 在 on/off perf build 都可跑通。</li>
            <li>最后才重新做 SSA on/off 的性能和 hotspot profiling 对比。</li>
          </ol>
        </div>
      </section>

      <section class="panel">
        <h2>工件路径</h2>
        <ul class="mono">
          <li>{html.escape(short_path(bench_off['root']))}</li>
          <li>{html.escape(short_path(bench_on['root']))}</li>
          <li>{html.escape(short_path(payload['off_spot']['root']))}</li>
          <li>{html.escape(short_path(payload['on_phi_sample']['root']))}</li>
          <li>{html.escape(short_path(payload['perf_off_sample']['root']))}</li>
          <li>{html.escape(short_path(payload['perf_on_stale_sample']['root']))}</li>
          <li>{html.escape(short_path(payload['perf_on_fresh_sample']['root']))}</li>
        </ul>
      </section>
    </div>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render focused Chinese HTML for current SSA=ON open issues."
    )
    parser.add_argument("--benchmark-off", required=True)
    parser.add_argument("--benchmark-on", required=True)
    parser.add_argument("--off-spotcheck", required=True)
    parser.add_argument("--on-phi-sample", required=True)
    parser.add_argument("--perf-off-sample", required=True)
    parser.add_argument("--perf-on-stale-sample", required=True)
    parser.add_argument("--perf-on-fresh-sample", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bench_off = load_benchmark_bundle(Path(args.benchmark_off))
    bench_on = load_benchmark_bundle(Path(args.benchmark_on))
    off_spot = load_sample_bundle(Path(args.off_spotcheck))
    on_phi_sample = load_sample_bundle(Path(args.on_phi_sample))
    perf_off_sample = load_sample_bundle(Path(args.perf_off_sample))
    perf_on_stale_sample = load_sample_bundle(Path(args.perf_on_stale_sample))
    perf_on_fresh_sample = load_sample_bundle(Path(args.perf_on_fresh_sample))

    payload = build_issue_payload(
        bench_off=bench_off,
        bench_on=bench_on,
        off_spot=off_spot,
        on_phi_sample=on_phi_sample,
        perf_off_sample=perf_off_sample,
        perf_on_stale_sample=perf_on_stale_sample,
        perf_on_fresh_sample=perf_on_fresh_sample,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(payload), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
