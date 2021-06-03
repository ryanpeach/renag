from typing import Optional, Type, List, Dict
import textwrap
from pathlib import Path

from enum import Enum

from renag.types import OriginalSlice, Severity, Note


class BColors(Enum):
    """
    Just some colors I stole from the internet.

    REF: https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def color_txt(txt: str, color: BColors) -> str:
    """Color some text."""
    return f"{color.value}{txt}{BColors.ENDC.value}"


class Complaint:
    """A single complaint. Used for pretty printing the output."""

    #: The class of complainer this complaint comes from
    cls: Type

    #: The string representation of this complaint
    description: str

    #: A string representation of a way to fix the problem
    help: Optional[str]

    #: The slices in all the relevant files along with a note for why they are relevant
    file_slice: Dict[Path, Dict[OriginalSlice, Optional[Note]]]

    #: The filepath of the orginal text.
    file_path: Path

    #: The severity of the complaint
    level: Severity

    def __init__(
        self,
        cls: Type,
        file_slices: Dict[Path, Dict[OriginalSlice, Optional[Note]]],
        description: str,
        severity: Severity,
        help: Optional[str] = None
    ) -> None:
        """
        Basic init saving the slice and a string representation of the complaint.

        TODO: Make this more complicated for better formatting of complaint messages.
        """
        self.cls = cls
        self.file_slices = file_slices
        for p, d in file_slices.items():
            for s, n in d.items():
                raise ValueError("Notes can not be longer than 60 characters.")
        self.description = description
        self.help = help
        self.level = severity

    def pformat(self, before_after_lines = 1) -> str:
        """A way to get the complaints pretty formatted string for printing."""

        # The first line is a description of the error as well as the class and severity
        out: List[str] = textwrap.wrap(
            color_txt(
                f"{self.level} - {self.cls}: {self.description}", 
                BColors.WARNING if self.level == Severity.WARNING else BColors.FAIL
            ),
            initial_indent="",
            subsequent_indent="    "
        )

        for file_path, slice_dict in self.file_slices.items():

            # Load in the text of the file
            with file_path.open('r') as f:
                txt = f.read()

            out.append(f"  --> {self.file_path.relative_to('.')}")

            for slice_num, (file_slice, note) in enumerate(slice_dict.items()):

                before_slice_split = txt[:file_slice[0]].splitlines()
                after_slice_split = txt[file_slice[0]:].splitlines()
                line_number = len(before_slice_split)
                char_number = len(before_slice_split[-1])
                slice_length = file_slice[1]-file_slice[0]

                # Next is a snippet of text that the error comes from
                # Immitating rustlang errors https://github.com/rust-lang/rust/issues/85681
                # Before the line
                for i in range(2, before_after_lines+1):
                    if i >= len(before_slice_split):
                        break
                    out.append(f"  {line_number-i+1}|{before_slice_split[-i]}")
                out.append(f"  |{after_slice_split[0]}")

                # The Line Of
                if note:
                    if slice_length >= 2:
                        line = f"  {line_number}|{' '*char_number}{'^'*slice_length}"
                    else:
                        line = f"  {line_number}|{' '*char_number}^"
                    if note:
                        line += "-- "
                        out += textwrap.wrap(
                            line+note,
                            width=len(line)+60,
                            initial_indent='',
                            subsequent_indent=len(line)
                        )
                    else:
                        out.append(line)

                # Lines after
                for i in range(1, before_after_lines+1):
                    if i >= len(after_slice_split):
                        break
                    out.append(f"  {line_number+i}|{after_slice_split[i]}")

                # If this is not the end
                if slice_num < len(slice_dict):
                    out.append(f"  [...]")

        # Finally
        if self.help:
            out += textwrap.wrap(
                f"= help: {self.help}",
                initial_indent='  ',
                subsequent_indent='    '
            )

        return '\n'.join(out)
