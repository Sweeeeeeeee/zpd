# Olympiad Geometry Scanner

Which geometry problems can a deduction engine prove with the points already in the diagram? When it stalls, this project tests whether a heuristic or a small transformer can supply a useful auxiliary point. The solver records the construction, proof outcome, search depth and resource use for each problem.

**[View the live results](https://zpd.aniwe.me/)**, open the [self-contained HTML](docs/results/index.html) locally, or read the [Latvian research paper (PDF)](zpd_darbs/preliminary/template_preliminary.pdf). The [eight-slide Latvian presentation](zpd_darbs/prezentacija/prezentacija.pdf) includes a worked olympiad proof and [rehearsal notes](zpd_darbs/prezentacija/README.md). The [local replication](results/local-cpu/README.md) links predictions, per-problem proofs and scoring definitions.

## Findings

In the archived JGEX benchmark, DD-AR solved 205 of 231 problems. Across independent searches with heuristics and two trained models, 217 distinct problems had proofs. Those searches allowed up to two auxiliary levels. The restricted-domain experiment uses a separate limit of one auxiliary point.

At step 6,300, the 11.2M-parameter Geo-LM small model matched the first auxiliary point in 137 of 200 cases within four proposals, compared with 129 for mid. It recovered six JGEX and one IMO proof on baseline failures. All seven constructions replayed with deduction alone. Earlier configurations had already proved those seven problems.

The completed 20,000-step run selected step 20,000 by validation loss. It matched 113 of 200 first proposals and 143 within four proposals. On baseline failures it proved 6/26 JGEX and 0/14 IMO problems. Across the separate 101-problem auxiliary set, heuristics, mini_long and mid together proved 11 distinct problems.

The [within-edition IMO comparison](results/local-cpu/imo/score-comparison.md) covers 12 official problems in six cohorts. In the three editions where deduction proved just one, contestants scored higher on the problem it proved. In the other three pairs, both solver outcomes matched.

Across [390 runs on the same 65 Latvian problems](results/latvia-domains/#auxiliary-point-search-in-the-full-rule-set), all three policies proved the same 20 problems with algebraic reasoning enabled and zero with it disabled. Each attempt had 60 seconds after loading.

For the Latvian corpus, automatic checks accepted 57 of 80 candidates. Recorded Claude decisions accepted eight more and rejected five. Ten translations await decisions. [Six official sources were compared with their translations](problems/latvia/geometry_translated/REVIEW.md#findings-for-the-six-selected-translations). All 3,940 figures constructed on fresh seeds satisfied their goals, and 220 attempts failed during construction. [Drawing records and the two-problem student score comparison](results/latvia-audit/)

## Run locally

On a fresh Debian or Ubuntu machine with Python 3.11–3.13:

```sh
bash setup.sh --no-tex
.venv-newclid/bin/python -m pytest -q
.venv-newclid/bin/python -m bench show problems/examples/varignon
```

To regenerate the HTML from saved runs, execute `python -m bench.publish` in the project environment. To build the paper, see [the LaTeX instructions](zpd_darbs/README.md). Serve the published HTML from any static web server.

| Directory | Contents |
|---|---|
| [ddar](ddar/) and [pipeline](pipeline/) | Deduction rules, auxiliary-point tools, search and budgets |
| [geo-lm](geo-lm/) and [models](models/registry.json) | Trained geometry models and external weight references |
| [bench](bench/) and [results](results/) | Runners, raw records and publication code |
| [problems/latvia](problems/latvia/) | Source problems, translations and review status |
| [docs](docs/README.md) | Methods, installation, CLI usage and [training](docs/training_setup.md) |
