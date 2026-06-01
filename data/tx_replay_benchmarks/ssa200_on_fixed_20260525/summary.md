# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `61.53454712941311` ms
- Median: `31.577208545058966` ms
- P95: `199.04044687282268` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `36.250913087278605` ms
- Mean JIT compilation: `4.3630625` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `98.91227359883487` ms
- Mean JIT compilation: `8.148588235294119` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `30.187655654735863` ms
- Mean JIT compilation: `1.6271702127659575` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `88.68601211812347` ms
- Mean JIT compilation: `4.15035` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `20.453581204637885` ms
- Mean JIT compilation: `None` ms
