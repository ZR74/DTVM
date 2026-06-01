# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `none`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"-6": 6, "0": 5, "1": 2, "2": 9, "3": 3, "5": 4, "7": 3, "8": 8}`

## Wall Time

- Mean: `9807.203115953598` ms
- Median: `3710.1821625838056` ms
- P95: `37641.90388029674` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"2": 3, "3": 1, "5": 4, "7": 2}`
- Mean wall time: `3363.25831245631` ms
- Mean JIT compilation: `3328.0317999999997` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"-6": 2, "0": 5, "2": 3}`
- Mean wall time: `13973.485918156803` ms
- Mean JIT compilation: `11292.09` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"3": 2, "8": 8}`
- Mean wall time: `4806.253064214252` ms
- Mean JIT compilation: `4762.4573` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"-6": 4, "1": 2, "2": 3, "7": 1}`
- Mean wall time: `17085.81516898703` ms
- Mean JIT compilation: `14157.061000000002` ms
