"""This is the primary class the user will overwrite with their own complainers."""

import logging
import re
from pathlib import Path

# REF: https://github.com/python/mypy/issues/6239
from typing import List, Optional, Union

from pyparsing import Empty, ParserElement, ParseResults, Regex

from renag.types.complaint import Complaint
from renag.types.custom_types import GlobStr, RegexStr, Severity, Span

logger = logging.getLogger(__name__)

class Complainer:
    """Emits errors when it finds specific strings."""

    #: A regex under which to check the rules of the complaint.
    #: For instance, this could be a variable declaration, or a function definition.
    #: The smaller number of unique captures you have, the faster your code will run.
    #: If you only have a capture, and no `check` method, this will define an `exists` complaint
    #: that will raise wherever this regex finds a match, and doesn't if no match is found.
    #: Defaults to "*" when passed None
    capture: Optional[Union[RegexStr, ParserElement]]

    #: Optionally define file types that this complaint runs on.
    #: For instance ["*.py"]
    #: Applies recursively through subdirectories.
    glob: List[GlobStr]

    #: Optionally define file types that this complaint will ignore
    #: For instance ["test_*.py"]
    #: Applies recursively through subdirectories.
    exclude_glob: Optional[List[GlobStr]] = None

    #: Regex options
    regex_options: Union[re.RegexFlag, int] = 0

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
        self, txt: str, path: Path, capture_span: Span, capture_data: ParseResults
    ) -> List[Complaint]:
        """
        Checks a piece of text and returns a list of complaints.

        Needs to be overwritten by the creator of each complaint.

        If it is not overwritten, the default check is whether or not the capture is found.

        The default description is the docstring of the class.

        If no complaints are found, returns an empty list.


        Parameters
        ----------
        txt : str
            The captured text itself.
        path : Path
            The path of the file being scanned.
        capture_span : Span
            A 2-Tuple containing the character indexes of the captured text within the file.
            The first int is inclusive, the second int is exclusive
        capture_data : ParseResults
            The first output of each tuple returned via `self.capture.scanString(txt)`.

        Returns
        -------
        List[Complaint]
            A list of complaints.
        """
        if not self.__doc__:
            self.__doc__ = f"This error message needs to be replaced via a docstring for this complaint: {type(self)}"

        logger.debug(
            f"Checking {type(self)}: {id(self)} on {path} at {capture_span} with {capture_data}"
        )

        return [
            Complaint(
                complainer=type(self),
                file_spans={path: {capture_span: None}},
                description=self.__doc__,
                severity=self.severity,
                help=None,
            )
        ]

    def finalize(self) -> List[Complaint]:
        """
        After this has run on all files and all captures, this allows you to return a list of complaints from the saved
        information.

        For example: Lets say you wanted to make a complainer that doesn't complain at all until all captures in the project
        are saved in some kind of dictionary internal to this complainer instance (which will persist over all files) and then
        analyzes that dictionary for bad outcomes. Like maybe you want to check for naming conflicts! Or that there are
        exactly 5 global variables for some reason. This is the place to do that.

        Returns
        -------
        List[Complaint]
            A list of complaints.
        """
        logger.debug(f"Finalizing {type(self)}: {id(self)}")
        return []

    def __hash__(self) -> int:
        """
        Hashes the complainer based on the capture string.
        Useful for putting complainers into sets and dictionaries.

        Returns
        -------
        int
            The hash of the complainer by the capture string.
        """
        return hash(self.capture)

    def get_pyparsing_capture(self: "Complainer") -> ParserElement:
        """
        Simplify the capture type to a pyparsing ParserElement.
        Strings get converted to regex.
        """
        if not self.capture:
            return Empty()
        if isinstance(self.capture, str):
            return Regex(self.capture, flags=self.regex_options)
        return self.capture
