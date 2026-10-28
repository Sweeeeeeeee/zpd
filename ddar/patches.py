"""Runtime fixes for bugs in Newclid 3.0.1's pure-Python engine.

All three are still present on Newclid's GitHub main (commit ac65507). Each
fix is a small wrapper, applied once by `apply_patches()`; the installed
package itself is not modified.

1. `predicate_from_construction` builds `diff` with exactly 2 points, but rules
   r34-r37, r52, r53 and r60-r63 have premises like `diff A B C`.
2. `enumerate_lconsts` iterates a dict as if it held (key, value) pairs.
3. Rules with `allow_point_repetition` (r52, r53, ...) produce mappings such as
   `simtri e a d e a d`, which fail validation and abort the whole rule.
   Such mappings are now skipped.
"""

from __future__ import annotations

import sys

_applied = False


def apply_patches() -> None:
    global _applied
    if _applied:
        return
    _fix_multi_point_diff()
    _fix_enumerate_lconsts()
    _fix_degenerate_mappings()
    _applied = True


def _fix_multi_point_diff() -> None:
    import newclid.api  # noqa: F401  (load every module that imports the function)
    import newclid.predicates as preds
    from newclid.predicates._index import PredicateType
    from newclid.predicates.different import Diff

    original = preds.predicate_from_construction

    def fixed(construction, points_registry):
        if construction.predicate_type == PredicateType.DIFFERENT:
            args = tuple(sorted(construction.args))
            return Diff(points=tuple(points_registry.names2points(args)))
        return original(construction, points_registry)

    # Modules imported the function by name, so rebind it everywhere.
    for mod in list(sys.modules.values()):
        if getattr(mod, "predicate_from_construction", None) is original:
            mod.predicate_from_construction = fixed


def _fix_enumerate_lconsts() -> None:
    from newclid.deductors.sympy_ar import algebraic_manipulator as am
    from newclid.deductors.sympy_ar import ar_predicates as arp

    import sympy as sp
    from newclid.numerical import close_enough
    from newclid.predicates._index import PredicateType
    from newclid.predicate_types import PredicateArgument
    from newclid.problem import PredicateConstruction

    original = arp.enumerate_lconsts

    def fixed(table):
        # Same as the original, but iterating `.items()`.
        for segment, expected_length_value in list(table.expected_lconsts.items()):
            subbed_in = table.inner_table.substitute_in_existing_expressions(segment)
            if subbed_in.free_symbols:
                continue
            length = sp.exp(subbed_in)
            if not close_enough(float(length), expected_length_value):
                arp.LOGGER.error(
                    f"Length {length} is not equal to expected length {expected_length_value}"
                )
            p0, p1 = table.sympy_symbol_to_str_symbol[segment]
            points = tuple(PredicateArgument(pt.name) for pt in (p0, p1))
            length_arg = PredicateArgument(
                arp.fraction_to_ratio(arp.get_quotient(length))
            )
            yield (
                PredicateConstruction.from_predicate_type_and_args(
                    PredicateType.CONSTANT_LENGTH, points + (length_arg,)
                ),
                segment,
            )

    arp.enumerate_lconsts = fixed
    if getattr(am, "enumerate_lconsts", None) is original:
        am.enumerate_lconsts = fixed


def _fix_degenerate_mappings() -> None:
    from newclid.predicates._index import PredicateType
    from newclid.problem import PredicateConstruction
    from newclid.rule_matching.mapping_matcher import FilterMapper

    original = FilterMapper.mappings

    def mappings(self, rule, points, proof):
        for mapping in original(self, rule, points, proof):
            try:
                for part in rule.premises + rule.conclusions:
                    PredicateConstruction.from_predicate_type_and_args(
                        PredicateType(part.name),
                        tuple(mapping[v] for v in part.variables),
                    )
            except (ValueError, KeyError):
                continue
            yield mapping

    FilterMapper.mappings = mappings
