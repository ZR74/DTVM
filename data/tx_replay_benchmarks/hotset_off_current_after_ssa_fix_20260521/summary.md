# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 11, "1": 2, "2": 23, "5": 4}`

## Wall Time

- Mean: `61.394410813227296` ms
- Median: `34.05730484519154` ms
- P95: `190.4778683558106` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 5, "5": 4}`
- Mean wall time: `44.080114527605474` ms
- Mean JIT compilation: `5.473375` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 4}`
- Mean wall time: `66.0073779989034` ms
- Mean JIT compilation: `6.296333333333333` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 10}`
- Mean wall time: `29.476351267658174` ms
- Mean JIT compilation: `1.5084444444444445` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 4, "1": 2, "2": 4}`
- Mean wall time: `106.01379945874214` ms
- Mean JIT compilation: `3.9333333333333336` ms
