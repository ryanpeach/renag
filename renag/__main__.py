"""
This module runs the code from the commandline.
"""
import argparse
import importlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

import git
from pyparsing import ParserElement, Regex

from renag.complainer import Complainer
from renag.custom_types import BColors, Severity
from renag.utils import color_txt


def main() -> None:
    """Main function entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--load_module",
        type=str,
        default="./complainers",
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
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Only glob files that are staged for git commit.",
    )
    parser.add_argument(
        "--include_untracked",
        action="store_true",
        help="Also include untracked files from git in glob.",
    )
    args = parser.parse_args()
    args.analyze_dir = Path(args.analyze_dir).absolute()
    if not args.analyze_dir.is_dir():
        raise ValueError(f"{args.analyze_dir} is not a directory.")

    load_module_path = Path(args.load_module).relative_to(".")
    analyze_dir = Path(args.analyze_dir).absolute()
    context_nb_lines = max(int(args.n), 0)

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
    all_captures_files: Dict[Path, Set[ParserElement]] = defaultdict(set)
    capture_to_complainer: Dict[ParserElement, List[Complainer]] = defaultdict(list)
    for complainer in all_complainers:
        # Make sure that glob is not an empty list
        if not complainer.glob:
            raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

        # Map the capture to all complainers
        capture_to_complainer[complainer.capture].append(complainer)

        # Add all globs and captures to the dict
        all_files: Set[Path] = set()
        for g in complainer.glob:
            all_files |= set(analyze_dir.rglob(g))
        if complainer.exclude_glob:
            for g in complainer.exclude_glob:
                all_files -= set(analyze_dir.rglob(g))
        for file in all_files:
            if file.is_file():
                if isinstance(complainer.capture, str):
                    complainer.capture = Regex(
                        complainer.capture, flags=complainer.regex_options
                    )
                all_captures_files[file].add(complainer.capture)

    # Get git repo information
    try:
        repo = git.Repo()
    except:  # noqa: E722  I don't know what this might return if there isn't a git repo
        staged_files: Set[Path] = set()
        untracked_files: Set[Path] = set()
    else:
        if args.staged:
            staged_files_diffs = repo.index.diff("HEAD")
            staged_files = {
                Path(repo.working_tree_dir) / diff.b_path for diff in staged_files_diffs
            }
        else:
            staged_files = set()
        untracked_files = {Path(path).absolute() for path in repo.untracked_files}

    # Iterate over all captures and globs
    N, N_WARNINGS, N_CRITICAL = 0, 0, 0
    for file, captures in all_captures_files.items():

        # Check if file is staged for git commit if args.git is true
        if args.staged and file not in staged_files:
            continue

        # Check if file is untracked if we are in a git repo
        if (not args.include_untracked) and (file.absolute() in untracked_files):
            continue

        # Open the file
        with file.open("r") as f:
            try:
                txt: str = f.read()
            except UnicodeDecodeError:
                continue

        # Get the or of all captures
        # Then Iterate over all captures
        for capture in captures:

            # Then Get all matches in the file
            for match, start, stop in capture.scanString(txt):

                # Then iterate over all complainers
                for complainer in capture_to_complainer[capture]:

                    complaints = complainer.check(
                        txt=txt,
                        capture_span=(start, stop),
                        path=file,
                        capture_data=match,
                    )

                    for complaint in complaints:
                        N += 1
                        if complaint.severity is Severity.CRITICAL:
                            N_CRITICAL += 1
                        else:
                            N_WARNINGS += 1

                        print(complaint.pformat(context_nb_lines=context_nb_lines))
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
