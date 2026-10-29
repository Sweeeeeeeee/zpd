# Step 6: Toolbox and the first pipeline

## The tool interface (`tools.py`)

```python
class Tool(ABC):
    name: str
    def run(self, state: ProofState) -> list[AuxConstruction] | None: ...
```

A tool takes the current proof state and returns either nothing or new auxiliary
constructions. An `AuxConstruction` is a tuple of Newclid (JGEX) clauses, such as
`("e = foot e a b c",)`, together with the name of the tool that proposed it and
a score.

| tool | class | returns |
|---|---|---|
| DDAR | `tools.DDARTool` | nothing. It runs Newclid's DDAR on the state and records solved, proof, rules fired and the numeric figure. Its options are a step 2 DDAR config, so rule toggling and AR on/off apply here too. |
| transformer | `transformer_tool.TransformerTool` | the model's beam-search hypotheses (deterministic), translated to JGEX clauses |
| heuristics | `tools.HeuristicsTool` | midpoints, circumcenters and feet of altitudes. Candidates touching more goal points come first, ties are broken alphabetically, and points that coincide with existing ones are skipped |

The transformer's input and output use the GenesisGeo predicate format.
`translate.py` converts both ways:
* **Input:** the checked Newclid problem becomes predicates per point, with
  points renamed a, b, c, ...
* **Output:** each predicate on the new point becomes a one-locus construction:
  * `coll` becomes `on_line`;
  * `perp` becomes `on_tline` or `on_dia`;
  * `para` becomes `on_pline`;
  * `cong` becomes `on_circle`, `on_bline` or `eqdistance`;
  * `cyclic` becomes `on_circum`.

  Hypotheses that use other predicates (`eqangle`, `aconst`, ...) are dropped.

## The pipeline (`search.py`)

1. Run DDAR on the problem until it stops. If the problem is solved, stop.
2. Ask the proposer tools, in `proposer_order`, for constructions. Keep the
   first `branching` distinct ones.
3. Add each construction and run DDAR again. Stop at the first solved state.
4. Repeat from the unsolved results (at most `max_frontier`) until `max_depth`.

Limits: `max_depth`, `branching`, `max_frontier`, `max_ddar_calls` and
`time_limit` (seconds). Nothing is sampled at random.

```bash
.venv-newclid/bin/python -m pipeline.search --config pipeline/configs/default.json \
    -s "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c"
# add --json for the full result: solved, proof, depth, aux (with source tool),
# rules fired / in proof, tool calls, DDAR calls, wall time, failure reason
```

## Config

```json
{
  "tools": {
    "ddar":        {"enabled": true,  "options": {"config": "ddar/configs/yuclid.json"}},
    "transformer": {"enabled": true,  "options": {"checkpoint": "geo-lm/runs/small/best.pt", "beam_size": 4}},
    "heuristics":  {"enabled": false, "options": {"kinds": ["foot"], "max_candidates": 8}}
  },
  "proposer_order": ["transformer", "heuristics"],
  "search": {"max_depth": 2, "branching": 8, "max_frontier": 6, "max_ddar_calls": 80, "time_limit": 0}
}
```

* `enabled: false` switches a tool off.
* `"class": "my_pkg.my_module:MyTool"` replaces a tool with any `Tool`
  subclass. Its `options` are passed to the class constructor.
* Configs provided: `default.json` (needs a trained model), `heuristics_only.json`,
  `ddar_only.json`, and `tiny_model.json` (uses the step 5 smoke checkpoint).

## Adding a tool

```python
from pipeline.tools import AuxConstruction, Tool

class ReflectionTool(Tool):
    name = "reflections"
    def run(self, state):
        if state.problem_setup is None:   # DDAR has not checked this state
            return None
        return [AuxConstruction(("x = mirror x a b",), self.name)]
```

Then add it to the config:
`"reflections": {"enabled": true, "class": "my_tools:ReflectionTool"}`, and list
it in `proposer_order`.

## Status

The wiring has been run end to end with the 60-step smoke model: DDAR → proposals
→ DDAR, including proposals rejected because they break the figure. The real
model (`geo-lm/configs/train_small.json`) still has to be trained before the
transformer tool proposes anything useful. When the search fails, the result
shows the first state of the last frontier.
