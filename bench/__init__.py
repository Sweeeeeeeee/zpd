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

A result record holds the solve() return value plus what produced it: config
name, a hash of the config contents (including the DDAR rule config it
points to), the budget, the git commit and the date. Running the same
problem with the same config hash and budget again is skipped unless forced,
so the results files only grow when something changed.
"""

from bench.store import (  # noqa: F401
    Problem,
    config_fingerprint,
    load_problems,
    load_records,
    run,
)
