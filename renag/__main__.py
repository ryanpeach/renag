"""
This module runs the code from the commandline.
"""
import argparse
import importlib.util
import inspect
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
        help="A local python module or just a folder containing all complainers. "
        "The difference is that the module must contain a '__init__.py' file inside it. "
        "The module needs to supply all complainers via `from $load_module import *`.",
    )
    parser.add_argument(
        "--analyze_dir",
        type=str,
        default=".",
        help="The directory to run all globs and issue complaints about.",
    )
    parser.add_argument(
        "-n",
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

    # Handle some basic tests
    if load_module_path == Path("."):
        raise ValueError(f"load_module should be a subdirectory, not the current path.")
    if not load_module_path.is_dir():
        raise ValueError(f"{load_module_path} is not a directory.")

    # Get all complainers
    all_complainers: List[Complainer] = []

    # Check for an __init__.py
    IS_MODULE = (load_module_path / "__init__.py").is_file()

    # get complainers by loading a module with an __init__.py
    if IS_MODULE:
        # Get the relative module name
        load_module = str(load_module_path).replace(os.sep, ".")

        # Load the complainers within the module
        mod = importlib.import_module(load_module)
        for item_name in mod.__dict__:
            if not item_name.startswith("_"):
                item = getattr(mod, item_name)
                if isinstance(item, type) and issubclass(item, Complainer):
                    # Initialize the item and add it to all complainers
                    all_complainers.append(item())

    # get complainers by loading a list of files in a directory
    else:
        # For all files in the target folder.
        for file1 in load_module_path.iterdir():
            # If file starts from letter and ends with .py
            if file1.is_file() and file1.suffix == ".py":
                # Import each file as a module from it's full path.
                spec = importlib.util.spec_from_file_location(
                    ".", load_module_path.parent.absolute() / file1
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                # For each object definition that is a class.
                for _name, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, Complainer) and obj != Complainer:
                        all_complainers.append(obj())

    if not all_complainers:
        raise ValueError(f"No Complainers found in module from {load_module_path}.")

    print(color_txt("Found Complainers:", BColors.OKGREEN))
    for c in all_complainers:
        print(
            color_txt(
                "  - " + type(c).__module__ + "." + type(c).__name__, BColors.OKGREEN
            )
        )

    print(color_txt(f"Running renag analyzer on '{analyze_dir}'..", BColors.OKGREEN))

    # Get all the captures and globs of all complainers
    all_captures_files: Dict[Path, Set[ParserElement]] = defaultdict(set)
    capture_to_complainer: Dict[ParserElement, List[Complainer]] = defaultdict(list)
    complainer_to_files: Dict[Complainer, Set[Path]] = defaultdict(set)
    for complainer in all_complainers:
        # Make sure that glob is not an empty list
        if not complainer.glob:
            raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

        # Map the capture to all complainers
        capture_to_complainer[complainer.capture].append(complainer)

        # Get all the files to analyze
        all_files: Set[Path] = set()
        for g in complainer.glob:
            all_files |= set(analyze_dir.rglob(g))
        if complainer.exclude_glob:
            for g in complainer.exclude_glob:
                all_files -= set(analyze_dir.rglob(g))

        # Add all files and captures to the dicts
        for file1 in all_files:
            if isinstance(complainer.capture, str):
                complainer.capture = Regex(
                    complainer.capture, flags=complainer.regex_options
                )
            all_captures_files[file1].add(complainer.capture)
            complainer_to_files[complainer].add(file1)

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
    N_WARNINGS, N_CRITICAL = 0, 0
    for file2, captures in all_captures_files.items():
        # Check if file is staged for git commit if args.git is true
        if args.staged and file2 not in staged_files:
            continue

        # Check if file is untracked if we are in a git repo
        if (not args.include_untracked) and (file2.absolute() in untracked_files):
            continue

        # Open the file
        with file2.open("r") as f2:
            try:
                txt: str = f2.read()
            except UnicodeDecodeError:
                continue

        # Get the or of all captures
        # Then Iterate over all captures
        for capture in captures:

            # Then Get all matches in the file
            for match, start, stop in capture.scanString(txt):

                # Then iterate over all complainers
                for complainer in capture_to_complainer[capture]:

                    # Skip if this file is not specifically globbed by this complainer
                    if file2 not in complainer_to_files[complainer]:
                        continue

                    complaints = complainer.check(
                        txt=txt,
                        capture_span=(start, stop),
                        path=file2,
                        capture_data=match,
                    )

                    for complaint in complaints:
                        if complaint.severity is Severity.CRITICAL:
                            N_CRITICAL += 1
                        else:
                            N_WARNINGS += 1

                        print(
                            complaint.pformat(context_nb_lines=context_nb_lines),
                            end="\n\n",
                        )

    # In the end, we try to call .finalize() on each complainer. Its purpose is
    # to allow for complainers to have methods that will be called once, in the end.
    for complainer in all_complainers:
        if not hasattr(complainer, "finalize"):
            continue

        complaints = complainer.finalize()
        for complaint in complaints:
            if complaint.severity == Severity.CRITICAL:
                N_CRITICAL += 1
            else:
                N_WARNINGS += 1

            print(
                complaint.pformat(context_nb_lines=context_nb_lines), end="\n\n",
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
