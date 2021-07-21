"""Shows an example of comparing between two files."""

import re
from pathlib import Path
from typing import Any, List

from iregex import ALPHA_NUMERIC, WHITESPACE, AnyChar, OneOrMore

from renag import Complainer, Complaint, Span, get_lines_and_numbers
from renag.custom_types import Severity


class ReadmeReferenceComplainer(Complainer):
    """Checks if a class is in the readme."""

    capture = str(
        "class" + OneOrMore(WHITESPACE) + OneOrMore(AnyChar(ALPHA_NUMERIC, "_")) + ":"
    )  # An example of iregex
    # capture = "class\s+[A-Za-z0-9_]+:"
    glob = ["*.py"]
    severity = Severity.WARNING

    def __init__(self) -> None:
        """Reading in README for future use."""
        # Lets save the text of the readme for future use.
        # We will do this in the __init__ statement so it only has to be read from disk once.
        # The path will be relative to the directory `renag` is run in.
        # Which should always be project root.
        with Path("README.md").open("r") as f:
            self.README: str = f.read()

    def check(
        self, txt: str, path: Path, capture_span: Span, capture_data: Any
    ) -> List[Complaint]:
        """Check that the README contains a reference to this class."""
        # Get the line number
        lines, line_numbers = get_lines_and_numbers(txt, capture_span)

        # In python a class definition can only take up one line
        # Lets also get rid of indentation
        assert len(lines) == 1, f"More than one line detected: {lines}"
        line, line_number = lines[0].strip(), line_numbers[0]

        # Now lets get the class name
        _, name, *_ = re.split("[\s:]", line)

        # Now we will search the README (which we got from __init__)
        # for at least one instance of name surrounded in whitespace so it's full word
        if re.search(f"\s{name}\s", self.README):

            # If we do find something, return an empty list of complaints
            return []

        # If we don't find anything, return a single complaint referencing this class and it's capture_span.
        else:
            return [
                Complaint(
                    cls=type(self),
                    file_spans={
                        path: {capture_span: None},
                        Path("./README.md"): {
                            (
                                self.README.index("# Complainers"),
                                self.README.index("# Complainers")
                                + len("# Complainers"),
                            ): "Add it here."
                        },
                    },
                    description="Not found in README.md",
                    severity=self.severity,
                    help=None,
                )
            ]
