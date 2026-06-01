# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_175`
- Mode override: `none`
- Repetitions: `1`
- Runs: `175`
- Exit codes: `{"0": 49, "1": 12, "2": 102, "5": 12}`

## Wall Time

- Mean: `63.62467542822872` ms
- Median: `33.74810214154422` ms
- P95: `217.711141891777` ms

## Per Dataset

### cow_settlement

- Runs: `25`
- Exit codes: `{"0": 1, "2": 14, "5": 10}`
- Mean wall time: `38.169163446873426` ms
- Mean JIT compilation: `5.375` ms

### erc20_transfer

- Runs: `50`
- Exit codes: `{"0": 33, "1": 1, "2": 16}`
- Mean wall time: `80.94462050125003` ms
- Mean JIT compilation: `13.83715` ms

### erc4337_bundle

- Runs: `50`
- Exit codes: `{"2": 50}`
- Mean wall time: `30.764220617711544` ms
- Mean JIT compilation: `1.7301041666666668` ms

### uniswap_v3_swap

- Runs: `50`
- Exit codes: `{"0": 15, "1": 11, "2": 22, "5": 2}`
- Mean wall time: `91.89294115640223` ms
- Mean JIT compilation: `4.5921` ms
