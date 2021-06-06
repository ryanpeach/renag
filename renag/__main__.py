"""
This module runs the code from the commandline.
"""
import argparse
import importlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Union

import regex
from iregex import Regex
from pyparsing import ParserElement

from renag.complainer import Complainer
from renag.custom_types import BColors, GlobStr, RegexStr, Severity
from renag.utils import color_txt


def main() -> None:
    """Main function entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--load_module",
        type=str,
        default=".complainers",
        help="A local python module (folder) containing all complainers. "
        "A directory with an __init__.py inside it. "
        "The module needs to supply all complainers via `from $load_module import *`.",
    )
    parser.add_argument(
        "--analyze_dir",
        type=str,
        default=".",
        help="The directory to run all globs and issue complaints about.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=5,
        help="The number of lines before and after an error to show in context.",
    )
    args = parser.parse_args()
    args.analyze_dir = Path(args.analyze_dir).absolute()
    if not args.analyze_dir.is_dir():
        raise ValueError(f"{args.analyze_dir} is not a directory.")

    load_module_path = Path(args.load_module).relative_to(".")
    analyze_dir = Path(args.analyze_dir).absolute()
    context_nb_lines = max(int(args.n), 1)

    # Check for an __init__.py
    path_ = load_module_path
    if path_ == Path("."):
        raise ValueError(f"load_module should be a subdirectory, not the current path.")
    if not path_.is_dir():
        raise ValueError(f"{path_} is not a directory.")
    while path_ != Path("."):
        if not (path_ / "__init__.py").is_file():
            raise ValueError(
                f"{(load_module_path / '__init__.py')} does not exist. Should be a python module."
            )
        path_ = path_.parent

    # Get the relative module name
    load_module = str(load_module_path).replace(os.sep, ".")

    mod = importlib.import_module(load_module)
    all_complainers: List[Complainer] = []
    for item_name in mod.__dict__:
        if not item_name.startswith("_"):
            item = getattr(mod, item_name)
            if isinstance(item, type) and issubclass(item, Complainer):
                # Initialize the item and add it to all complainers
                all_complainers.append(item())

    print("Found Complainers:")
    for c in all_complainers:
        print("  - " + type(c).__module__ + "." + type(c).__name__)

    if not all_complainers:
        raise ValueError(f"No Complainers found in module {load_module}.")

    # Get all the captures and globs of all complainers
    all_captures_globs: Dict[
        GlobStr, Set[Union[RegexStr, Regex, ParserElement]]
    ] = defaultdict(set)
    capture_to_complainer: Dict[
        Union[RegexStr, Regex, ParserElement], List[Complainer]
    ] = defaultdict(list)
    for complainer in all_complainers:
        # Make sure that glob is not an empty list
        if not complainer.glob:
            raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

        # Map the capture to all complainers
        capture_to_complainer[complainer.capture].append(complainer)

        # Add all globs and captures to the dict
        for g in complainer.glob:
            all_captures_globs[g].add(complainer.capture)

    # Iterate over all captures and globs
    N, N_WARNINGS, N_CRITICAL = 0, 0, 0
    for glob, captures in all_captures_globs.items():

        # First get all files in the glob
        for file in analyze_dir.rglob(glob):
            if file.is_file():

                # Open the file
                with file.open("r") as f:
                    try:
                        txt: str = f.read()
                    except UnicodeDecodeError:
                        continue

                # Then Iterate over all captures
                for capture in captures:

                    # Then Get all matches in the file
                    if isinstance(capture, str):
                        iterator = (
                            (int(match.start()), int(match.end()))
                            for match in regex.compile(
                                capture, regex.MULTILINE | regex.DOTALL
                            ).finditer(txt)
                        )
                    elif isinstance(capture, Regex):
                        # Do this to make Regex support the regex library instead of re
                        iterator = (
                            (int(match.start()), int(match.end()))
                            for match in regex.compile(
                                str(capture), regex.MULTILINE | regex.DOTALL
                            ).finditer(txt)
                        )
                    elif isinstance(capture, ParserElement):
                        iterator = (
                            (int(start), int(stop))
                            for _, start, stop in capture.scanString(txt)
                        )
                    else:
                        raise TypeError(f"Unrecognized type: {type(capture)}")
                    for span in iterator:

                        # Then iterate over all complainers
                        for complainer in capture_to_complainer[capture]:

                            complaints = complainer.check(
                                txt=txt, capture_span=span, path=file,
                            )

                            for complaint in complaints:
                                N += 1
                                if complaint.severity is Severity.CRITICAL:
                                    N_CRITICAL += 1
                                else:
                                    N_WARNINGS += 1

                                print(
                                    complaint.pformat(context_nb_lines=context_nb_lines)
                                )
                                print()

    # End by exiting the program
    if N == 0:
        print(color_txt("No complaints. Enjoy the rest of your day!", BColors.OKGREEN))
        exit(0)
    if N_WARNINGS > 0 and N_CRITICAL == 0:
        print(
            color_txt(
                f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.",
                BColors.WARNING,
            )
        )
        exit(0)
    print(
        color_txt(
            f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.",
            BColors.WARNING,
        )
    )
    exit(1)


if __name__ == "__main__":
    main()
