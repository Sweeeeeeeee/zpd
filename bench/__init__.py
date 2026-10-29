"""Problem collection + stored solve() results, kept in git.

Layout:
    problems/<set>/<name>.txt        one problem: header comments + JGEX line
    results/<set>/<name>.json        every solve() result for that problem

Problem file:
    # Varignon: the midpoints of the sides of any quadrilateral form a parallelogram.
    # source: classical
    # tags: midpoints, parallel
    a b c d = quadrangle a b c d; e = midpoint e a b; ... ? para e f g h

`# key: value` lines are metadata; other `#` lines form the description.

A result record holds what is worth knowing about the problem under one
setting: the config name and its settings (tools, DDAR rules and AR, search
limits), the resources available and used (time, memory, CPU, DDAR calls),
and the outcome (solved, failure reason, depth, auxiliary points, tools and
rules used, proof). There is one record per config and budget; nothing about
the particular run (date, commit, machine) is stored.
"""

from bench.store import (  # noqa: F401
    Problem,
    settings_summary,
    load_problems,
    load_records,
    run,
)
