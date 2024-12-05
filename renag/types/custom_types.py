"""Where all types for typing are declared."""
from enum import Enum
from typing import Tuple

#: Represents a the beginning and end of a section of string.
#: First int is inclusive, second int is exclusive
Span = Tuple[int, int]

#: Any string representing Regex
RegexStr = str

#: A string to glob for files with
GlobStr = str

#: A short string representing an inline note
Note = str


class Severity(Enum):
    """
    An enum representing the severity of the complaint.

    Warnings will represent complaints that will not result in an exitcode 1.

    Critical will represent complaints that will result in an exitcode 1.
    """

    WARNING = 0
    CRITICAL = 1


class BColors(Enum):
    """
    Just some colors I stole from the internet.

    REF: https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
    """

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
