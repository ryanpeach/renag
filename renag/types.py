"""Where all types for typing are declared."""

from enum import Enum, IntEnum
from typing import NewType, Tuple, Union

from iregex import Regex

#: Represents an index in the original string.
OriginalIdx = NewType("OriginalIdx", int)

#: Represents an index in a partial section of the original string.
PartialIdx = NewType("PartialIdx", int)

#: Represents a slice in the original index.
#: Last index is inclusive
OriginalSlice = Tuple[OriginalIdx, OriginalIdx]

#: Represents a slice in the partial index.
#: Last index is inclusive
PartialSlice = Tuple[PartialIdx, PartialIdx]

#: Represents the original text.
OriginalTxt = NewType("OriginalTxt", str)

#: Represents a partial section of the original text.
PartialTxt = NewType("PartialTxt", str)

#: Any string representing Regex
RegexStr = str

#: Represents any regex type
AnyRegex = Union[RegexStr, Regex]

#: A string to glob for files with
GlobStr = str

#: A short string representing an inline note
Note = str


class Severity(IntEnum):
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
