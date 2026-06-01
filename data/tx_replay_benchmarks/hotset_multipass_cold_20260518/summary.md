# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 10, "2": 17, "5": 5, "9": 8}`

## Wall Time

- Mean: `6035.191862820648` ms
- Median: `2014.2285604961216` ms
- P95: `24582.234132377173` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 5, "5": 4}`
- Mean wall time: `7551.139526290353` ms
- Mean JIT compilation: `7499.6891000000005` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 2, "9": 2}`
- Mean wall time: `9490.423620713409` ms
- Mean JIT compilation: `11774.662625` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 8, "9": 2}`
- Mean wall time: `2791.530211502686` ms
- Mean JIT compilation: `3441.46175` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 3, "2": 2, "5": 1, "9": 4}`
- Mean wall time: `4307.674092776142` ms
- Mean JIT compilation: `7099.536833333333` ms
