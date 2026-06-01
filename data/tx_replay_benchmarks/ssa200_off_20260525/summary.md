# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `59.98775000334717` ms
- Median: `33.62598887179047` ms
- P95: `196.37756018200866` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `40.78971614129841` ms
- Mean JIT compilation: `5.7461875` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `84.43552271928638` ms
- Mean JIT compilation: `15.875399999999999` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `32.84767692908645` ms
- Mean JIT compilation: `1.9565625000000002` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `91.79383381735533` ms
- Mean JIT compilation: `4.566750000000001` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `20.958216954022646` ms
- Mean JIT compilation: `None` ms
