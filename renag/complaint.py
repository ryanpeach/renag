"""The basic Complaint class along with its pretty printing functionality."""
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Type

from renag.custom_types import BColors, Note, Severity, Span
from renag.utils import color_txt, get_line_sep


class Complaint:
    """A single complaint. Used for pretty printing the output."""

    #: The class of complainer this complaint comes from
    cls: Type

    #: The string representation of this complaint
    description: str

    #: A string representation of a way to fix the problem
    help: Optional[str]

    #: The spans in all the relevant files along with a note for why they are relevant
    file_spans: Dict[Path, Dict[Span, Optional[Note]]]

    #: The filepath of the orginal text.
    file_path: Path

    #: The severity of the complaint
    severity: Severity

    def __init__(
        self,
        cls: Type,
        file_spans: Dict[Path, Dict[Span, Optional[Note]]],
        description: str,
        severity: Severity,
        help: Optional[str] = None,
    ) -> None:
        """
        Basic init saving the slice and a string representation of the complaint.

        TODO: Make this more complicated for better formatting of complaint messages.
        """
        self.cls = cls
        self.file_spans = file_spans
        self.description = description
        self.help = help
        self.severity = severity

    def pformat(self, context_nb_lines: int = 1) -> str:
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

        for file_num, (file_path, slice_dict) in enumerate(self.file_spans.items()):

            # Load in the text of the file
            with file_path.open("r") as f:
                txt = f.read()

            txt_split = txt.splitlines()
            numbered_txt_split = list(enumerate(txt_split))

            # Add a new line if in long mode
            if context_nb_lines > 0:
                out.append(" ")

            for slice_num, (file_slice, note) in enumerate(sorted(slice_dict.items())):
                linesep = get_line_sep(txt)
                txt_slice = txt[file_slice[0] : file_slice[1]]
                is_multiline_check = linesep in txt_slice
                first_line_number = txt[: file_slice[0]].count(linesep)
                last_line_number = txt_slice.count(linesep) + first_line_number
                try:
                    left_indent: int = max(
                        0, file_slice[0] - txt[: file_slice[0]].rindex(linesep) - 1
                    )
                except ValueError:
                    left_indent = max(0, file_slice[0] - 1)
                try:
                    right_indent: int = txt[file_slice[1] :].index(linesep)
                except ValueError:
                    right_indent = 0
                slice_length = file_slice[1] - file_slice[0]
                left, right = left_indent, left_indent + slice_length
                if is_multiline_check:
                    last_line_distance_to_end_of_slice = len(
                        txt_slice
                    ) - txt_slice.rindex(linesep)
                # print(left, right)  # This is a debug statement. It should be captured by EasyPrintComplainer but not by ComplexPrintComplainer

                # Print line numbers
                if (context_nb_lines == 0 and file_num == 0) or context_nb_lines > 0:
                    out[-1] += " --> "
                out[-1] += color_txt(
                    str(file_path.relative_to(str(Path(".").absolute()))),
                    BColors.HEADER,
                )
                if not is_multiline_check:
                    out[-1] += color_txt(
                        f"[{first_line_number}:{left}]", BColors.HEADER
                    )
                else:
                    out[-1] += color_txt(
                        f"[{first_line_number}:{left} to {last_line_number}:{last_line_distance_to_end_of_slice}]",
                        BColors.HEADER,
                    )
                if context_nb_lines == 0 and file_num < len(self.file_spans) - 1:
                    out[-1] += ", "

                # Short Mode
                if context_nb_lines == 0:
                    continue

                # Next is a snippet of text that the error comes from
                # Immitating rustlang errors https://github.com/rust-lang/rust/issues/85681
                # Before the line
                for this_line_num, line in numbered_txt_split[
                    max(0, first_line_number - context_nb_lines) : first_line_number
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
                                f"{str(this_line_num).rjust(6)}| {' '*left_indent}{color_txt('^'*(len(line)-left_indent-1), BColors.OKCYAN)}"
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
                    last_line_number + 1 : last_line_number + 1 + context_nb_lines
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
