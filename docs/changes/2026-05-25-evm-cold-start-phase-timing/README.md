# Change: Add Finer EVM Cold-Start Phase Timing

- **Status**: Implemented
- **Date**: 2026-05-25
- **Tier**: Light

## Overview

Extend DTVM's EVM replay timing to split cold-start cost into finer phases around
state loading, runtime setup, input decoding, message preparation,
pre-execution checks, and post-execution cleanup.

## Motivation

The current `Statistics` output captures runtime-internal phases such as
`Load`, `JIT Compilation`, `Instantiation`, and `Execution`, but the 200-tx
analysis shows a large residual wall-time segment outside those buckets. We
need phase-level visibility for the EVM CLI path so the next optimization
round can target the actual cold-start bottlenecks instead of over-focusing on
JIT compilation alone.

## Impact

- `src/utils/statistics.*`: extend phase definitions and reporting order
- `src/cli/dtvm.cpp`: instrument EVM replay cold-start stages
- `docs/modules/utils/`: update the `Statistics` contract documentation

## Checklist

- [x] Implementation complete
- [ ] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
