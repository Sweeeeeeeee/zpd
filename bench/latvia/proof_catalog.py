"""Index the printed premises, rule applications and goals in the original DD-AR proofs."""
from collections import Counter
from html import escape
import re
from statistics import median

from bench.latvia.paired_ar import records

FACT = re.compile(r"^\[([CN]\d+)\] : (.+)$", re.MULTILINE)
STEP = re.compile(r"(\d+)\. \| (.*?) =\((.+?)\)> (.+) \[(\d+)\]")
PREMISE = re.compile(r"(.*?) \[([CN]?\d+)\](?:, |$)")
GOAL = re.compile(r"(.+) : Proved \[(\d+)\]")


def anchor(name):
    return "proof-" + name.removeprefix("latvia/").replace("/", "-")


def parse_proof(row, audited_steps):
    setup, rest = row["proof"].split("# Goals\n", 1)
    targets, rest = rest.split("# Proof:", 1)
    proof = rest.partition("# Appendix:")[0]
    initial = FACT.findall(setup)
    facts = dict(initial)
    audit = {str(item["step"]): item for item in audited_steps}
    if len(facts) != len(initial) or len(audit) != len(audited_steps):
        raise ValueError(f"Repeated fact or audit ID in {row['name']}")
    steps = {}
    rules = Counter()
    depths = {}
    for line in proof.strip().splitlines():
        match = STEP.fullmatch(line)
        if not match:
            raise ValueError(f"Unrecognized proof step in {row['name']}: {line}")
        number, premises, printed_rule, conclusion, key = match.groups()
        if int(number) != int(key) or key in facts:
            raise ValueError(f"Invalid step ID {key} in {row['name']}")
        refs = PREMISE.findall(premises)
        if ", ".join(f"{text} [{ref}]" for text, ref in refs) != premises:
            raise ValueError(f"Unparsed premises in {row['name']}, step {key}")
        for text, ref in refs:
            if facts.get(ref) != text:
                raise ValueError(f"Incorrect cited fact [{ref}] in {row['name']}, step {key}")
        check = audit.pop(key, None)
        if printed_rule == "AR Deduction":
            if not check or check["goal"] != conclusion:
                raise ValueError(f"Missing or inconsistent AR audit in {row['name']}, step {key}")
            rule_id = "AR:" + check["kind"].lower()
        else:
            if check:
                raise ValueError(f"Unexpected AR audit in {row['name']}, step {key}")
            rule_id = printed_rule.split(" ", 1)[0]
        rules[rule_id] += 1
        facts[key] = conclusion
        refs = [ref for _, ref in refs]
        depths[key] = 1 + max((depths.get(ref, 0) for ref in refs), default=0)
        steps[key] = dict(conclusion=conclusion, refs=refs, rule=printed_rule, audit=check)
    goals = []
    for line in targets.strip().splitlines():
        match = GOAL.fullmatch(line)
        if not match or match[2] not in steps or facts[match[2]] != match[1]:
            raise ValueError(f"Goal differs from its proof in {row['name']}")
        goals.append(match[2])
    if not goals or audit or dict(rules) != row["rules_in_proof"]:
        raise ValueError(f"Rule, audit or goal count mismatch in {row['name']}")
    # Walk backward from every goal, counting shared intermediate facts once.
    todo = goals.copy()
    reachable = set()
    while todo:
        key = todo.pop()
        if key in steps and key not in reachable:
            reachable.add(key)
            todo.extend(steps[key]["refs"])
    return dict(initial=initial, steps=steps, goals=goals, rules=dict(rules),
                used_steps=len(reachable), chain=max(depths[g] for g in goals))


def catalog(path, checked_steps):
    originals = records(path, "full-deduction")
    wins = {name for name, row in originals.items() if row["solved"]}
    checks = {row["name"]: row["steps"] for row in checked_steps}
    if set(checks) != wins or len(checks) != len(checked_steps):
        raise ValueError("Original proof IDs differ from the AR audit")
    proofs = {n: parse_proof(originals[n], checks[n]) for n in sorted(wins)}
    step_counts = [len(p["steps"]) for p in proofs.values()]
    by_rule = Counter()
    by_case = Counter()
    for p in proofs.values():
        by_rule.update(p["rules"])
        by_case.update(p["rules"].keys())
    summary = dict(proofs=len(proofs), goals=sum(len(p["goals"]) for p in proofs.values()),
                   steps=sum(step_counts), steps_reaching_goals=sum(p["used_steps"] for p in proofs.values()),
                   minimum_steps=min(step_counts), median_steps=median(step_counts), maximum_steps=max(step_counts),
                   longest_chain=max(p["chain"] for p in proofs.values()),
                   rules={r: {"steps": by_rule[r], "proofs": by_case[r]} for r in sorted(by_rule)})
    return proofs, summary


def render(name, proof, label, path):
    slug = escape(anchor(name), quote=True)
    def ref(key):
        return f'<a href="#{slug}-{key}">[{key}]</a>'
    def fact(key, content):
        return f'<li id="{slug}-{key}"><span class="fact-id">[{key}]</span> {content}</li>'
    def audit_note(step):
        check = step["audit"]
        if not check:
            return ""
        if check["outcome"] == "follows":
            note = "Follows from the printed equations."
        elif check.get("additional_construction_equations"):
            extra = ", ".join(escape(x) for x in check["additional_construction_equations"])
            note = f"Follows after adding construction facts: {extra}."
        elif check["outcome"] == "needs_context":
            note = "Further context required for this printed inference."
        else:
            note = "The printed premises are inconsistent in this equation check."
        return f' <span class="proof-audit">{note}</span>'
    goals = " · ".join(f'{escape(proof["steps"][k]["conclusion"])} {ref(k)}' for k in proof["goals"])
    facts = "".join(fact(key, escape(text)) for key, text in proof["initial"])
    steps = []
    for key, step in proof["steps"].items():
        links = " ".join(ref(k) for k in step["refs"])
        rule = step["rule"] if not step["audit"] else step["audit"]["kind"] + " chasing"
        steps.append(fact(key, f'<strong>{escape(step["conclusion"])}</strong>'
                          f'<span class="proof-reason">{escape(rule)} · {links}</span>{audit_note(step)}'))
    rules = " · ".join(f'{escape(k)} × {v}' for k, v in sorted(proof["rules"].items()))
    return (
        f'<details class="proof" id="{slug}"><summary>{escape(label)}</summary>'
        f'<p><strong>Goal</strong> {goals}</p><p class="note">{len(steps)} numbered steps · '
        f'{proof["chain"]} on the longest cited chain · <a href="#{slug}">Link to proof</a> · '
        f'<a href="https://github.com/Sweeeeeeeee/zpd/blob/main/{escape(path, quote=True)}">Problem statement</a></p>'
        f'<h4>Assumptions and numerical checks</h4><ul class="facts">{facts}</ul>'
        f'<h4>Recorded deductions</h4><ol class="facts">{"".join(steps)}</ol>'
        f'<p class="note">Rules in this proof: {rules}.</p></details>'
    )
