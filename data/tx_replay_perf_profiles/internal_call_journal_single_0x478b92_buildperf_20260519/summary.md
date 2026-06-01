# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build_perf/dtvm`
- Mode override: `multipass`
- Extra executions: `5000`
- Perf frequency: `9999`
- Runs: `1`
- Top-frame samples: `19821`
- Category pct: `{"evm_bb": 1.4934, "evm_host": 3.6022, "keccak": 5.8675, "kernel": 1.6346, "memory": 4.4296, "other": 24.9382, "unknown": 58.0344}`

## Top EVM BBs

- `EVMBB0_JUMPDEST_14524`: `28` samples
- `EVMBB0_SWITCH0_11246`: `23` samples
- `EVMBB0_JUMPDEST_13042`: `20` samples
- `EVMBB0_JUMPDEST_8539`: `18` samples
- `EVMBB0_JUMPDEST_10618`: `15` samples
- `EVMBB0_JUMPDEST_7641`: `10` samples
- `EVMBB0_JUMPDEST_4544`: `10` samples
- `EVMBB0_JUMPDEST_14608`: `9` samples
- `EVMBB0_MAIN_ENTRY_1`: `9` samples
- `EVMBB0_JUMPDEST_11223`: `9` samples
- `EVMBB0_JUMPDEST_12991`: `7` samples
- `EVMBB0_JUMPDEST_11409`: `7` samples
- `EVMBB0_SWITCH0_14608`: `6` samples
- `EVMBB0_JUMPDEST_9586`: `6` samples
- `EVMBB0_JUMPDEST_4410`: `5` samples
- `EVMBB0_JUMPDEST_4167`: `5` samples
- `EVMBB0_SWITCH0_11368`: `5` samples
- `EVMBB0_JUMPDEST_9703`: `5` samples
- `EVMBB0_SWITCH0_11611`: `5` samples
- `EVMBB0_JUMPDEST_13008`: `5` samples

## Top Host Symbols

- `evmGetCallDataLoad`: `274` samples
- `evmHandleCallInternal`: `121` samples
- `evmEmitLog3`: `55` samples
- `evmGetSLoad`: `47` samples
- `evmSetReturn`: `39` samples
- `evmSetRevert`: `22` samples
- `evmSetReturnDataCopy`: `19` samples
- `evmGetExtCodeSize`: `18` samples
- `evmSetCallDataCopy`: `17` samples
- `evmSetSStore`: `16` samples
- `evmHandleStaticCall`: `13` samples
- `evmGetTimestamp`: `10` samples
- `evmGetSelfBalance`: `9` samples
- `evmGetDiv`: `9` samples
- `evmSetCodeCopy`: `9` samples
- `evmExpandMemoryNoGas`: `9` samples
- `evmEmitLog2`: `8` samples
- `evmHandleCall`: `7` samples
- `evmHandleDelegateCall`: `6` samples
- `evmGetChainId`: `4` samples

## Datasets

### cow_settlement

- Top-frame samples: `19821`
- Category pct: `{"evm_bb": 1.4934, "evm_host": 3.6022, "keccak": 5.8675, "kernel": 1.6346, "memory": 4.4296, "other": 24.9382, "unknown": 58.0344}`
- Top BBs: `{"EVMBB0_JUMPDEST_14524": 28, "EVMBB0_SWITCH0_11246": 23, "EVMBB0_JUMPDEST_13042": 20, "EVMBB0_JUMPDEST_8539": 18, "EVMBB0_JUMPDEST_10618": 15, "EVMBB0_JUMPDEST_7641": 10, "EVMBB0_JUMPDEST_4544": 10, "EVMBB0_JUMPDEST_14608": 9, "EVMBB0_MAIN_ENTRY_1": 9, "EVMBB0_JUMPDEST_11223": 9}`
