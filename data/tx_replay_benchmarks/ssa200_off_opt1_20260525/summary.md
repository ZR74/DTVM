# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `57.95527943409979` ms
- Median: `33.56970695313066` ms
- P95: `213.33867462817562` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `40.46491364017129` ms
- Mean JIT compilation: `5.52825` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `81.51131440419704` ms
- Mean JIT compilation: `14.072149999999999` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `32.55816118326038` ms
- Mean JIT compilation: `1.6794375` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `87.00927713885903` ms
- Mean JIT compilation: `4.3383` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `21.019816379994154` ms
- Mean JIT compilation: `None` ms
