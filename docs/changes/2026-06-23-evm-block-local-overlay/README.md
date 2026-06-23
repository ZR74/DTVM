# EVM SSA-off Block-local Runtime Stack Overlay

## Status

Implemented.

## Tier

Light.

## Motivation

When EVM stack SSA lifting is disabled, JIT compilation should not depend on
lifted entry-stack materialization to prove that block entry state can be
transferred safely. The non-lifted path can use the real EVM runtime stack as
the semantic boundary, but writing every stack operation directly to the runtime
stack creates unnecessary load/store and temporary-value pressure.

## Change

- Add a block-local runtime-stack overlay in the EVM bytecode visitor when
  `ZEN_ENABLE_EVM_STACK_SSA_LIFT` is disabled.
- Lazy-load stack entries from the runtime stack only when a block needs them.
- Keep block-local pushes, pops, DUPs, and SWAPs in the overlay.
- Flush the overlay at block exits and runtime-visible helper, memory, host, and
  dynamic-control-flow boundaries.
- Keep dynamic/deep-entry module-level fallback gates active only for the stack
  SSA lift path; SSA-off still respects normal JIT suitability thresholds.

## Validation

- `evmJitFrontendTests` covers the overlay access pattern and analyzer
  materializability metadata.
