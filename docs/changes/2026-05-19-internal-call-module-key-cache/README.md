# Change: Internal-call module key cache reuse

- **Status**: Implemented
- **Date**: 2026-05-19
- **Tier**: Light

## Overview

Reduce multipass internal-call overhead by reusing loaded EVM modules with a
structured cache key based on `codehash + revision + memory specialization`,
instead of rebuilding a unique address-based module name and re-hashing the
callee code on every nested call.

## Motivation

The 40-transaction replay hotset showed two issues on nested multi-contract
paths:

- internal calls repeatedly spent time in `keccakf1600_bmi`, `toHex`, and
  `ConstStringPool::newSymbol` before even entering execution-heavy logic;
- identical runtime bytecode deployed at multiple addresses could not reuse the
  same compiled module because the temporary module key still included the
  callee address.

This change addresses the first optimization slice without changing call/rollback
semantics.

## Impact

- `src/runtime/runtime.*`: add symbol-based EVM module lookup for cache hits.
- `src/tests/evm_test_host.hpp`: cache internal-call module identities by
  `codehash + revision + specialization`, lazily materialize missing
  `codehash`, and reuse loaded modules across identical callee bytecode.
- `src/tests/evm_interp_tests.cpp`: add regression coverage for same-bytecode
  reuse across multiple addresses.
- `docs/modules/runtime/spec.md`: document the new lookup contract.

## Checklist

- [x] Implementation complete
- [x] Tests added/updated
- [x] Module specs in `docs/modules/` updated (if affected)
- [x] Build and tests pass
