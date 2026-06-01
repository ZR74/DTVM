# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `57.69334905780852` ms
- Median: `33.84559147525579` ms
- P95: `216.3774151704273` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `38.14583790488541` ms
- Mean JIT compilation: `5.385125` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `79.53335232567042` ms
- Mean JIT compilation: `14.0805` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `32.793693570420146` ms
- Mean JIT compilation: `1.6843541666666668` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `88.29819347709417` ms
- Mean JIT compilation: `3.849` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `22.150475811213255` ms
- Mean JIT compilation: `None` ms
