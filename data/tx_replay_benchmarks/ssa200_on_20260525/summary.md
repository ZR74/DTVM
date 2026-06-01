# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"-6": 4, "0": 46, "1": 12, "2": 126, "5": 12}`

## Wall Time

- Mean: `59.948049280792475` ms
- Median: `32.556979451328516` ms
- P95: `215.86728065740303` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `35.42345901951194` ms
- Mean JIT compilation: `4.816625` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"-6": 3, "0": 30, "1": 1, "2": 16}`
- Mean wall time: `87.01467296108603` ms
- Mean JIT compilation: `8.849` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"-6": 1, "2": 49}`
- Mean wall time: `32.95881565660238` ms
- Mean JIT compilation: `1.7046808510638298` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `90.71201659739017` ms
- Mean JIT compilation: `4.2267` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `22.789924796670675` ms
- Mean JIT compilation: `None` ms
