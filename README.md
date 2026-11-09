# Olympiad geometry scanner

Finds olympiad geometry problems that have an easy solution in one geometry
domain (a set of theorems): provable by Newclid's DDAR with that domain's
rules, at most one auxiliary point, 60 s and 2 GB. Auxiliary points come from
human heuristics and a small transformer trained from scratch on CPU.

| where | what |
|---|---|
| [docs/README.md](docs/README.md) | overview, installation, usage, folder map |
| [docs/apraksts.md](docs/apraksts.md) | project description (Latvian) |
| [docs/tasks.md](docs/tasks.md) | task list and progress |
| [docs/rezultati.md](docs/rezultati.md) | current results (Latvian) |
| [zpd_darbs/](zpd_darbs/README.md) | the written ZPD paper (LaTeX) |
| [claude/LOG.md](claude/LOG.md) | work log: what was done in each session, where to continue |

```bash
bash setup.sh                             # fresh machine: env, data, TeX, tests (runs by itself in a new Codespace)
.venv-newclid/bin/python -m pytest -q     # 85 tests
```
