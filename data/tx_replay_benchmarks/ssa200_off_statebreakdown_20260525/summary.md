# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"0": 49, "1": 12, "2": 127, "5": 12}`

## Wall Time

- Mean: `58.52616851567291` ms
- Median: `34.16591859422624` ms
- P95: `212.74954058462748` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `39.14804148487747` ms
- Mean JIT compilation: `5.4608125` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `81.86692772898823` ms
- Mean JIT compilation: `13.99505` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `32.945845713838935` ms
- Mean JIT compilation: `1.807125` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `87.85745275206864` ms
- Mean JIT compilation: `4.18615` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `23.720854250714183` ms
- Mean JIT compilation: `None` ms
