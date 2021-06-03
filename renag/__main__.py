"""
This module runs the code from the commandline.
"""

import argparse
import importlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from iregex import Regex

from renag.complainer import Complainer
from renag.customtypes import (
    GlobStr,
    OriginalSlice,
    OriginalTxt,
    PartialTxt,
    RegexStr,
    Severity,
)

# ================= Utilities ===============


def _askyn(question: str, default: Optional[bool] = None) -> bool:
    """
    Asks a yes or no question and returns a bool.
    REF: https://gist.github.com/garrettdreyfus/8153571
    """
    # Modify the question with the default value capitalized
    if default is not None:
        if default:
            question += " [Y/n]: "
        else:
            question += " [y/N]: "
    else:
        question += " [y/n]: "

    # Iterate until an answer is determined
    while True:
        reply = str(input(question).lower().strip())
        if reply == "" and default is not None:
            return default
        elif reply in ("y", "yes"):
            return True
        if reply in ("n", "no"):
            return False
        else:
            print(f"Unrecognized answer: '{reply}'")


def main(load_module: str, analyze_dir: Path, context_n_lines: int) -> None:
    """Runs all Complainers found in `load_dir` on all files found in `analyze_dir` recursive."""


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
    default=1,
    help="The number of lines before and after an error to show in context.",
)
args = parser.parse_args()
args.analyze_dir = Path(args.analyze_dir).absolute()
if not args.analyze_dir.is_dir():
    raise ValueError(f"{args.analyze_dir} is not a directory.")

load_module_path = Path(args.load_module).relative_to(".")
analyze_dir = Path(args.analyze_dir).absolute()
context_n_lines = max(int(args.n), 1)

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
if "__all__" not in mod.__dict__:
    raise KeyError(
        f"Please define an __all__ variable inside {load_module_path / '__init__.py'} referencing all of your Complainers. Please refer to https://docs.python.org/3/tutorial/modules.html#importing-from-a-package for help on this matter."
    )
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

# Get all the contexts and globs of all complainers
all_contexts_globs: Dict[GlobStr, Set[RegexStr]] = defaultdict(set)
context_to_complainer: Dict[RegexStr, List[Complainer]] = defaultdict(list)
for complainer in all_complainers:
    # Make sure that glob is not an empty list
    if not complainer.glob:
        raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

    # Map the context to all complainers
    context_to_complainer[str(complainer.context)].append(complainer)

    # Add all globs and contexts to the dict
    for g in complainer.glob:
        all_contexts_globs[g].add(str(complainer.context))

# Iterate over all contexts and globs
exitcode: int = 0
N, N_WARNINGS, N_CRITICAL = 0, 0, 0
for glob, contexts in all_contexts_globs.items():

    # First get all files in the glob
    for file in analyze_dir.rglob(glob):
        if file.is_file():

            # Open the file
            with file.open("r") as f:
                try:
                    txt = OriginalTxt(f.read())
                except UnicodeDecodeError:
                    continue

            # Then Iterate over all contexts
            for context in contexts:

                # Then Get all matches in the file
                for match in Regex(context).compile().finditer(txt):
                    original_slice: OriginalSlice = match.span()

                    # Then iterate over all complainers
                    for complainer in context_to_complainer[str(context)]:

                        complaints = complainer.check(
                            context_txt=PartialTxt(
                                txt[original_slice[0] : original_slice[1]]
                            ),
                            original_slice=original_slice,
                            file_path=file,
                        )

                        for complaint in complaints:
                            N += 1
                            if complaint.severity is Severity.CRITICAL:
                                N_CRITICAL += 1
                                exitcode = 1
                            else:
                                N_WARNINGS += 1
                                exitcode = max(exitcode, 0)

                            print(complaint.pformat(before_after_lines=context_n_lines))
                            print()

# End by exiting the program
if N == 0:
    print("No complaints. Enjoy the rest of your day!")
else:
    print(f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.")
exit(exitcode)
