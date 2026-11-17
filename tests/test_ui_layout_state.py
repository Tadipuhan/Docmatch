from ui_layout_state import group_check_state, responsive_split_widths


def test_parent_check_state():
    assert group_check_state([False, False]) == 0
    assert group_check_state([True, False]) == 1
    assert group_check_state([True, True]) == 2
    assert group_check_state([]) == 0


def test_responsive_split_widths():
    assert responsive_split_widths(1440, 360) == [1080, 360]
    assert responsive_split_widths(900, 360) == [540, 360]
    assert responsive_split_widths(700, 360) == [420, 280]
    assert sum(responsive_split_widths(560)) == 560
    assert responsive_split_widths(900, 999)[1] <= 440
