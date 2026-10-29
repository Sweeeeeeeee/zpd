# Step 4: Training data for auxiliary constructions

## Source: GenesisGeo (reused, not regenerated)

GenesisGeo (arXiv 2509.21896, ZJUVAI) open-sourced both its generator (a fork
of Newclid, github.com/ZJUVAI/GenesisGeo) and its data, so we reuse the data:

* https://huggingface.co/datasets/ZJUVAI/GenesisGeo, Apache-2.0, 8.2 GB of
  Parquet in 8 shards of about 1 GB each.
* 21.8M problems, each proven by their Newclid-based DDAR. 2.96M (13.6%) need an
  auxiliary construction.

`genesisgeo.py` downloads only as many shards as it needs (one shard is enough
for 100k examples). It keeps the rows that have an `<aux>` section and converts
them. It also drops exact duplicates, caps the number of goals kept per figure,
and takes a uniform random sample. The split into train and validation is by
figure, so no figure appears in both.

```bash
.venv-newclid/bin/python -m datagen.genesisgeo --size 100000          # ~2 min after download
.venv-newclid/bin/python -m datagen.genesisgeo --size 5000 --out-dir data/gg_5k
```

Options: `--size`, `--val-frac` (0.02), `--max-tokens` (512, drop longer examples),
`--max-per-setup` (3 goals per figure), `--shards`, `--seed`, `--out-dir`.

## Output (`data/genesisgeo/`, gitignored)

| file | content |
|---|---|
| `train.txt` | 98,008 lines |
| `val.txt` | 1,992 lines |
| `meta.json` | source, arguments, filter statistics, length statistics |

From one shard (2.76M rows): 298k rows have an aux section, 162k were dropped by
the per-figure cap, and 136k candidates remained, from which 100k were sampled.
Sequences are 100 tokens long at the median and 239 at most.

Format: one example per line, `PROBLEM <aux> AUX`. Each point is defined by the
predicates it satisfies:

```
a :; b :; c :; d : cong a d b d; e : coll b d e, cong b e d e; f : coll c d f, cong c f d f; g : coll c e g, coll b f g ? eqratio a d c g d e e g <aux> h : coll b c h, cong b h c h
```

74% of examples add 1 auxiliary point, 18% add 2, and the rest add 3–8.

## Notes

* The syntax is predicate-based (AlphaGeometry / GenesisGeo style), not
  Newclid's construction syntax. `pipeline/translate.py` converts in both
  directions: Newclid problem to model input, and model output to Newclid
  constructions.
* The proof steps in the source are dropped. Only (problem, aux) pairs are kept.
* The fraction of rows with aux varies along the shard: 3% in the first row
  group, 11% over the whole shard.
* Generating fresh data instead would mean running GenesisGeo's pipeline
  (`src/newclid/generation/pipeline.py`, Ray-based) or Newclid's `ncdgen`. That
  was not needed here.
