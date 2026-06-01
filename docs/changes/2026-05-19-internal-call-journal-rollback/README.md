# Change: Internal Call Journal Rollback

- **Status**: Implemented
- **Date**: 2026-05-19
- **Tier**: Light

## Overview

Replace the internal `CALL` path's full host snapshot/restore with a lightweight
journal that records only state mutated during the active nested-call frames.

## Motivation

40-transaction replay profiling showed nested internal calls spending
significant time cloning `accounts`, logs, and selfdestruct records even when
the callee only touches a small subset of state.

## Impact

Affected area:

- `src/tests/evm_test_host.hpp`
- `src/tests/evm_interp_tests.cpp`

Behavioral contract:

- Nested call reverts must still roll back account/storage/log/selfdestruct
  state observed by the existing host snapshot model.
- No runtime module contract changes; `docs/modules/` updates are not required.

## Checklist

- [x] Implementation complete
- [x] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
