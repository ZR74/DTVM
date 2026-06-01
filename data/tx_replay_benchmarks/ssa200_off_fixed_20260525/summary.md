# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `58.50552659132518` ms
- Median: `32.003738451749086` ms
- P95: `208.25281759025526` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `37.580054979771376` ms
- Mean JIT compilation: `4.9300625` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `81.7978340247646` ms
- Mean JIT compilation: `14.4071` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `30.87732377462089` ms
- Mean JIT compilation: `1.7233749999999999` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `90.34980166703463` ms
- Mean JIT compilation: `4.6561` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `24.414238817989826` ms
- Mean JIT compilation: `None` ms
