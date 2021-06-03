"""Some helpful regex variables that these complainers use."""

from iregex import Regex
from iregex.consts import ALPHA, ALPHA_NUMERIC

# A valid variable, type, class, or function name
NAME = (
    Regex()
    .literal(ALPHA)
    .literal(Regex().any_char("_", ALPHA_NUMERIC).zero_or_more_repititions())
)

# The left hand side of a variable declaration
LVALUE = (
    (NAME + Regex().whitespace())
    .m_or_more_repititions(2)
    .make_named_capture_group("lvalue")
    .whitespace()
    .literal("=")
    .anything()
    .literal(";")
)

# The right hand side of a variable declaration
RVALUE = (
    (NAME + Regex().whitespace())
    .m_or_more_repititions(2)
    .literal("=")
    .make_named_capture_group("rvalue")
    .literal(";")
)

# A full variable declaration
DECLARATION = (
    (NAME + Regex().whitespace())
    .m_or_more_repititions(2)
    .literal("=")
    .anything()
    .literal(";")
)
