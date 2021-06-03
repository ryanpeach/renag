"""The basic Complaint class along with its pretty printing functionality."""
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Type

from renag.customtypes import BColors, Note, OriginalSlice, Severity


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
    severity: Severity

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
        self.severity = severity

    def pformat(self, before_after_lines: int = 1) -> str:
        """A way to get the complaints pretty formatted string for printing."""
        # The first line is a description of the error as well as the class and severity
        out: List[str] = textwrap.wrap(
            color_txt(
                f"{self.severity} - {self.cls.__name__}: {self.description}",
                BColors.WARNING if self.severity == Severity.WARNING else BColors.FAIL,
            ),
            width=120,
            initial_indent="",
            subsequent_indent="    ",
        )

        for file_path, slice_dict in self.file_slices.items():

            # Load in the text of the file
            with file_path.open("r") as f:
                txt = f.read()

            txt_split = txt.splitlines()
            numbered_txt_split = list(enumerate(txt_split))

            out.append(f"  --> {file_path.relative_to(str(Path('.').absolute()))}")

            for slice_num, (file_slice, note) in enumerate(sorted(slice_dict.items())):
                is_multiline_check = "\n" in txt[file_slice[0] : file_slice[1]]
                first_line_number = txt[: file_slice[0]].count("\n")
                last_line_number = (
                    txt[file_slice[0] : file_slice[1]].count("\n") + first_line_number
                )
                left_indent = file_slice[0] - txt[: file_slice[0]].rindex("\n") - 1
                right_indent = txt[file_slice[1] :].index("\n")
                slice_length = file_slice[1] - file_slice[0]
                left, right = left_indent, left_indent + slice_length

                # Next is a snippet of text that the error comes from
                # Immitating rustlang errors https://github.com/rust-lang/rust/issues/85681
                # Before the line
                for this_line_num, line in numbered_txt_split[
                    max(0, first_line_number - before_after_lines) : first_line_number
                ]:
                    out.append(f"{str(this_line_num).rjust(6)}| {line}")

                # The Lines of
                for this_line_num, line in numbered_txt_split[
                    first_line_number : (last_line_number + 1)
                ]:
                    if not is_multiline_check:
                        out.append(
                            f"{str(this_line_num).rjust(6)}| {line[:left]}{color_txt(line[left:right], BColors.OKCYAN)}{line[right:]}"
                        )
                        out.append(
                            f"{str(this_line_num).rjust(6)}| {' '*left_indent}{color_txt('^'*slice_length, BColors.OKCYAN)}"
                        )
                    else:
                        if this_line_num == first_line_number:
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {line[:left]}{color_txt(line[left:], BColors.OKCYAN)}"
                            )
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {' '*left_indent}{color_txt('^'*(len(line)-left_indent), BColors.OKCYAN)}"
                            )
                        elif this_line_num == last_line_number:
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {color_txt(line[:right], BColors.OKCYAN)}{line[right:]}"
                            )
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {color_txt('^'*(len(line)-right_indent), BColors.OKCYAN)}"
                            )
                        else:
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {color_txt(line, BColors.OKCYAN)}"
                            )
                            out.append(
                                f"{str(this_line_num).rjust(6)}| {color_txt('^'*len(line), BColors.OKCYAN)}"
                            )

                if note:
                    line = out.pop()
                    out += textwrap.wrap(
                        line + " --> " + color_txt(note, BColors.OKBLUE),
                        width=len(out[-1]) + 60,
                        initial_indent="",
                        subsequent_indent=" " * len(line),
                    )

                # Lines after
                for this_line_num, line in numbered_txt_split[
                    last_line_number + 1 : last_line_number + 1 + before_after_lines
                ]:
                    out.append(f"{str(this_line_num).rjust(6)}| {line}")

                # If this is not the end
                if slice_num < len(slice_dict) - 1:
                    out.append(f"  [...]")

        # Finally
        if self.help:
            out += textwrap.wrap(
                f"= help: {self.help}", initial_indent="  ", subsequent_indent="    "
            )

        return "\n".join(out)
