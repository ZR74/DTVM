# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"-6": 9, "0": 4, "1": 5, "2": 5, "3": 2, "5": 4, "7": 3, "8": 8}`

## Wall Time

- Mean: `5935.451944707893` ms
- Median: `1975.0031260191463` ms
- P95: `24440.076354081935` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"-6": 2, "0": 1, "1": 1, "5": 4, "7": 2}`
- Mean wall time: `308.89024699572474` ms
- Mean JIT compilation: `245.49185714285713` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"-6": 3, "0": 3, "1": 2, "2": 2}`
- Mean wall time: `4459.871568507515` ms
- Mean JIT compilation: `4651.3566` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"3": 2, "8": 8}`
- Mean wall time: `4747.681031911634` ms
- Mean JIT compilation: `4704.904` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"-6": 4, "1": 2, "2": 3, "7": 1}`
- Mean wall time: `14225.364931416698` ms
- Mean JIT compilation: `11517.698999999999` ms
