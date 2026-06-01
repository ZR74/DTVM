# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 6, "1": 7, "2": 10, "3": 2, "5": 4, "7": 3, "8": 8}`

## Wall Time

- Mean: `9455.501738318708` ms
- Median: `2080.9368065092713` ms
- P95: `40439.03243859531` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 3, "1": 1, "5": 4, "7": 2}`
- Mean wall time: `332.43244434706867` ms
- Mean JIT compilation: `201.6078888888889` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 3, "1": 4, "2": 3}`
- Mean wall time: `5937.516563595273` ms
- Mean JIT compilation: `8766.533333333333` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"3": 2, "8": 8}`
- Mean wall time: `4916.449058498256` ms
- Mean JIT compilation: `4873.08` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"1": 2, "2": 7, "7": 1}`
- Mean wall time: `26635.608886834234` ms
- Mean JIT compilation: `29123.307444444443` ms
