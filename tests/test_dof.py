"""pipeline.dof: degrees of freedom of a translation (hidden-specialisation check, task 7.5)."""

from pipeline.dof import check_file, count


def test_general_triangle_has_two_shape_parameters():
    assert count("a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d")["shape"] == 2


def test_point_on_side_adds_one_and_intersection_adds_none():
    p = "a b c = triangle a b c; d = on_line d b c; e = on_line e a c, on_pline e d a b ? para d e a b"
    assert count(p)["shape"] == 3


def test_special_triangle_is_caught(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("# dof: 2  (any triangle)\na b c = iso_triangle a b c; m = midpoint m b c ? perp a m b c\n")
    ok, msg = check_file(f)
    assert ok is False and "MISMATCH" in msg


def test_unknown_construction_is_reported():
    assert count("a b c = triangle a b c; x = made_up x a b ? coll a b x")["unknown"] == ["made_up"]
