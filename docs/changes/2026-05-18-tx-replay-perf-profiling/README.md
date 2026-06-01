# Change: Add execution-focused replay perf profiler

- **Status**: Implemented
- **Date**: 2026-05-18
- **Tier**: Light

## Overview

Add a replay perf profiler under `tools/` that warms up a prepared EVM replay to
the point just after the initial compile-heavy execution, then attaches Linux
`perf` to the repeated execution-only phase and aggregates BB / host-function
hotspots across a replay corpus.

## Motivation

Prepared replay baselines already tell us wall-clock and DTVM statistics, but
they do not isolate execution hotspots from the large one-time multipass JIT
cost on realistic multi-contract Ethereum transactions. We need a profiler that
can:

- reuse the first execution as warmup,
- attach `perf` only after the compile-heavy phase,
- preserve JIT BB symbol names in generated perf artifacts,
- and summarize execution hotspots across many prepared transactions.

## Impact

- **Module**: `tools/`
- Adds `tx_replay_perf_profile.py` for execution-focused replay profiling.
- Adds focused parser/aggregation tests for perf-script top-frame summaries.
- Updates the tools module spec to document the profiler.

## Checklist

- [x] Implementation complete
- [x] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
