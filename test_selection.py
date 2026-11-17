import pytest

from erome_dl.selection import parse_selection


def test_single_list_and_range():
    assert parse_selection("3", 10) == [3]
    assert parse_selection("1,4,7", 10) == [1, 4, 7]
    assert parse_selection("3-6", 10) == [3, 4, 5, 6]


def test_mixed_reversed_and_duplicates():
    assert parse_selection("1, 3-5, 4, 9", 10) == [1, 3, 4, 5, 9]
    assert parse_selection("6-4", 10) == [4, 5, 6]


@pytest.mark.parametrize("bad", ["", "abc", "1,x", "0", "11", "2-", "-3", "1-99"])
def test_bad_input(bad):
    with pytest.raises(ValueError):
        parse_selection(bad, 10)
