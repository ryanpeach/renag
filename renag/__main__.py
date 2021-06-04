"""
This module runs the code from the commandline.
"""
import argparse
import importlib
import inspect
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from iregex import Regex

from renag.complainer import Complainer
from renag.custom_types import BColors, GlobStr, RegexStr, Severity, Span
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

    # load_module_path = Path(args.load_module).relative_to(".")
    load_module_path: Path = Path(args.load_module).absolute()
    analyze_dir: Path = Path(args.analyze_dir).absolute()
    context_nb_lines = max(int(args.n), 0)

    all_complainers: List[Complainer] = []
    # For all files in the target folder.
    for file in os.listdir(load_module_path):
        # If file starts from letter and ends with .py
        if file[0].isalpha() and file.endswith(".py"):
            # Import each file as a module from it's full path.
            spec = importlib.util.spec_from_file_location(".", load_module_path / file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # For each object definition that is a class.
            for _name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Complainer) and obj != Complainer:
                    all_complainers.append(obj())

    # print("Found Complainers:")
    # for c in all_complainers:
    #     print(f"  - ({load_module_path.parent}) {type(c).__name__}")

    if not all_complainers:
        raise ValueError(f"No Complainers found in module from {load_module_path}.")

    # Get all the captures and globs of all complainers
    all_captures_globs: Dict[GlobStr, Set[RegexStr]] = defaultdict(set)
    capture_to_complainer: Dict[RegexStr, List[Complainer]] = defaultdict(list)
    for complainer in all_complainers:
        # Make sure that glob is not an empty list
        if not complainer.glob:
            raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

        # Map the capture to all complainers
        capture_to_complainer[str(complainer.capture)].append(complainer)

        # Add all globs and captures to the dict
        for g in complainer.glob:
            all_captures_globs[g].add(str(complainer.capture))

    # Iterate over all captures and globs
    N_WARNINGS, N_CRITICAL = 0, 0
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
                    for match in (
                        Regex(capture).compile(re.MULTILINE | re.DOTALL).finditer(txt)
                    ):
                        span: Span = match.span()

                        # Then iterate over all complainers
                        for complainer in capture_to_complainer[str(capture)]:

                            complaints = complainer.check(
                                txt=txt, capture_span=span, path=file
                            )

                            for complaint in complaints:
                                if complaint.severity == Severity.CRITICAL:
                                    N_CRITICAL += 1
                                else:
                                    N_WARNINGS += 1

                                print(
                                    complaint.pformat(
                                        context_nb_lines=context_nb_lines
                                    ),
                                    end="\n\n",
                                )

    # End by exiting the program
    N = N_WARNINGS + N_CRITICAL
    if not N:
        print(color_txt("Renag finished with no complaints.", BColors.OKGREEN))
        exit(0)

    print(
        color_txt(
            f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.",
            BColors.WARNING,
        )
    )

    # If has critical errors - exit with non-zero code..
    if N_CRITICAL != 0:
        exit(1)
    # ..else quit early.
    exit(0)


if __name__ == "__main__":
    main()
