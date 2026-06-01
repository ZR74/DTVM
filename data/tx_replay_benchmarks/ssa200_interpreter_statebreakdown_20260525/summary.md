# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `interpreter`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `23.446306441910565` ms
- Median: `20.48523398116231` ms
- P95: `51.34009903995319` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `22.173566529527307` ms
- Mean JIT compilation: `None` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `25.43981411959976` ms
- Mean JIT compilation: `None` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `19.257174446247518` ms
- Mean JIT compilation: `None` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `30.95380994025618` ms
- Mean JIT compilation: `None` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `14.0952879935503` ms
- Mean JIT compilation: `None` ms
