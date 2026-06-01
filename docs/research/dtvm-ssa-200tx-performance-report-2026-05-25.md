# DTVM 200 Transaction Performance Report

- Date: `2026-05-25`
- Scope: prepared replay corpus with `200` transactions
- Focus: DTVM multipass replay cost, SSA on/off comparison, and hotspot-based optimization priorities

## Executive Summary

The current DTVM replay path remains bottlenecked by host-path and per-run
framework overhead rather than JIT basic-block execution.

On the 200-transaction corpus:

- `ssa200_off` mean wall time: `59.99 ms`
- `ssa200_on` mean wall time: `59.95 ms`
- `evmone` mean wall time: `15.20 ms`

Relative to `evmone`, DTVM is slower by about `3.95x` overall. The largest gaps
are in:

- `erc20_transfer`: `5.75x`
- `uniswap_v3_swap`: `4.98x`

SSA-on reduces some compilation-time counters in representative builds, but it
does not yet translate into material end-to-end replay improvement on this
corpus.

## Data Sources

Primary benchmark summaries:

- `data/tx_replay_benchmarks/ssa200_off_20260525/summary.json`
- `data/tx_replay_benchmarks/ssa200_on_20260525/summary.json`
- `data/tx_replay_benchmarks/ssa200_evmone_20260525/summary.json`

Representative perf profiles used for hotspot attribution:

- `data/tx_replay_perf_profiles/hotset_execution_x5000_current_off_20260519/summary.json`
- `data/tx_replay_perf_profiles/hotset_execution_x500_current_on_20260519/summary.json`

Note: the `ssa200_rep_off_20260525` and `ssa200_rep_on_20260525` perf runs did
not capture usable top-frame samples, so hotspot attribution relies on the
effective `2026-05-19` hotset profiles.

## Method

This analysis uses two layers of evidence:

1. Corpus-wide replay summaries for 200 prepared transactions
2. Representative steady-state perf samples for hotspot attribution

The benchmark summaries capture end-to-end process wall time, CPU time, replay
exit code distribution, and internal statistics timers. The perf profiles
capture where execution time concentrates inside the JIT host bridge and
supporting runtime code.

## Corpus Overview

Datasets:

- `cow_settlement`: `25`
- `erc20_transfer`: `50`
- `erc4337_bundle`: `50`
- `uniswap_v3_swap`: `50`
- `uniswapx_reactor`: `25`

Exit-code distribution in DTVM indicates many failing or early-exit cases are
still included in the corpus. This matters because end-to-end replay cost is
not just “successful VM execution”; failure handling and process setup also
contribute materially to wall time.

## End-to-End Replay Results

### Overall

| Runner | Mean wall | Median wall | P95 wall |
|---|---:|---:|---:|
| `ssa200_off` | `59.99 ms` | `33.63 ms` | `196.38 ms` |
| `ssa200_on` | `59.95 ms` | `32.56 ms` | `215.87 ms` |
| `evmone` | `15.20 ms` | `13.01 ms` | n/a |

Overall delta:

- `ssa_on` vs `ssa_off`: `-0.07%` wall time
- `ssa_on` vs `ssa_off`: `-4.15%` user CPU
- `ssa_on` vs `ssa_off`: `-5.78%` system CPU

Interpretation: current SSA-on changes are not the primary lever for the 200
transaction replay path.

### Per Dataset

| Dataset | DTVM off mean | DTVM on mean | evmone mean | Off / evmone |
|---|---:|---:|---:|---:|
| `cow_settlement` | `40.79 ms` | `35.42 ms` | `19.94 ms` | `2.05x` |
| `erc20_transfer` | `84.44 ms` | `87.01 ms` | `14.68 ms` | `5.75x` |
| `erc4337_bundle` | `32.85 ms` | `32.96 ms` | `11.67 ms` | `2.81x` |
| `uniswap_v3_swap` | `91.79 ms` | `90.71 ms` | `18.44 ms` | `4.98x` |
| `uniswapx_reactor` | `20.96 ms` | `22.79 ms` | `12.10 ms` | `1.73x` |

Priority candidates from a performance perspective:

1. `uniswap_v3_swap`
2. `erc20_transfer`
3. `erc4337_bundle`

## Why Wall Time Is Still High

Internal timers are much smaller than wall time. Examples from `ssa200_off`:

- `erc20_transfer`: statistics mean `6.64 ms`, wall mean `84.44 ms`
- `uniswap_v3_swap`: statistics mean `2.12 ms`, wall mean `91.79 ms`
- `erc4337_bundle`: statistics mean `1.93 ms`, wall mean `32.85 ms`

This strongly suggests that single-process VM execution is not the only cost.
The replay path is also paying for:

- process startup and teardown
- prepared input/state loading
- JSON parsing / object setup
- host bridge overhead
- failure-path handling

