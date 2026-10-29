"""Build a Newclid solver for a DDARConfig.

engine "yuclid": Newclid's C++ engine (stock rules, AR on).
engine "python": Newclid's DDARN + SymPy AR with the configured rules. Newclid
3.0.1's Python engine has three bugs; they are handled here, without
modifying or monkeypatching Newclid:

1. Rules r34-r37, r52, r53, r60-r63 have premises like `diff A B C`, but
   Newclid only builds `diff` with 2 points. `diff A B C` means "pairwise
   distinct", so `prepare_rules` rewrites it as `diff A B, diff A C, diff B C`.
2. The AR length enumerator iterates a dict as if it held pairs.
   `ARDeductor` uses a corrected copy of it.
3. Rules that allow repeated points (r52, r53, ...) produce degenerate
   mappings such as `simtri e a d e a d`, which abort the whole rule.
   `SkipDegenerateMapper` skips them.
"""

from __future__ import annotations

import itertools

import sympy as sp
from newclid.api import GeometricSolverBuilder, PythonDefault
from newclid.deductors.sympy_ar import ar_predicates
from newclid.deductors.sympy_ar.algebraic_manipulator import SympyARDeductor
from newclid.numerical import close_enough
from newclid.predicate_types import PredicateArgument
from newclid.predicates._index import PredicateType
from newclid.problem import PredicateConstruction
from newclid.rule import Rule
from newclid.rule_matching.mapping_matcher import FilterMapper, MappingMatcher

from ddar.rule_config import DDARConfig


def prepare_rule(rule: Rule) -> Rule:
    """Split every `diff` with more than 2 points into pairwise `diff`s."""
    premises: list[str] = []
    for premise in rule.premises_txt:
        name, *points = premise.split()
        if name == "diff" and len(points) > 2:
            premises += [f"diff {a} {b}" for a, b in itertools.combinations(points, 2)]
        else:
            premises.append(premise)
    if len(premises) == len(rule.premises_txt):
        return rule
    return rule.model_copy(update={"premises_txt": tuple(premises)})


class SkipDegenerateMapper(FilterMapper):
    """FilterMapper that drops mappings giving an invalid premise or conclusion."""

    def mappings(self, rule, points, proof):
        for mapping in super().mappings(rule, points, proof):
            try:
                for part in rule.premises + rule.conclusions:
                    PredicateConstruction.from_predicate_type_and_args(
                        PredicateType(part.name), tuple(mapping[v] for v in part.variables)
                    )
            except (ValueError, KeyError):
                continue
            yield mapping


def enumerate_lconsts(table):
    """Newclid's ar_predicates.enumerate_lconsts, iterating `.items()`."""
    for segment, expected_length in list(table.expected_lconsts.items()):
        subbed_in = table.inner_table.substitute_in_existing_expressions(segment)
        if subbed_in.free_symbols:
            continue
        length = sp.exp(subbed_in)
        if not close_enough(float(length), expected_length):
            ar_predicates.LOGGER.error(f"Length {length} is not equal to expected length {expected_length}")
        p0, p1 = table.sympy_symbol_to_str_symbol[segment]
        points = tuple(PredicateArgument(pt.name) for pt in (p0, p1))
        length_arg = PredicateArgument(ar_predicates.fraction_to_ratio(ar_predicates.get_quotient(length)))
        yield (
            PredicateConstruction.from_predicate_type_and_args(
                PredicateType.CONSTANT_LENGTH, points + (length_arg,)
            ),
            segment,
        )


class ARDeductor(SympyARDeductor):
    """SymPy AR with the corrected length enumerator."""

    def __init__(self) -> None:
        super().__init__()
        self.ratio_enumerators = [
            enumerate_lconsts if f is ar_predicates.enumerate_lconsts else f
            for f in self.ratio_enumerators
        ]


def build_solver(problem_setup, config: DDARConfig, seed: int = 0):
    """GeometricSolver for `problem_setup`, using only the enabled rules."""
    if config.engine == "yuclid":
        from py_yuclid.api_default import HEDefault

        builder = GeometricSolverBuilder(rng=seed, api_default=HEDefault())
        return builder.with_rules(config.rules()).build(problem_setup)
    builder = GeometricSolverBuilder(rng=seed, api_default=PythonDefault(use_sympy_ar=config.ar))
    return (
        builder.with_rules([prepare_rule(r) for r in config.rules()])
        .with_rule_matcher(MappingMatcher(SkipDegenerateMapper()))
        .with_deductors([ARDeductor()] if config.ar else [])
        .build(problem_setup)
    )
