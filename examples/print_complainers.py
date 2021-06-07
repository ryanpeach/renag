"""An example of a very simple complainer."""

from pyparsing import Literal, QuotedString, nestedExpr, restOfLine

from renag import Complainer, Severity


class EasyPrintComplainer(Complainer):
    """Print statements can slow down code."""

    capture = r"(?<=\s|^)print\s*(?=\()"  # An example of pure regex
    severity = Severity.WARNING
    glob = ["*.py"]


class ComplexPrintComplainer(Complainer):
    """Print statements can slow down code."""

    capture = (
        (Literal("print") + nestedExpr("(", ")"))
        .ignore("#" + restOfLine)
        .ignore(QuotedString('"', multiline=False))
        .ignore(QuotedString("'", multiline=False))
        .ignore(QuotedString('"""', multiline=True))
        .ignore(QuotedString("'''", multiline=True))
    )  # An example of pyparsing
    severity = Severity.WARNING
    glob = ["*.py"]
