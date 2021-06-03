"""This is the primary class the user will overwrite with their own complainers."""

from pathlib import Path
from typing import List

from renag.complaint import Complaint
from renag.customtypes import AnyRegex, GlobStr, OriginalSlice, PartialTxt, Severity


class Complainer:
    """Emits errors when it finds specific strings."""

    #: A context under which to check the rules of the complaint.
    #: For instance, this could be a variable declaration, or a function definition.
    #: The smaller number of contexts you have, the faster your code will run.
    #: If you only have a context, and no `check` method, this will define an `exists` complaint
    #: that will raise wherever this regex finds a match, and doesn't if no match is found.
    #: Defaults to "*" when passed None
    context: AnyRegex

    #: Optionally define file types that this complaint runs on.
    #: For instance ["*.py"]
    #: Applies recursively through subdirectories.
    #: Defaults to ["*"] when passed None
    glob: List[GlobStr]

    #: WARNING: Will return exit code 0, but will still print a warning.
    #: CRITICAL: Will return exit code 1
    severity: Severity = Severity.CRITICAL

    def __init__(self) -> None:
        """
        A simple init function that can be used to create private attributes.

        Useful for referencing the text of other necessary files, like config files.

        Only runs once.
        """
        pass

    def check(
        self, context_txt: PartialTxt, original_slice: OriginalSlice, file_path: Path,
    ) -> List[Complaint]:
        """
        Checks a piece of text and returns a list of complaints.

        Needs to be overwritten by the creator of each complaint.

        If it is not overwritten, the default check is whether or not the context is found,
        and the default description is the docstring of the class.

        If no complaints are found, return an empty list.
        """
        if not self.__doc__:
            self.__doc__ = f"This error message needs to be replaced via a docstring for this complaint: {type(self)}"

        return [
            Complaint(
                file_slices={file_path: {original_slice: None}},
                cls=type(self),
                description=self.__doc__,
                help=None,
                severity=self.severity,
            )
        ]
