"""DDAR configuration: which rules are enabled and whether AR is on.

Config file (JSON):

    {
      "name": "no_similarity",
      "engine": "python",
      "enabled_rules": "default",
      "disabled_rules": ["r34", "r35", "r52", "r53"],
      "ar": true
    }

* `enabled_rules` is a list of rule ids, or "default" (Newclid's 58 default
  rules) or "all" (all 87 rules ever defined in Newclid).
* `disabled_rules` (optional) is removed from `enabled_rules` afterwards.
* `ar` turns algebraic reasoning (angle and ratio chasing) on or off.
* `engine` is "python" (Newclid's DDARN, patched; honours every setting) or
  "yuclid" (Newclid's C++ engine; its rules are compiled in, so it only
  accepts the default rules with AR on).

Rules are filtered at load time: the engine only ever sees the enabled ones.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Union

from newclid.all_rules import ALL_RULES, DEFAULT_RULES
from newclid.rule import Rule

RuleSelection = Union[list[str], Literal["default", "all"]]

RULES_BY_ID: dict[str, Rule] = {r.id: r for r in ALL_RULES}

# Predicates the SymPy AR deductor reads and writes
# (SympyARDeductor._table_for_predicate).
AR_PREDICATES = {
    "coll", "eqangle", "aconst", "para", "perp",  # angle table
    "lconst", "rconst", "cong", "eqratio",  # ratio table
}

# Checked numerically on the figure; no rule is needed to use them.
NUMERICAL_PREDICATES = {
    "diff", "ncoll", "npara", "nperp", "nsameside", "obtuse_angle",
    "sameclock", "sameside",
}


class RuleCoverageWarning(UserWarning):
    pass


@dataclass
class DDARConfig:
    name: str = "default"
    engine: Literal["python", "yuclid"] = "python"
    enabled_rules: RuleSelection = "default"
    disabled_rules: list[str] = field(default_factory=list)
    ar: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> DDARConfig:
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        config = cls(**data)
        config.validate()
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> DDARConfig:
        data = json.loads(Path(path).read_text())
        data.setdefault("name", Path(path).stem)
        return cls.from_dict(data)

    def validate(self) -> None:
        if self.engine not in ("python", "yuclid"):
            raise ValueError(f"engine must be 'python' or 'yuclid', got {self.engine!r}")
        if isinstance(self.enabled_rules, str):
            if self.enabled_rules not in ("default", "all"):
                raise ValueError(
                    "enabled_rules must be a list of ids, 'default' or 'all',"
                    f" got {self.enabled_rules!r}"
                )
        else:
            _check_ids(self.enabled_rules, "enabled_rules")
        _check_ids(self.disabled_rules, "disabled_rules")
        if self.engine == "yuclid" and not self.is_stock():
            raise ValueError(
                "engine 'yuclid' has its rules and AR compiled in: use"
                " enabled_rules='default', no disabled_rules and ar=true,"
                " or switch to engine 'python'"
            )

    def is_stock(self) -> bool:
        return self.enabled_rules == "default" and not self.disabled_rules and self.ar

    def rule_ids(self) -> list[str]:
        if self.enabled_rules == "default":
            ids = {r.id for r in DEFAULT_RULES}
        elif self.enabled_rules == "all":
            ids = set(RULES_BY_ID)
        else:
            ids = set(self.enabled_rules)
        return sorted(ids - set(self.disabled_rules))

    def rules(self) -> list[Rule]:
        """The enabled rules, sorted by id, as passed to the engine."""
        return [RULES_BY_ID[i] for i in self.rule_ids()]


def _check_ids(ids: list[str], key: str) -> None:
    unknown = [i for i in ids if i not in RULES_BY_ID]
    if unknown:
        raise ValueError(
            f"{key}: unknown rule ids {unknown}. Known ids: r00-r92"
            " (see newclid/all_rules.py; some numbers are unused)"
        )


def rule_predicates(rule: Rule) -> tuple[set[str], set[str]]:
    """(premise predicate names, conclusion predicate names) of a rule."""
    return {p.name for p in rule.premises}, {c.name for c in rule.conclusions}


def construction_predicates() -> dict[str, list[str]]:
    """Predicate name -> construction names whose hypotheses use it.

    Newclid 3.x has no defs.txt; the constructions live in
    newclid/jgex/constructions as JGEXDefinition objects.
    """
    from newclid.jgex.constructions import ALL_JGEX_CONSTRUCTIONS

    used: dict[str, list[str]] = {}
    for definition in ALL_JGEX_CONSTRUCTIONS:
        for clause in definition.clauses:
            for construction in clause.constructions:
                used.setdefault(construction.name, []).append(definition.name.value)
    return used


def coverage_warnings(config: DDARConfig) -> list[str]:
    """Explain what disabling rules (or AR) cuts off: hypotheses produced by
    constructions that nothing can use any more, and predicates that nothing
    can prove any more. The reference is what the config would give without
    disabling anything: Newclid's default rules plus any extra rules listed."""
    enabled = config.rules()
    base = DDARConfig(enabled_rules=config.enabled_rules).rules()
    reference = sorted(set(base) | set(DEFAULT_RULES), key=lambda r: r.id)
    ar = AR_PREDICATES if config.ar else set()

    def consumers(rules: list[Rule], pred: str) -> list[str]:
        return [r.id for r in rules if pred in rule_predicates(r)[0]]

    def producers(rules: list[Rule], pred: str) -> list[str]:
        return [r.id for r in rules if pred in rule_predicates(r)[1]]

    messages: list[str] = []
    for pred, constructions in sorted(construction_predicates().items()):
        if pred in NUMERICAL_PREDICATES or pred in ar:
            continue
        lost = consumers(reference, pred)
        if lost and not consumers(enabled, pred):
            names = ", ".join(sorted(set(constructions))[:6])
            more = "" if len(set(constructions)) <= 6 else ", ..."
            messages.append(
                f"no enabled rule uses '{pred}' as a premise (enable one of"
                f" {lost}); hypotheses from constructions [{names}{more}] will"
                " be ignored by the deduction"
            )

    every_conclusion = {c for r in reference for c in rule_predicates(r)[1]}
    every_conclusion -= {"pythagorean_conclusions"}  # internal helper predicate
    for pred in sorted(every_conclusion - NUMERICAL_PREDICATES - ar):
        if not producers(enabled, pred):
            messages.append(
                f"no enabled rule concludes '{pred}' (enable one of"
                f" {producers(reference, pred)}); goals of that type can only"
                " hold if they are hypotheses"
            )
    if not config.ar:
        messages.append(
            "AR is off: angle and ratio chasing are disabled, so facts that need"
            " them (sums of angles, ratio products, ...) must come from rules"
        )
    return messages


def load_config(path: str | Path, warn: bool = True) -> DDARConfig:
    """Load and validate a config; emit RuleCoverageWarning for each problem."""
    config = DDARConfig.from_json(path)
    if warn:
        for message in coverage_warnings(config):
            warnings.warn(f"[{config.name}] {message}", RuleCoverageWarning, stacklevel=2)
    return config
