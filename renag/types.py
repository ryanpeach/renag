from pathlib import Path

from typing import NewType, Tuple, Union

from enum import IntEnum

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
Node = str

class Severity(IntEnum):
    """
    An enum representing the severity of the complaint.

    Warnings will represent complaints that will not result in an exitcode 1.

    Critical will represent complaints that will result in an exitcode 1.
    """
    WARNING = 0
    CRITICAL = 1



