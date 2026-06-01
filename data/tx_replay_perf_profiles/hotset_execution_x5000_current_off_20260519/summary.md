# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build_perf/dtvm`
- Mode override: `multipass`
- Extra executions: `5000`
- Perf frequency: `9999`
- Runs: `40`
- Top-frame samples: `185589`
- Category pct: `{"evm_bb": 1.2668, "evm_host": 3.0896, "keccak": 7.2607, "kernel": 4.5919, "memory": 4.9739, "other": 29.7792, "unknown": 49.0379}`

## Top EVM BBs

- `EVMBB0_MAIN_ENTRY_1`: `126` samples
- `EVMBB0_JUMPDEST_10422`: `29` samples
- `EVMBB0_JUMPDEST_10438`: `28` samples
- `EVMBB0_JUMPDEST_14524`: `25` samples
- `EVMBB0_JUMPDEST_10361`: `22` samples
- `EVMBB0_JUMPDEST_10347`: `22` samples
- `EVMBB0_JUMPDEST_5225`: `22` samples
- `EVMBB0_JUMPDEST_13042`: `20` samples
- `EVMBB0_JUMPDEST_8671`: `20` samples
- `EVMBB0_JUMPDEST_4932`: `20` samples
- `EVMBB0_JUMPDEST_7382`: `20` samples
- `EVMBB0_JUMPDEST_10331`: `19` samples
- `EVMBB0_JUMPDEST_3882`: `19` samples
- `EVMBB0_JUMPDEST_18336`: `17` samples
- `EVMBB0_JUMPDEST_16858`: `17` samples
- `EVMBB0_SWITCH0_11246`: `16` samples
- `EVMBB0_JUMPDEST_8539`: `16` samples
- `EVMBB0_JUMPDEST_8136`: `16` samples
- `EVMBB0_JUMPDEST_18481`: `15` samples
- `EVMBB0_JUMPDEST_5384`: `15` samples

## Top Host Symbols

- `evmGetCallDataLoad`: `1492` samples
- `evmHandleCallInternal`: `1230` samples
- `evmGetSLoad`: `534` samples
- `evmGetMulMod`: `473` samples
- `evmEmitLog3`: `358` samples
- `evmSetReturn`: `344` samples
- `evmSetSStore`: `190` samples
- `evmEmitLog2`: `166` samples
- `evmSetRevert`: `98` samples
- `evmSetCallDataCopy`: `97` samples
- `evmExpandMemoryNoGas`: `95` samples
- `evmHandleCall`: `79` samples
- `evmHandleStaticCall`: `61` samples
- `evmGetSDiv`: `59` samples
- `evmGetExtCodeSize`: `54` samples
- `evmSetReturnDataCopy`: `51` samples
- `evmGetDiv`: `51` samples
- `evmSetCodeCopy`: `43` samples
- `evmHandleDelegateCall`: `34` samples
- `evmGetOrigin`: `30` samples

## Datasets

### cow_settlement

- Top-frame samples: `46282`
- Category pct: `{"evm_bb": 1.0998, "evm_host": 2.7981, "keccak": 6.845, "kernel": 6.8688, "memory": 4.9674, "other": 28.2291, "unknown": 49.1919}`
- Top BBs: `{"EVMBB0_JUMPDEST_14524": 25, "EVMBB0_MAIN_ENTRY_1": 24, "EVMBB0_JUMPDEST_13042": 20, "EVMBB0_JUMPDEST_8671": 20, "EVMBB0_JUMPDEST_18336": 17, "EVMBB0_SWITCH0_11246": 16, "EVMBB0_JUMPDEST_8539": 16, "EVMBB0_JUMPDEST_18481": 15, "EVMBB0_JUMPDEST_18621": 13, "EVMBB0_JUMPDEST_11223": 11}`

### erc20_transfer

- Top-frame samples: `50262`
- Category pct: `{"evm_bb": 1.5598, "evm_host": 3.0062, "keccak": 4.2179, "kernel": 3.7324, "memory": 5.4534, "other": 32.3445, "unknown": 49.6856}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 45, "EVMBB0_JUMPDEST_10422": 29, "EVMBB0_JUMPDEST_10438": 28, "EVMBB0_JUMPDEST_10361": 22, "EVMBB0_JUMPDEST_10347": 22, "EVMBB0_JUMPDEST_5225": 22, "EVMBB0_JUMPDEST_4932": 20, "EVMBB0_JUMPDEST_10331": 19, "EVMBB0_JUMPDEST_5384": 15, "EVMBB0_JUMPDEST_4814": 14}`

### erc4337_bundle

- Top-frame samples: `20270`
- Category pct: `{"evm_bb": 1.6428, "evm_host": 1.5146, "keccak": 29.9803, "kernel": 5.9497, "memory": 3.5767, "other": 27.7849, "unknown": 29.5511}`
- Top BBs: `{"EVMBB0_JUMPDEST_7382": 20, "EVMBB0_JUMPDEST_8136": 16, "EVMBB0_JUMPDEST_14045": 15, "EVMBB0_JUMPDEST_10824": 14, "EVMBB0_MAIN_ENTRY_1": 10, "EVMBB0_JUMPDEST_3950": 10, "EVMBB0_JUMPDEST_2114": 9, "EVMBB0_JUMPDEST_5177": 8, "EVMBB0_JUMPDEST_10985": 7, "EVMBB0_JUMPDEST_5198": 7}`

### uniswap_v3_swap

- Top-frame samples: `68775`
- Category pct: `{"evm_bb": 1.0542, "evm_host": 3.811, "keccak": 3.068, "kernel": 3.2875, "memory": 5.0396, "other": 29.5354, "unknown": 54.2043}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 47, "EVMBB0_JUMPDEST_3882": 19, "EVMBB0_JUMPDEST_16858": 17, "EVMBB0_JUMPDEST_10306": 15, "EVMBB0_JUMPDEST_4108": 13, "EVMBB0_JUMPDEST_10160": 12, "EVMBB0_JUMPDEST_2146": 12, "EVMBB0_JUMPDEST_16597": 11, "EVMBB0_JUMPDEST_4387": 11, "EVMBB0_JUMPDEST_16234": 11}`
