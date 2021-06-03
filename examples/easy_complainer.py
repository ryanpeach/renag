"""An example of a very simple complainer."""

from renag import Complainer, Severity


class EasyComplainer(Complainer):
    """Find all print statements."""

    context = r"print\(.*\)"
    level = Severity.WARNING
