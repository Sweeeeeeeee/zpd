"""Read the alternating name and problem lines in a Newclid benchmark."""
from pathlib import Path


def read_problems(path: Path) -> dict[str, str]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if len(lines) % 2:
        raise ValueError(f"{path}: missing problem text for {lines[-1]!r}")
    problems = {}
    for name, text in zip(lines[::2], lines[1::2], strict=True):
        if name in problems:
            raise ValueError(f"{path}: duplicate problem ID {name!r}")
        problems[name] = text
    return problems
