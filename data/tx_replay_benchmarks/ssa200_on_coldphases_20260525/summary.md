# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"-6": 4, "0": 46, "1": 12, "2": 126, "5": 12}`

## Wall Time

- Mean: `57.914094207808375` ms
- Median: `31.68267000000924` ms
- P95: `215.01974505372343` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `40.37039208225906` ms
- Mean JIT compilation: `5.2261875` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"-6": 3, "0": 30, "1": 1, "2": 16}`
- Mean wall time: `82.06438991241157` ms
- Mean JIT compilation: `8.349588235294119` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"-6": 1, "2": 49}`
- Mean wall time: `30.346425804309547` ms
- Mean JIT compilation: `1.5583829787234043` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `88.08924104087055` ms
- Mean JIT compilation: `4.20055` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `21.942248065024614` ms
- Mean JIT compilation: `None` ms
