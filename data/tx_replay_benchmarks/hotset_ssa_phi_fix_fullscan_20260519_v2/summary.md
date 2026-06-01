# Replay Benchmark Summary

- Prepared root: `/root/DTVM_zr/DTVM/data/tx_replay_prepare_hotset_partial_build_ssa`
- Mode override: `none`
- Repetitions: `1`
- Runs: `40`
- Exit codes: `{"0": 5, "1": 2, "2": 15, "3": 3, "5": 4, "7": 3, "8": 8}`

## Wall Time

- Mean: `12508.354053745279` ms
- Median: `5047.725676558912` ms
- P95: `40558.07958281365` ms

## Per Dataset

### cow_settlement

- Runs: `10`
- Exit codes: `{"2": 3, "3": 1, "5": 4, "7": 2}`
- Mean wall time: `3360.7552553294227` ms
- Mean JIT compilation: `3325.4216` ms

### erc20_transfer

- Runs: `10`
- Exit codes: `{"0": 5, "2": 5}`
- Mean wall time: `16006.52591495309` ms
- Mean JIT compilation: `15946.256599999999` ms

### erc4337_bundle

- Runs: `10`
- Exit codes: `{"3": 2, "8": 8}`
- Mean wall time: `5400.084953010082` ms
- Mean JIT compilation: `5348.9028` ms

### uniswap_v3_swap

- Runs: `10`
- Exit codes: `{"1": 2, "2": 7, "7": 1}`
- Mean wall time: `25266.05009168852` ms
- Mean JIT compilation: `25195.1517` ms
