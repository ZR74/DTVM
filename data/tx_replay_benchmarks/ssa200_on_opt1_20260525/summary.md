# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"-6": 4, "0": 46, "1": 12, "2": 126, "5": 12}`

## Wall Time

- Mean: `59.543721227673814` ms
- Median: `33.766499953344464` ms
- P95: `201.29152442095793` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `40.72114505805075` ms
- Mean JIT compilation: `5.1659375` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"-6": 3, "0": 30, "1": 1, "2": 16}`
- Mean wall time: `83.93635582178831` ms
- Mean JIT compilation: `8.04370588235294` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"-6": 1, "2": 49}`
- Mean wall time: `32.83281534444541` ms
- Mean JIT compilation: `1.6241914893617022` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `88.09989588335156` ms
- Mean JIT compilation: `3.8714` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `25.890490664169192` ms
- Mean JIT compilation: `None` ms
