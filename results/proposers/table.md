### Held-out problems (GenesisGeo val, first auxiliary point, beam 4)

| Model | Size | Kind | Problems | Translatable beams | Exact@1 | Exact@4 (95% CI) | s / problem | Load s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mini | 2,1M | mūsu | 200 | 91.6% | 7.5% | 28.5% (22.7%–35.1%) | 0.3 | 6 |
| mini_long | 2,1M | mūsu | 200 | 90.6% | 42% | 65% (58.2%–71.3%) | 0.3 | 5 |
| mid | 5,1M | mūsu | 200 | 90.8% | 51.5% | 68% (61.2%–74.1%) | 0.7 | 3 |
| SmolLM2-135M | 135M | vispārīgs, few-shot | 50 | 0% | 0% | 0% (0%–7.1%) | 12.9 | 10 |
| SmolLM2-360M | 360M | vispārīgs, few-shot | 50 | 55% | 2% | 12% (5.6%–23.8%) | 25.2 | 14 |
| Qwen3-0.6B-Base | 0,6B | vispārīgs, few-shot | 5 | 10% | 0% | 0% (0%–43.4%) | 89.0 | 10 |
| Qwen2.5-1.5B | 1,5B | vispārīgs, few-shot | 3 | 66.7% | 0% | 0% (0%–56.2%) | 463.9 | 11 |
| GenesisGeo | 0,6B | ģeometrijas, gatavs | 15 | 81.7% | 53.3% | 73.3% (48%–89.1%) | 28.5 | 18 |
| AlphaGeometry | 152M | ģeometrijas, gatavs | 0 | – | – | – | – | killed 3 of 3 attempts (rc 1), 0 problems done |

### Comparison (DDAR failures per domain, one auxiliary point, 60 s after loading)

| Domain | Proposer | Solved | Of | Median s | Median load s | Peak MB | Timeouts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full | DDAR alone | 5 | 60 | 62.7 | – | – | 32 |
| full | heuristics | 0 | 55 (run on 31) | 61.7 | 4.0 | 289 | 26 |
