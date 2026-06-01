# Campaign Analysis

- Campaign root: `/root/DTVM_zr/DTVM/data/tx_corpus_campaign_free_rpc_mainnet_2026_05_18`
- Generated at: `2026-05-18T06:52:09.561085+00:00`
- Replay-ready rows: `175`
- Stats-only rows: `25`
- Replay hotset rows: `40`

## Dataset Summary

| Dataset | Rows | ReplayReady | Templates | GasP50 | GasP90 | CalldataP50 | CalldataP90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cow_settlement | 25 | 25 | 9 | 499457 | 1382397 | 3364 | 6700 |
| erc20_transfer | 50 | 50 | 50 | 151047 | 547821 | 228 | 3340 |
| erc4337_bundle | 50 | 50 | 3 | 195202 | 589933 | 1764 | 3748 |
| uniswap_v3_swap | 50 | 50 | 50 | 333611 | 1028692 | 1476 | 6340 |
| uniswapx_reactor | 25 | 0 | 2 | 139986 | 169419 | 1316 | 1476 |

## cow_settlement

- Rows: `25`
- Replay-ready: `25`
- Unique template keys: `9`
- Status counts: `{"1": 25}`
- Top selectors: `[["0x13d79a0b", 13], ["0xef4d7b75", 4], ["0x6d7b7040", 3], ["0x4a7cf362", 2], ["0x6a761202", 2]]`
- Top templates: `[["0x744d58584e38d214eb190629f131d5cf8b8703bd68e04452f9692177c37c4bc9", 7], ["0x93dd0a7789d67d75d537cd90e5ccf8f919593cb652f6a7a5f8d6cf7e3769bfd8", 4], ["0x043affbd5683a4f5d460697366a1e1f637b819d28622bffefa042f0805f0af2f", 3], ["0x3b61a4a627bc80287579dd5afae9c0a131b4b86a6deaba3390affc781eeeb3ca", 3], ["0xeb4a81c4f84cabdb4a84ea20e1379a1ca48b326f8b261bc6be6a3b14ef9c335b", 3]]`

## erc20_transfer

- Rows: `50`
- Replay-ready: `50`
- Unique template keys: `50`
- Status counts: `{"1": 50}`
- Top selectors: `[["0xa9059cbb", 13], ["0x34fcd5be", 2], ["0xde0e9a3e", 2], ["0x08b9b2a9", 1], ["0x13d79a0b", 1]]`
- Top templates: `[["0x0000000000000068f116a894984e2db1123eb395", 1], ["0x00c21ca82d94dade0d5d1ed420a4728f58427d21", 1], ["0x00fe78205f5f0e63b8ad2b2ae5337f538a610e04", 1], ["0x043bb01ff9ea6aa00d90ebebb98b4615b66cb1892cf7c4bd1c63d556b8e46e88", 1], ["0x04b7c3feb25fb139df3caea7abc837e09bdfa5fba696d104c777aa9e0052cf8d", 1]]`

## erc4337_bundle

- Rows: `50`
- Replay-ready: `50`
- Unique template keys: `3`
- Status counts: `{"1": 50}`
- Top selectors: `[["0x765e827f", 35], ["0x1fad948c", 15]]`
- Top templates: `[["0x8db5ff695839d655407cc8490bb7a5d82337a86a6b39c3f0258aa6c3b582fc58", 28], ["0xc93c806e738300b5357ecdc2e971d6438d34d8e4e17b99b758b1f9cac91c8e70", 15], ["0x44e632a24c6f2600cbd5b5b8b4c2d372359112c8b5774297f5fd0a9e64f11f86", 7]]`

## uniswap_v3_swap

- Rows: `50`
- Replay-ready: `50`
- Unique template keys: `50`
- Status counts: `{"1": 50}`
- Top selectors: `[["0x99e1d016", 8], ["0x00000000", 3], ["0x13d79a0b", 2], ["0x3593564c", 2], ["0x3e9714c1", 2]]`
- Top templates: `[["0x00000000008d5f1200332af8a6813cb8377b5bfd", 1], ["0x00000000fd3a7b3fa5bcfa843c648714b11e089b", 1], ["0x022d2c67655f64a980535faf0da8009eec889e3ac12d571bcc8a4f5013bce7d7", 1], ["0x0476c2483f4c6aa4dfb6efa29815ab74d9c1e508", 1], ["0x06cff7088619c7178f5e14f0b119458d08d2f5ef", 1]]`

## uniswapx_reactor

- Rows: `25`
- Replay-ready: `0`
- Unique template keys: `2`
- Status counts: `{"0": 3, "1": 22}`
- Top selectors: `[["0x3f62192e", 25]]`
- Top templates: `[["0xb9a2f8c1e26718dcbfd6b091dc077b3e3412f3cb3841913865a4f8dbbc835400", 24], ["0x2c40c62a66e1f1c254a739de6e1e25b126f7dd677de74fa715a43d1114d89946", 1]]`

## Replay Notes

- Stats-only datasets: `uniswapx_reactor`
- These rows are usable for workload statistics, but not for replay until trace/state material is added.
