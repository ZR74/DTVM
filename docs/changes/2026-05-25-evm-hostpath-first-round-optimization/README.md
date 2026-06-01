# Change: EVM host-path first-round optimization

- **Status**: Implemented
- **Date**: 2026-05-25
- **Tier**: Light

## Overview

Reduce steady-state overhead in the EVM JIT host bridge by optimizing three hot
paths identified from the 200-transaction replay corpus:

- `evmHandleCallInternal`
- `evmGetSLoad` / `evmSetSStore`
- `evmGetCallDataLoad`

The first round focuses on low-risk changes that preserve execution semantics
while reducing repeated copies, allocations, and avoidable host-path work.

## Motivation

The 200-transaction replay report shows DTVM wall time is still dominated by
host-bridge and execution-framework overhead rather than JIT basic-block time.
Representative perf profiles show the hottest runtime symbols are:

- `evmGetCallDataLoad`
- `evmHandleCallInternal`
- `evmGetSLoad`

Memory allocation also remains visible in steady-state profiles, especially
around return-data materialization.

## Impact

- Affected modules: `compiler`, `runtime`
- No intended EVM semantic changes
- No intended gas-accounting changes
- No module spec updates expected unless contracts change during implementation

## Checklist

- [x] Implementation complete
- [ ] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
