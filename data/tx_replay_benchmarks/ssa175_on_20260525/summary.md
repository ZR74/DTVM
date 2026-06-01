# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_175`
- Mode override: `none`
- Repetitions: `1`
- Runs: `175`
- Exit codes: `{"-6": 4, "0": 46, "1": 12, "2": 101, "5": 12}`

## Wall Time

- Mean: `64.99115234773073` ms
- Median: `34.9116250872612` ms
- P95: `213.53649725206174` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `38.68642957881093` ms
- Mean JIT compilation: `4.9188125` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"-6": 3, "0": 30, "1": 1, "2": 16}`
- Mean wall time: `82.81672239303589` ms
- Mean JIT compilation: `8.389294117647058` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"-6": 1, "2": 49}`
- Mean wall time: `35.42453837580979` ms
- Mean JIT compilation: `1.7868510638297872` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `89.88455765880644` ms
- Mean JIT compilation: `4.25345` ms
