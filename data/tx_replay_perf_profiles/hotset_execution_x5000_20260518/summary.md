# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build_perf/dtvm`
- Mode override: `multipass`
- Extra executions: `5000`
- Perf frequency: `9999`
- Runs: `40`
- Top-frame samples: `840412`
- Category pct: `{"evm_bb": 0.3162, "evm_host": 0.7755, "keccak": 54.9759, "kernel": 1.558, "memory": 2.8373, "other": 10.9907, "unknown": 28.5465}`

## Top EVM BBs

- `EVMBB0_MAIN_ENTRY_1`: `126` samples
- `EVMBB0_JUMPDEST_5225`: `32` samples
- `EVMBB0_JUMPDEST_10422`: `31` samples
- `EVMBB0_JUMPDEST_2146`: `30` samples
- `EVMBB0_JUMPDEST_10361`: `29` samples
- `EVMBB0_JUMPDEST_3620`: `28` samples
- `EVMBB0_JUMPDEST_8136`: `24` samples
- `EVMBB0_JUMPDEST_16234`: `23` samples
- `EVMBB0_JUMPDEST_3882`: `23` samples
- `EVMBB0_JUMPDEST_8539`: `22` samples
- `EVMBB0_JUMPDEST_18336`: `22` samples
- `EVMBB0_JUMPDEST_10438`: `22` samples
- `EVMBB0_JUMPDEST_2018`: `22` samples
- `EVMBB0_JUMPDEST_8671`: `21` samples
- `EVMBB0_JUMPDEST_10331`: `21` samples
- `EVMBB0_JUMPDEST_16`: `20` samples
- `EVMBB0_JUMPDEST_5362`: `20` samples
- `EVMBB0_JUMPDEST_7641`: `19` samples
- `EVMBB0_JUMPDEST_14524`: `19` samples
- `EVMBB0_JUMPDEST_10347`: `19` samples

## Top Host Symbols

- `evmGetCallDataLoad`: `1613` samples
- `evmHandleCallInternal`: `1340` samples
- `evmGetSLoad`: `697` samples
- `evmGetMulMod`: `449` samples
- `evmSetReturn`: `398` samples
- `evmEmitLog3`: `395` samples
- `evmSetSStore`: `249` samples
- `evmEmitLog2`: `166` samples
- `evmSetCallDataCopy`: `117` samples
- `evmSetRevert`: `115` samples
- `evmExpandMemoryNoGas`: `100` samples
- `evmSetReturnDataCopy`: `100` samples
- `evmHandleCall`: `88` samples
- `evmGetExtCodeSize`: `84` samples
- `evmGetDiv`: `79` samples
- `evmSetCodeCopy`: `70` samples
- `evmGetSDiv`: `69` samples
- `evmHandleStaticCall`: `64` samples
- `evmHandleDelegateCall`: `45` samples
- `evmGetTimestamp`: `43` samples

## Datasets

### cow_settlement

- Top-frame samples: `187883`
- Category pct: `{"evm_bb": 0.281, "evm_host": 0.793, "keccak": 43.7182, "kernel": 1.6441, "memory": 3.5863, "other": 12.5866, "unknown": 37.3908}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 33, "EVMBB0_JUMPDEST_8539": 22, "EVMBB0_JUMPDEST_18336": 22, "EVMBB0_JUMPDEST_8671": 21, "EVMBB0_JUMPDEST_7641": 19, "EVMBB0_JUMPDEST_14524": 19, "EVMBB0_JUMPDEST_13042": 17, "EVMBB0_SWITCH0_11246": 15, "EVMBB0_JUMPDEST_10618": 13, "EVMBB0_JUMPDEST_4410": 12}`

### erc20_transfer

- Top-frame samples: `254560`
- Category pct: `{"evm_bb": 0.319, "evm_host": 0.7248, "keccak": 53.5555, "kernel": 1.7497, "memory": 2.8979, "other": 11.4496, "unknown": 29.3035}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 34, "EVMBB0_JUMPDEST_5225": 32, "EVMBB0_JUMPDEST_10422": 31, "EVMBB0_JUMPDEST_10361": 29, "EVMBB0_JUMPDEST_10438": 22, "EVMBB0_JUMPDEST_10331": 21, "EVMBB0_JUMPDEST_5362": 20, "EVMBB0_JUMPDEST_10347": 19, "EVMBB0_JUMPDEST_4814": 17, "EVMBB0_JUMPDEST_7471": 14}`

### erc4337_bundle

- Top-frame samples: `32973`
- Category pct: `{"evm_bb": 1.2131, "evm_host": 0.9948, "keccak": 22.4456, "kernel": 4.3581, "memory": 4.8039, "other": 23.7861, "unknown": 42.3983}`
- Top BBs: `{"EVMBB0_JUMPDEST_3620": 28, "EVMBB0_JUMPDEST_8136": 24, "EVMBB0_JUMPDEST_7382": 19, "EVMBB0_MAIN_ENTRY_1": 15, "EVMBB0_JUMPDEST_23559": 13, "EVMBB0_JUMPDEST_11035": 12, "EVMBB0_JUMPDEST_10824": 12, "EVMBB0_JUMPDEST_1451": 11, "EVMBB0_JUMPDEST_3950": 11, "EVMBB0_JUMPDEST_5177": 11}`

### uniswap_v3_swap

- Top-frame samples: `364996`
- Category pct: `{"evm_bb": 0.2512, "evm_host": 0.7819, "keccak": 64.7002, "kernel": 1.1271, "memory": 2.2318, "other": 8.6932, "unknown": 22.2145}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 44, "EVMBB0_JUMPDEST_2146": 30, "EVMBB0_JUMPDEST_16234": 23, "EVMBB0_JUMPDEST_3882": 23, "EVMBB0_JUMPDEST_2018": 22, "EVMBB0_JUMPDEST_16597": 17, "EVMBB0_JUMPDEST_16": 17, "EVMBB0_JUMPDEST_10306": 16, "EVMBB0_JUMPDEST_10160": 16, "EVMBB0_JUMPDEST_16858": 16}`
