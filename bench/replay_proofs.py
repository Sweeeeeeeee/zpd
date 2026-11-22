"""Replay the winning constructions in a sweep with deduction alone.

python -m bench.replay_proofs DATASET SWEEP.jsonl PROOFS.jsonl
"""
import argparse
import json
from pathlib import Path

from bench.dataset import read_problems
from pipeline.solve import Budget, solve
from pipeline.tools import AuxConstruction, ProofState


def replay(dataset, records):
    problems = read_problems(dataset)
    for line in records.read_text().splitlines():
        row = json.loads(line)
        if not row["solved"]:
            continue
        state = ProofState.from_text(problems[row["name"]])
        for aux in row["aux"]:
            state = state.child(AuxConstruction(tuple(aux["clauses"]), aux["source"]))
        result = solve(state.text(), "pipeline/configs/ddar_only.json", Budget(time_s=60))
        if not result.solved or not result.proof or result.ddar_calls != 1:
            raise ValueError(f"Proof replay failed for {row['name']}: {result.failure_reason}")
        yield {"name": row["name"], "problem_with_aux": state.text(),
               "proof": result.proof, "rules_in_proof": result.rules_in_proof}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    proofs = list(replay(args.dataset, args.records))
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in proofs))
    print(f"Replayed {len(proofs)} proofs")


if __name__ == "__main__":
    main()
