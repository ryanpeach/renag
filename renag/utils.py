"""Just some basic utils mostly for internal use, but some can be helpful for writing custom complainers as well."""

from typing import List, Optional, Tuple

from renag.custom_types import BColors, Span


def color_txt(txt: str, color: BColors) -> str:
    """Color some text."""
    return f"{color.value}{txt}{BColors.ENDC.value}"


def get_line_sep(txt: str) -> str:
    r"""Gets the line seperator in a block of text. Defaults to \n"""
    if "\r\n" in txt:
        linesep = "\r\n"
    elif "\r" in txt:
        linesep = "\r"
    else:
        linesep = "\n"
    return linesep


def get_lines_and_numbers(txt: str, span: Span) -> Tuple[List[str], List[int]]:
    """
    Gets the line numbers from some text and a span.

    Returns a list of lines (represented as strings) and a list of line numbers (represented as int).
    """
    linesep = get_line_sep(txt)
    first_line_num = txt[: span[0]].count(linesep)
    last_line_num = first_line_num + txt[span[0] : span[1]].count(linesep)
    try:
        first_line_index: Optional[int] = txt[: span[0]].rindex(linesep) + 1
    except ValueError:
        first_line_index = None
    try:
        last_line_index: Optional[int] = txt[span[1] :].index(linesep) + span[1]
    except ValueError:
        last_line_index = None
    section = txt[first_line_index:last_line_index].splitlines()
    return section, list(range(first_line_num, last_line_num + 1))


def askyn(question: str, default: Optional[bool] = None) -> bool:
    """
    Asks a yes or no question and returns a bool.
    REF: https://gist.github.com/garrettdreyfus/8153571
    """
    # Modify the question with the default value capitalized
    if default is not None:
        if default:
            question += " [Y/n]: "
        else:
            question += " [y/N]: "
    else:
        question += " [y/n]: "

    # Iterate until an answer is determined
    while True:
        reply = str(input(question).lower().strip())
        if reply == "" and default is not None:
            return default
        elif reply in ("y", "yes"):
            return True
        if reply in ("n", "no"):
            return False
        else:
            print(f"Unrecognized answer: '{reply}'")
