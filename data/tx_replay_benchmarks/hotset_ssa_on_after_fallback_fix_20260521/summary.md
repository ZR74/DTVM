# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 11, "1": 2, "2": 23, "5": 4}`

## Wall Time

- Mean: `63.860286882845685` ms
- Median: `38.0515429424122` ms
- P95: `192.48361752834165` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 5, "5": 4}`
- Mean wall time: `46.29915179684758` ms
- Mean JIT compilation: `4.99875` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 4}`
- Mean wall time: `70.98429009784013` ms
- Mean JIT compilation: `7.688` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 10}`
- Mean wall time: `32.28829230647534` ms
- Mean JIT compilation: `1.416111111111111` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 4, "1": 2, "2": 4}`
- Mean wall time: `105.86941333021969` ms
- Mean JIT compilation: `3.3296666666666668` ms
