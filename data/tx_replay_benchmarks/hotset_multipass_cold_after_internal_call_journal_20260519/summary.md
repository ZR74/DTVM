# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 11, "1": 2, "2": 20, "3": 3, "5": 4}`

## Wall Time

- Mean: `13068.425906394259` ms
- Median: `4626.557177572977` ms
- P95: `44180.57984986225` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 4, "3": 1, "5": 4}`
- Mean wall time: `4265.1931720087305` ms
- Mean JIT compilation: `4222.7474` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 4}`
- Mean wall time: `16549.392177094705` ms
- Mean JIT compilation: `16473.4168` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 8, "3": 2}`
- Mean wall time: `4876.596604078077` ms
- Mean JIT compilation: `4829.3035` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 4, "1": 2, "2": 4}`
- Mean wall time: `26582.521672395524` ms
- Mean JIT compilation: `26493.9782` ms
