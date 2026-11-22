"""Justify a shared line or circle from the incidence facts already in a proof."""
from itertools import combinations

from newclid.justifications._index import JustificationError
from newclid.justifications.justification import DirectConsequence
from newclid.predicates.collinearity import Coll, NColl
from newclid.predicates.cyclic import Cyclic
from newclid.predicates.different import Diff
from newclid.proof_state import ProofState


def shared_points_witness(common, circle):
    """Two distinct points determine a line, three noncollinear points a circle."""
    for points in combinations(sorted(common, key=lambda p: p.name), 3 if circle else 2):
        distinct = Diff(points=points)
        if distinct.check_numerical():
            if not circle:
                return distinct
            noncollinear = NColl(points=points)
            if noncollinear.check_numerical():
                return noncollinear
    return None


def merge_justification(goal, known, symbol):
    target = set(goal.points)
    components = []
    for fact in known:
        if type(fact) is not type(goal):
            continue
        points = set(fact.points)
        if not points <= symbol.points:
            continue
        premises = [fact]
        while not target <= points:
            for i, (other, support) in enumerate(components):
                if points <= other:
                    points, premises = other, support
                elif not other <= points:
                    witness = shared_points_witness(points & other, isinstance(goal, Cyclic))
                    if witness is None:
                        continue
                    points.update(other)
                    premises.extend([*support, witness])
                components.pop(i)
                break
            else:
                break
        if target <= points:
            return DirectConsequence(predicate=goal, premises=tuple(dict.fromkeys(premises)))
        components.append((points, premises))
    raise JustificationError(f"No chain of known incidence facts proves {goal}")


class IncidenceProofState(ProofState):
    def justify(self, predicate):
        if isinstance(predicate, (Coll, Cyclic)) and predicate not in self.graph.hyper_graph:
            points = set(predicate.points)
            if isinstance(predicate, Coll):
                symbol = self.symbols.lines.line_containing(points)
            else:
                symbol = self.symbols.circles.circle_containing(points)
            if symbol is None:
                raise JustificationError(f"No registered line or circle contains {predicate}")
            reason = merge_justification(predicate, self.graph.hyper_graph, symbol)
            if not self.apply(reason):
                raise JustificationError(f"Incidence conclusion failed validation: {predicate}")
            return reason
        return super().justify(predicate)
