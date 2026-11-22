import subprocess
import sys
from pathlib import Path

import pytest

from bench.dataset import read_problems


@pytest.mark.parametrize(("data", "message"), [
    ("case1\na ? b\ncase2\n", "missing problem text"),
    ("case1\na ? b\ncase1\nc ? d\n", "duplicate problem ID"),
])
def test_malformed_dataset_is_reported(tmp_path, data, message):
    file = tmp_path / "dataset.txt"
    file.write_text(data)
    with pytest.raises(ValueError, match=message):
        read_problems(file)


def test_unknown_filter_fails_before_creating_output(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.write_text("case1\na ? b\n")
    keep = tmp_path / "ids"
    keep.write_text("case2\n")
    output = tmp_path / "run.jsonl"
    result = subprocess.run(
        [sys.executable, "bench/sweep.py", str(dataset), "pipeline/configs/ddar_only.json",
         str(output), "--only", str(keep)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
    )
    assert result.returncode != 0 and "case2" in result.stderr
    assert not output.exists()
