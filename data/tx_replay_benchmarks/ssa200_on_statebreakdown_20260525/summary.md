# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_200`
- Mode override: `none`
- Repetitions: `1`
- Runs: `200`
- Exit codes: `{"-6": 4, "0": 46, "1": 12, "2": 126, "5": 12}`

## Wall Time

- Mean: `58.147137648193166` ms
- Median: `31.15361393429339` ms
- P95: `203.65963513031582` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `35.89799609966576` ms
- Mean JIT compilation: `4.9813125000000005` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"-6": 3, "0": 30, "1": 1, "2": 16}`
- Mean wall time: `82.66915603540838` ms
- Mean JIT compilation: `7.836117647058823` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"-6": 1, "2": 49}`
- Mean wall time: `32.90324244648218` ms
- Mean JIT compilation: `1.732617021276596` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `87.79497088864446` ms
- Mean JIT compilation: `4.3114` ms

### uniswapx_reactor

- Runs: `25`
- Exit codes: `{"2": 25}`
- Mean wall time: `22.544366344809532` ms
- Mean JIT compilation: `None` ms
