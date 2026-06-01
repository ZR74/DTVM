# Change: Add replay benchmark runner for prepared transaction bundles

- **Status**: Implemented
- **Date**: 2026-05-18
- **Tier**: Light

## Overview

Add a small CLI under `tools/` that batch-runs `prepared.json` replay bundles,
collects process-level timing and child CPU usage, parses DTVM statistics logs
when available, and writes machine-readable summaries for before/after replay
benchmark comparisons.

## Motivation

The transaction corpus workflow can already produce replay-ready `state.json` /
bytecode / command bundles, but comparing DTVM changes on those workloads still
requires manual shell loops. We need a repeatable runner that can:

- execute a whole prepared replay tree with fresh processes,
- preserve exit-code distributions for semantically mixed workloads,
- summarize wall-clock and CPU cost by dataset and transaction,
- and capture DTVM phase timings such as JIT compilation and instantiation when
  the current build exposes them.

## Impact

- **Module**: `tools/`
- Adds `tx_replay_benchmark.py` for batch replay baselines.
- Adds focused tests for statistics parsing, mode overrides, and end-to-end
  summary generation on a fake prepared tree.
- Updates the tools module spec to document the runner.

## Checklist

- [x] Implementation complete
- [x] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
