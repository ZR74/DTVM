# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial`
- Mode override: `interpreter`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 12, "2": 23, "5": 5}`

## Wall Time

- Mean: `30.02294712641742` ms
- Median: `27.49955898616463` ms
- P95: `51.74828538438299` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"0": 1, "2": 5, "5": 4}`
- Mean wall time: `28.93649898469448` ms
- Mean JIT compilation: `None` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 6, "2": 4}`
- Mean wall time: `25.660333898849785` ms
- Mean JIT compilation: `None` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"2": 10}`
- Mean wall time: `23.43523930758238` ms
- Mean JIT compilation: `None` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"0": 5, "2": 4, "5": 1}`
- Mean wall time: `42.05971631454304` ms
- Mean JIT compilation: `None` ms
