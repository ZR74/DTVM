# Change: Add transaction corpus collection and sampling tooling

- **Status**: Implemented
- **Date**: 2026-05-18
- **Tier**: Light

## Overview

Add a small Python CLI under `tools/` for collecting transaction candidates from
Etherscan, enriching them through JSON-RPC with aggressive local caching, and
sampling compact performance corpora under free-RPC budget constraints. Extend
the workflow with a replay-preparation helper that turns trace-backed rows into
DTVM `state.json` / bytecode / command bundles using ordinary historical RPC.

## Motivation

The repository already contains real-transaction replay datasets, but the
collection flow is not packaged as a reusable tool. For workload analysis and
before/after DTVM performance comparisons, we need a repeatable way to:

- inspect the current local corpus,
- collect more candidates for the five target transaction classes,
- enrich candidates without overspending a free RPC quota,
- derive a small, stratified performance subset for replay and profiling,
- and convert the subset into DTVM-ready replay inputs without depending on a
  paid debug RPC tier for every follow-up run.

## Impact

- **Module**: `tools/`
- Adds a standalone CLI script, a sample config file, and a sample campaign plan
  for the five target transaction classes.
- Adds campaign-analysis outputs so replay-ready rows and stats-only rows are
  separated automatically after collection.
- Adds a replay-preparation helper that parses structLogs, backfills account and
  code data with ordinary historical RPC, and emits DTVM replay bundles.
- Adds focused tests for reporting, budget estimation, stratified sampling, and
  replay preparation.
- Updates the tools and utils module specs to document the helper workflow and
  the persisted `block_hash` state field.

## Checklist

- [x] Implementation complete
- [x] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
