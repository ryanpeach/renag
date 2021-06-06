from pathlib import Path
from typing import List

from iregex import Regex

from renag import Complainer, Complaint, Severity, Span, get_lines_and_numbers


class EasyPrintComplainer(Complainer):
    capture = Regex("print").whitespace() + (Regex("\(").make_lookahead())
    severity = Severity.WARNING
    glob = ["*.py"]


class ComplexPrintComplainer(Complainer):
    capture = Regex("print").whitespace() + (Regex("\(").make_lookahead())
    severity = Severity.WARNING
    glob = ["*.py"]

    def __init__(self):
        self.cache = list()

    def check(self, txt: str, path: Path, capture_span: Span) -> List[Complaint]:
        """Check that the print statement is not commented out before complaining."""
        # Get the line number
        lines, line_numbers = get_lines_and_numbers(txt, capture_span)

        # Check on the first line of the capture_span that the capture is not preceded by a '#'
        # In such a case, the print has been commented out
        if lines[0].count("#") > 0 and lines[0].index("#") < capture_span[0]:

            # If it is the case that the print was commented out, we do not need to complain
            # So we will return an empty list of complaints
            return []

        # Otherwise we will do as normal
        self.cache.extend(super().check(txt=txt, path=path, capture_span=capture_span))
        return []

    def finalize(self) -> List[Complaint]:
        return self.cache
