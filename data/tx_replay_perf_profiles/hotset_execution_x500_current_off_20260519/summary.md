# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build_perf/dtvm`
- Mode override: `multipass`
- Extra executions: `500`
- Perf frequency: `9999`
- Runs: `40`
- Top-frame samples: `23383`
- Category pct: `{"evm_bb": 1.454, "evm_host": 2.9594, "keccak": 7.9117, "kernel": 6.0642, "memory": 4.9095, "other": 29.9063, "unknown": 46.7947}`

## Top EVM BBs

- `EVMBB0_MAIN_ENTRY_1`: `15` samples
- `EVMBB0_JUMPDEST_8136`: `10` samples
- `EVMBB0_JUMPDEST_10347`: `7` samples
- `EVMBB0_JUMPDEST_18336`: `6` samples
- `EVMBB0_JUMPDEST_10422`: `6` samples
- `EVMBB0_JUMPDEST_5225`: `5` samples
- `EVMBB0_JUMPDEST_16633`: `5` samples
- `EVMBB0_JUMPDEST_18481`: `4` samples
- `EVMBB0_JUMPDEST_8671`: `4` samples
- `EVMBB0_JUMPDEST_18621`: `4` samples
- `EVMBB0_JUMPDEST_10277`: `4` samples
- `EVMBB0_JUMPDEST_4932`: `4` samples
- `EVMBB0_JUMPDEST_10361`: `4` samples
- `EVMBB0_JUMPDEST_10438`: `4` samples
- `EVMBB0_JUMPDEST_2692`: `4` samples
- `EVMBB0_JUMPDEST_7641`: `3` samples
- `EVMBB0_JUMPDEST_7020`: `3` samples
- `EVMBB0_JUMPDEST_2587`: `3` samples
- `EVMBB0_JUMPDEST_16`: `3` samples
- `EVMBB0_JUMPDEST_4814`: `3` samples

## Top Host Symbols

- `evmGetCallDataLoad`: `190` samples
- `evmHandleCallInternal`: `150` samples
- `evmGetSLoad`: `67` samples
- `evmGetMulMod`: `47` samples
- `evmEmitLog3`: `45` samples
- `evmSetReturn`: `31` samples
- `evmEmitLog2`: `21` samples
- `evmSetCallDataCopy`: `19` samples
- `evmSetSStore`: `18` samples
- `evmHandleCall`: `16` samples
- `evmSetRevert`: `12` samples
- `evmSetReturnDataCopy`: `11` samples
- `evmExpandMemoryNoGas`: `9` samples
- `evmHandleStaticCall`: `8` samples
- `evmGetDiv`: `7` samples
- `evmHandleUndefined`: `5` samples
- `evmGetTLoad`: `5` samples
- `evmHandleDelegateCall`: `4` samples
- `evmGetExtCodeSize`: `4` samples
- `evmGetMod`: `4` samples

## Datasets

### cow_settlement

- Top-frame samples: `5550`
- Category pct: `{"evm_bb": 1.0631, "evm_host": 2.7387, "keccak": 6.7748, "kernel": 4.3604, "memory": 5.5676, "other": 29.6577, "unknown": 49.8378}`
- Top BBs: `{"EVMBB0_JUMPDEST_18336": 6, "EVMBB0_JUMPDEST_18481": 4, "EVMBB0_JUMPDEST_8671": 4, "EVMBB0_JUMPDEST_18621": 4, "EVMBB0_JUMPDEST_7641": 3, "EVMBB0_JUMPDEST_7020": 3, "EVMBB0_JUMPDEST_2587": 3, "EVMBB0_JUMPDEST_9586": 2, "EVMBB0_JUMPDEST_14524": 2, "EVMBB0_SWITCH0_11246": 2}`

### erc20_transfer

- Top-frame samples: `6418`
- Category pct: `{"evm_bb": 2.01, "evm_host": 2.7267, "keccak": 4.129, "kernel": 6.3415, "memory": 5.5313, "other": 32.7984, "unknown": 46.4631}`
- Top BBs: `{"EVMBB0_MAIN_ENTRY_1": 8, "EVMBB0_JUMPDEST_10347": 7, "EVMBB0_JUMPDEST_10422": 6, "EVMBB0_JUMPDEST_5225": 5, "EVMBB0_JUMPDEST_10277": 4, "EVMBB0_JUMPDEST_4932": 4, "EVMBB0_JUMPDEST_10361": 4, "EVMBB0_JUMPDEST_10438": 4, "EVMBB0_JUMPDEST_2692": 4, "EVMBB0_JUMPDEST_4814": 3}`

### erc4337_bundle

- Top-frame samples: `3109`
- Category pct: `{"evm_bb": 1.8334, "evm_host": 1.8012, "keccak": 29.3342, "kernel": 5.854, "memory": 3.12, "other": 28.8839, "unknown": 29.1734}`
- Top BBs: `{"EVMBB0_JUMPDEST_8136": 10, "EVMBB0_JUMPDEST_1451": 3, "EVMBB0_JUMPDEST_2114": 3, "EVMBB0_JUMPDEST_10824": 2, "EVMBB0_JUMPDEST_1333": 2, "EVMBB0_JUMPDEST_7670": 2, "EVMBB0_JUMPDEST_10764": 2, "EVMBB0_JUMPDEST_14045": 2, "EVMBB0_JUMPDEST_4427": 2, "EVMBB0_JUMPDEST_3620": 2}`

### uniswap_v3_swap

- Top-frame samples: `8306`
- Category pct: `{"evm_bb": 1.1438, "evm_host": 3.7202, "keccak": 3.5757, "kernel": 7.0672, "memory": 4.6593, "other": 28.2206, "unknown": 51.6133}`
- Top BBs: `{"EVMBB0_JUMPDEST_16633": 5, "EVMBB0_MAIN_ENTRY_1": 4, "EVMBB0_JUMPDEST_9944": 3, "EVMBB0_JUMPDEST_16858": 3, "EVMBB0_JUMPDEST_2146": 3, "EVMBB0_JUMPDEST_34": 2, "EVMBB0_JUMPDEST_11676": 2, "EVMBB0_JUMPDEST_5475": 2, "EVMBB0_JUMPDEST_4404": 2, "EVMBB0_JUMPDEST_8450": 2}`
