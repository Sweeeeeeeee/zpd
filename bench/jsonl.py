"""Read completed rows and repair an interrupted final append."""
import json
from pathlib import Path


def resume_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("rb+") as stream:
        while True:
            start = stream.tell()
            line = stream.readline()
            if not line:
                break
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                if line.endswith(b"\n"):
                    raise ValueError(f"Invalid completed row at byte {start} in {path}") from None
                stream.truncate(start)
                break
            rows.append(row)
            if not line.endswith(b"\n"):
                stream.write(b"\n")
    return rows
