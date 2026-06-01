# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- Mode override: `multipass`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 11, "1": 2, "2": 20, "3": 3, "5": 4}`

## Wall Time

- Mean: `13068.53973964171` ms
- Median: `4681.633278960362` ms
- P95: `43759.10403750022` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 4, "3": 1, "5": 4}`
- Mean wall time: `4309.726204257458` ms
- Mean JIT compilation: `4264.1335` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 4}`
- Mean wall time: `16308.926755096763` ms
- Mean JIT compilation: `16229.9723` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 8, "3": 2}`
- Mean wall time: `4821.53464439325` ms
- Mean JIT compilation: `4772.5957` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 4, "1": 2, "2": 4}`
- Mean wall time: `26833.97135481937` ms
- Mean JIT compilation: `26749.9125` ms
