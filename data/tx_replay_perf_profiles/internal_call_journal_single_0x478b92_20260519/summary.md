# Replay Perf Profiling Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- DTVM path: `./build/dtvm`
- Mode override: `multipass`
- Extra executions: `5000`
- Perf frequency: `9999`
- Runs: `1`
- Top-frame samples: `20470`
- Category pct: `{"evm_host": 3.5173, "keccak": 6.1505, "kernel": 1.5193, "memory": 4.4602, "other": 23.3903, "unknown": 60.9624}`

## Top EVM BBs


## Top Host Symbols

- `evmGetCallDataLoad`: `329` samples
- `evmHandleCallInternal`: `117` samples
- `evmGetSLoad`: `54` samples
- `evmEmitLog3`: `35` samples
- `evmSetReturn`: `29` samples
- `evmSetCallDataCopy`: `21` samples
- `evmHandleStaticCall`: `14` samples
- `evmEmitLog2`: `14` samples
- `evmSetRevert`: `13` samples
- `evmSetReturnDataCopy`: `11` samples
- `evmExpandMemoryNoGas`: `11` samples
- `evmSetCodeCopy`: `10` samples
- `evmGetExtCodeSize`: `10` samples
- `evmSetSStore`: `10` samples
- `evmHandleCall`: `9` samples
- `evmGetTimestamp`: `8` samples
- `evmHandleDelegateCall`: `6` samples
- `evmGetDiv`: `6` samples
- `evmGetSelfBalance`: `5` samples
- `evmGetChainId`: `5` samples

## Datasets

### cow_settlement

- Top-frame samples: `20470`
- Category pct: `{"evm_host": 3.5173, "keccak": 6.1505, "kernel": 1.5193, "memory": 4.4602, "other": 23.3903, "unknown": 60.9624}`
- Top BBs: `{}`
