import pytest

from bench.jsonl import resume_rows


@pytest.mark.parametrize("suffix", [b'{"name":"b"', b'{"name":"b","word":"\xc3'])
def test_truncated_tail_can_be_retried(tmp_path, suffix):
    path = tmp_path / "records.jsonl"
    completed = b'{"name":"a"}\n'
    path.write_bytes(completed + suffix)
    assert resume_rows(path) == [{"name": "a"}]
    assert path.read_bytes() == completed


def test_valid_final_row_without_newline_is_preserved(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_bytes(b'{"name":"a"}')
    assert resume_rows(path) == [{"name": "a"}]
    assert path.read_bytes() == b'{"name":"a"}\n'


def test_invalid_completed_record_is_reported(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_bytes(b'bad\n{"name":"b"}\n')
    with pytest.raises(ValueError, match="byte 0"):
        resume_rows(path)
    assert path.read_bytes().startswith(b'bad\n')
