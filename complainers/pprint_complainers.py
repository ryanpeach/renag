"""An example of a very simple complainer."""

from pyparsing import Literal, QuotedString, nestedExpr, restOfLine

from renag import Complainer, Severity


class UsePformatInstead(Complainer):
    """Use pformat and print instead of pprint."""

    capture = (
        (Literal("pprint") + nestedExpr("(", ")"))
        .ignore("#" + restOfLine)
        .ignore(QuotedString('"', multiline=False))
        .ignore(QuotedString("'", multiline=False))
        .ignore(QuotedString('"""', multiline=True))
        .ignore(QuotedString("'''", multiline=True))
    )  # An example of pyparsing
    severity = Severity.WARNING
    glob = ["*.py"]
    exclude_glob = ["test_*.py"]