As a result, pure JIT codegen improvements alone cannot close the current gap.

## Representative Hotspots

### Steady-State Multipass, Current Off Build

Representative steady-state profile:

- `hotset_execution_x5000_current_off_20260519`
- runs: `40`
- top-frame samples: `185589`

Category split:

- `evm_host`: `3.09%`
- `keccak`: `7.26%`
- `memory`: `4.97%`
- `other`: `29.78%`
- `unknown`: `49.04%`

Top host symbols:

- `evmGetCallDataLoad`
- `evmHandleCallInternal`
- `evmGetSLoad`
- `evmGetMulMod`
- `evmEmitLog3`
- `evmSetReturn`
- `evmSetSStore`

Top keccak symbols:

- `keccakf1600_bmi`
- `evmGetKeccak256`
- `ethash_keccak256`

Interpretation:

- The hottest visible runtime work sits in the JIT host bridge, not in a small
  set of JIT basic blocks.
- `CALLDATALOAD`, internal call handling, and storage access are the main
  runtime optimization candidates.
- `keccak` remains significant for hash-heavy workloads.
- allocation and buffer churn are still observable.

### Dataset-Specific Hotspot Shape

`erc4337_bundle`:

- keccak-heavy
- representative keccak share: about `29.98%`

`erc20_transfer` and `uniswap_v3_swap`:

- stronger concentration in host-path calls
- repeated calldata loads
- repeated internal call handling
- repeated storage access

## SSA-On Representative Build Findings

Representative SSA-on perf profile:

- `hotset_execution_x500_current_on_20260519`
- top-frame samples: `2749297`

Top symbols are dominated by MIR/CFG build work:

- `EVMMirBuilder::setInsertBlock`
- `EVMMirBuilder::registerPhiIncomingBlock`
- `EVMMirBuilder::getOrCreateIndirectJumpBB`
- `EVMMirBuilder::resolvePhiIncomingPredecessorBB`

Interpretation:

- SSA-on reduces some compilation metrics, but the compiler frontend still
  carries heavy graph-construction cost.
- This is a real optimization target, but it is not the first explanation for
  poor 200-transaction end-to-end wall time.

## Slowest Transactions

The slowest replay cases are still concentrated in:

- `uniswap_v3_swap`
- `erc20_transfer`

Representative worst cases exceed `300 ms` and the slowest exceed `490 ms` to
`574 ms`. Some of these include no reported JIT compilation time, which further
supports the conclusion that framework and host-path overhead remain dominant in
the replay pipeline.

## Bottleneck Ranking

1. Per-transaction replay framework cost is too high.
2. JIT host-path runtime overhead is concentrated in calldata, call, and
   storage helpers.
3. `erc4337_bundle` remains hash-heavy and exposes keccak cost.
4. Allocation and return-data materialization are still visible.
5. SSA frontend CFG/phi management remains expensive but is not the first lever
   for end-to-end replay speed.

## Optimization Directions

### Priority 1: Reduce Single-Replay Framework Overhead

- Move from one-process-per-transaction replay to batched replay when possible.
- Reuse prepared state objects or adopt cheaper load formats than JSON for hot
  replay loops.
- Separate failing corpus cases from successful steady-state throughput cases.

### Priority 2: Reduce JIT Host-Path Overhead

- Optimize `evmGetCallDataLoad` to avoid copies on full 32-byte windows.
- Reduce return-data allocation churn in `evmHandleCallInternal`,
  `evmSetReturn`, and `evmSetRevert`.
- Reduce repeated storage fetch overhead in `evmGetSLoad`, while keeping
  warming and mutation semantics correct.
- Review `evmHandleCallInternal` for avoidable balance/account/object work on
  common fast paths.

### Priority 3: Reduce Keccak Pressure

- Focus first on reducing repeated hash invocations before attempting lower-level
  hash implementation work.
- Check for repeated hashing of identical short regions and repeated memory
  window formation.

### Priority 4: Reduce SSA Frontend Cost

- Reduce `setInsertBlock` churn.
- Reduce phi incoming bookkeeping pressure.
- Revisit dynamic jump block creation and predecessor resolution.

## Recommended Immediate Work

The first implementation round should target:

1. `evmGetCallDataLoad`
2. `evmHandleCallInternal`
3. `evmGetSLoad` / `evmSetSStore`

This is the best balance between:

- visible hotspot relevance
- low semantic risk
- likely measurable improvement
- limited change surface

## Conclusion

The 200-transaction corpus does not currently point to “JIT BB execution” as
the main bottleneck. The larger issue is the combination of replay framework
cost and JIT host-bridge overhead. The most actionable first-round path is to
reduce repeated copies, allocations, and redundant host-path work in the
calldata, internal-call, and storage helpers.
