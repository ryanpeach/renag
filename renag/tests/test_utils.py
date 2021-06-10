"""Tests utils.py"""

import inspect

from renag.utils import get_lines_and_numbers


def test_get_line_numbers1() -> None:
    """Test that get line numbers returns lines correctly."""
    test = inspect.cleandoc(
        """
    asdf
       jksks

    fds

    """
    )
    lines, line_nums = get_lines_and_numbers(txt=test, span=(3, 10))
    assert lines == ["asdf", "   jksks"]
    assert line_nums == [0, 1]
    print()  # This shouldn't be found by print_complainers
