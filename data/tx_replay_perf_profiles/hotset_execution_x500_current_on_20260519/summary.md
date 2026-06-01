# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build_perf_ssa/dtvm`
- Mode override: `multipass`
- Extra executions: `500`
- Perf frequency: `9999`
- Runs: `40`
- Top-frame samples: `2749297`
- Category pct: `{"compiler": 8.1962, "evm_bb": 0.008, "evm_host": 86.3794, "keccak": 0.041, "kernel": 1.6582, "memory": 0.3445, "other": 2.1045, "profiling_overhead": 0.0005, "unknown": 1.2677}`

## Top EVM BBs

- `EVMBB0_JUMPDEST_10315`: `15` samples
- `EVMBB0_JUMPDEST_9403`: `9` samples
- `EVMBB0_MAIN_ENTRY_1`: `8` samples
- `EVMBB0_JUMPDEST_13084`: `8` samples
- `EVMBB0_JUMPDEST_12458`: `8` samples
- `EVMBB0_JUMPDEST_9723`: `7` samples
- `EVMBB0_JUMPDEST_10742`: `7` samples
- `EVMBB0_JUMPDEST_1451`: `7` samples
- `EVMBB0_JUMPDEST_8983`: `5` samples
- `EVMBB0_JUMPDEST_7382`: `5` samples
- `EVMBB0_JUMPDEST_10824`: `5` samples
- `EVMBB0_JUMPDEST_12662`: `4` samples
- `EVMBB0_JUMPDEST_36`: `3` samples
- `EVMBB0_JUMPDEST_9685`: `3` samples
- `EVMBB0_JUMPDEST_9698`: `3` samples
- `EVMBB0_JUMPDEST_12086`: `3` samples
- `EVMBB0_JUMPDEST_11309`: `3` samples
- `EVMBB0_JUMPDEST_8136`: `3` samples
- `EVMBB0_JUMPDEST_9379`: `3` samples
- `EVMBB0_JUMPDEST_4108`: `3` samples

## Top Host Symbols

- `EVMMirBuilder::setInsertBlock`: `2054856` samples
- `EVMMirBuilder::registerPhiIncomingBlock`: `101559` samples
- `EVMMirBuilder::getOrCreateIndirectJumpBB`: `80151` samples
- `EVMMirBuilder::resolvePhiIncomingPredecessorBB`: `73420` samples
- `EVMMirBuilder::createIntConstInstruction`: `5732` samples
- `EVMByteCodeVisitor<COMPILER::EVMMirBuilder>::decode`: `3904` samples
- `EVMByteCodeVisitor<COMPILER::EVMMirBuilder>::handleBeginBlock`: `3442` samples
- `SwitchInstruction* COMPILER::MFunction::createInstruction<COMPILER::SwitchInstruction, COMPILER::EVMFrontendContext&, COMPILER::MInstruction*&, COMPILER::MBasicBlock*&, std::vector<std::pair<COMPILER::ConstantInstruction*, COMPILER::MBasicBlock*>, zen::common::MemPoolAllocator<std::pair<COMPILER::ConstantInstruction*, COMPILER::MBasicBlock*>, COMPILER::MonotonicMemPool> >&>`: `3019` samples
- `EVMAnalyzer::collectDynamicJumpSourceBlocksForInfo`: `2582` samples
- `EVMAnalyzer::finalizeEntryShapeMetadata`: `2269` samples
- `EVMAnalyzer::analyzeBlockBody`: `1755` samples
- `EVMMirBuilder::createJumpTable`: `1525` samples
- `EVMMirBuilder::loadVariable`: `1358` samples
- `EVMMirBuilder::protectUnsafeValue`: `1267` samples
- `EVMAnalyzer::buildBlocks`: `1223` samples
- `EVMLiftedStackLifter<COMPILER::EVMMirBuilder>::makeVirtualStackState`: `1122` samples
- `EVMMirBuilder::stackPop`: `933` samples
- `EVMMirBuilder::extractU256Operand`: `917` samples
- `EVMAnalyzer::resolveDynamicJumpTargetEntryDepths`: `865` samples
- `EVMAnalyzer::finalizeDynamicJumpRegionMetadata`: `840` samples

## Datasets

### cow_settlement

- Top-frame samples: `2049475`
- Category pct: `{"compiler": 5.7122, "evm_host": 90.1414, "kernel": 1.868, "memory": 0.2128, "other": 1.2233, "profiling_overhead": 0.0003, "unknown": 0.8418}`
- Top BBs: `{}`

### erc20_transfer

- Top-frame samples: `463280`
- Category pct: `{"compiler": 15.5243, "evm_bb": 0.0056, "evm_host": 75.7466, "keccak": 0.0004, "kernel": 0.9987, "memory": 0.7188, "other": 4.5782, "profiling_overhead": 0.0015, "unknown": 2.4257}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 3, "EVMBB0_SWITCH0_10648": 2, "EVMBB0_JUMPDEST_7500": 2, "EVMBB0_JUMPDEST_3671": 1, "EVMBB0_JUMPDEST_5656": 1, "EVMBB0_JUMPDEST_6270": 1, "EVMBB0_JUMPDEST_11756": 1, "EVMBB0_JUMPDEST_698": 1, "EVMBB0_JUMPDEST_12366": 1, "EVMBB0_JUMPDEST_798": 1}`

### erc4337_bundle

- Top-frame samples: `3102`
- Category pct: `{"evm_bb": 5.4803, "evm_host": 0.8704, "keccak": 34.1715, "kernel": 7.1244, "memory": 3.3849, "other": 27.9497, "unknown": 21.0187}`
- Top BBs: `{"EVMBB0_JUMPDEST_10315": 15, "EVMBB0_JUMPDEST_9403": 9, "EVMBB0_JUMPDEST_13084": 8, "EVMBB0_JUMPDEST_12458": 8, "EVMBB0_JUMPDEST_9723": 7, "EVMBB0_JUMPDEST_10742": 7, "EVMBB0_JUMPDEST_1451": 7, "EVMBB0_MAIN_ENTRY_1": 5, "EVMBB0_JUMPDEST_8983": 5, "EVMBB0_JUMPDEST_7382": 5}`

### uniswap_v3_swap

- Top-frame samples: `233440`
- Category pct: `{"compiler": 15.5697, "evm_bb": 0.0107, "evm_host": 75.5894, "keccak": 0.0274, "kernel": 1.0517, "memory": 0.7175, "other": 4.5879, "unknown": 2.4456}`
- Top BBs: `{"EVMBB0_JUMPDEST_4108": 3, "EVMBB0_JUMPDEST_2146": 3, "EVMBB0_JUMPDEST_3882": 2, "EVMBB0_JUMPDEST_11731": 1, "EVMBB0_JUMPDEST_18394": 1, "EVMBB0_JUMPDEST_12000": 1, "EVMBB0_JUMPDEST_11708": 1, "EVMBB0_SWITCH0_5853": 1, "EVMBB0_JUMPDEST_18512": 1, "EVMBB0_JUMPDEST_34": 1}`
