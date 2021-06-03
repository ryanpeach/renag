"""The basic Complaint class along with its pretty printing functionality."""
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Type

from renag.customtypes import BColors, Note, OriginalSlice, Severity


def _color_txt(txt: str, color: BColors) -> str:
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
        help: Optional[str] = None,
    ) -> None:
        """
        Basic init saving the slice and a string representation of the complaint.

        TODO: Make this more complicated for better formatting of complaint messages.
        """
        self.cls = cls
        self.file_slices = file_slices
        self.description = description
        self.help = help
        self.level = severity

    def pformat(self, before_after_lines: int = 1) -> str:
        """A way to get the complaints pretty formatted string for printing."""
        # The first line is a description of the error as well as the class and severity
        out: List[str] = textwrap.wrap(
            _color_txt(
                f"{self.level} - {self.cls.__name__}: {self.description}",
                BColors.WARNING if self.level == Severity.WARNING else BColors.FAIL,
            ),
            width=120,
            initial_indent="",
            subsequent_indent="    ",
        )

        for file_path, slice_dict in self.file_slices.items():

            # Load in the text of the file
            with file_path.open("r") as f:
                txt = f.read()

            out.append(f"  --> {file_path}")

            for slice_num, (file_slice, note) in enumerate(slice_dict.items()):

                before_slice_split = txt[: file_slice[0]].splitlines()
                after_slice_split = txt[file_slice[0] :].splitlines()
                if not before_slice_split:
                    line_number, char_number = 0, 0
                else:
                    line_number = len(before_slice_split) - 1
                    char_number = len(before_slice_split[0])
                slice_length = file_slice[1] - file_slice[0]

                # Next is a snippet of text that the error comes from
                # Immitating rustlang errors https://github.com/rust-lang/rust/issues/85681
                # Before the line
                for i in range(2, before_after_lines + 1):
                    if i >= len(before_slice_split):
                        break
                    out.append(f"  {line_number-i+1}| {before_slice_split[-i]}")

                # The Line Of
                out.append(
                    f"  {line_number}| {after_slice_split[0] if len(after_slice_split) == 1 else ''}"
                )
                if note:
                    if slice_length >= 2:
                        line = f"  {line_number}| {' '*char_number}{'^'*slice_length}"
                    else:
                        line = f"  {line_number}| {' '*char_number}^"
                    if note:
                        line += "-- "
                        out += textwrap.wrap(
                            line + note,
                            width=len(line) + 60,
                            initial_indent="",
                            subsequent_indent=" " * len(line),
                        )
                    else:
                        out.append(line)

                # Lines after
                for i in range(1, before_after_lines + 2):
                    if i >= len(after_slice_split):
                        break
                    out.append(f"  {line_number+i}| {after_slice_split[i]}")

                # If this is not the end
                if slice_num < len(slice_dict):
                    out.append(f"  [...]")

        # Finally
        if self.help:
            out += textwrap.wrap(
                f"= help: {self.help}", initial_indent="  ", subsequent_indent="    "
            )

        return "\n".join(out)
