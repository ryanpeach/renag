"""
This module runs the code from the commandline.
"""
import argparse
from dataclasses import dataclass
import importlib.util
import inspect
from logging import Logger
import os
from collections import defaultdict
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Set

from pyparsing import Empty, ParserElement, Regex

from renag.complainer import Complainer
from renag.complaint import Complaint
from renag.custom_types import BColors, Severity
from renag.utils import color_txt

try:
    import git
except ImportError:
    # Note: This is not an issue since we suppress all errors from git call below.
    git = None
    print(
        color_txt(
            "There was an error importing 'git' module! Please make sure that 'git' "
            "is available in your $PATH or $GIT_PYTHON_GIT_EXECUTABLE. Note: because "
            "of this, any git-related flags will not work!",
            BColors.WARNING,
        )
    )

def get_logger(severity: Severity) -> Logger:
    """Returns a logger with the appropriate severity."""
    import logging

    logger = logging.getLogger("renag")
    logger.setLevel(severity)
    return logger

logger = get_logger(Severity.DEBUG)

def main() -> None:
    """
    Main function entrypoint.
    Parses arguments and prints the complaints.
    """
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
        "--inline",
        action="store_true",
        help="Enable this option with zero chosen lines ('-n=0') to show error inline.",
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print out DEBUG level logs.",
    )

    args = parser.parse_args()

    # Overwrite the global logger if verbose is set
    if args.verbose:
        global logger
        logger = get_logger("INFO")

    args.analyze_dir = Path(args.analyze_dir).absolute()
    if not args.analyze_dir.is_dir():
        raise ValueError(f"{args.analyze_dir} is not a directory.")

    LOAD_MODULE_PATH = Path(args.load_module).relative_to(".")
    ANALYZE_DIR = Path(args.analyze_dir).absolute()
    CONTEXT_NB_LINES = max(int(args.n), 0)

    # Handle some basic tests
    if LOAD_MODULE_PATH == Path("."):
        raise ValueError(f"load_module should be a subdirectory, not the current path.")

    if not LOAD_MODULE_PATH.is_dir():
        raise ValueError(f"{LOAD_MODULE_PATH} is not a directory.")

    # Index the file system
    cidx = ComplainerIndex(LOAD_MODULE_PATH, ANALYZE_DIR)
    gitidx = GitIndex()

    # Parse the files and iterate over discovered complaints
    # Print them directly to stderr
    for complaint in parse_files(staged_only=args.staged, include_untracked=args.include_untracked, gitidx=gitidx, cidx=cidx):
        if complaint.severity == Severity.CRITICAL:
            N_CRITICAL += 1
        else:
            N_WARNINGS += 1
        print(
            complaint.pformat(
                context_nb_lines=CONTEXT_NB_LINES, inline_mode=args.inline
            ),
            file=sys.stderr,
            end="\n\n",
        )

    N = N_WARNINGS + N_CRITICAL
    if not N:
        logger.info(color_txt("Renag finished with no complaints.", BColors.OKGREEN))
        exit(0)

    logger.info(
        color_txt(
            f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.",
            BColors.WARNING,
        )
    )

    # If has critical errors - exit with non-zero code..
    if N_CRITICAL != 0:
        exit(1)
    # ..else quit quietly.
    exit(0)

@dataclass
class GitIndex:
    """
    Calculates staged files and untracked files in the current git repo.
    """
    staged_files: Set[Path]
    untracked_files: Set[Path]

    def __init__(self):
        # Initialize variables
        self.staged_files: Set[Path] = set()
        self.untracked_files: Set[Path] = set()

        # Get git repo information
        try:
            repo = git.Repo()
        except:  # noqa: E722  I don't know what this might return if there isn't a git repo
            pass
        else:
            staged_files_diffs = repo.index.diff("HEAD")
            self.staged_files = {
                Path(repo.working_tree_dir) / diff.b_path for diff in staged_files_diffs
            }
            self.untracked_files = {Path(path).absolute() for path in repo.untracked_files}


@dataclass
class ComplainerIndex:
    """
    Gets all the complainers in the current repository.
    Indexes them by the files they access and vice versa.
    """
    all_complainers: List[Complainer]
    file_to_complainers: Dict[Path, Set[Complainer]]
    capture_to_complainer: Dict[ParserElement, List[Complainer]]
    complainer_to_files: Dict[Complainer, Set[Path]]

    def __init__(self, LOAD_MODULE_PATH: Path, ANALYZE_DIR: Path):
        self.__load_complainers(LOAD_MODULE_PATH)
        self.__index_files_by_complainer(ANALYZE_DIR)

    def __load_complainers(self, LOAD_MODULE_PATH):
        """
        Load a list of all complainers from either a complainers folder or module.
        """
        # Get all complainers
        self.all_complainers = []

        # Check for an __init__.py
        IS_MODULE = (LOAD_MODULE_PATH / "__init__.py").is_file()

        # get complainers by loading a module with an __init__.py
        if IS_MODULE:
            # Get the relative module name
            load_module = str(LOAD_MODULE_PATH).replace(os.sep, ".")

            # Load the complainers within the module
            mod = importlib.import_module(load_module)
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Complainer) and obj != Complainer:
                    # Initialize the item and add it to all complainers
                    self.all_complainers.append(obj())

        # get complainers by loading a list of files in a directory
        else:
            # For all files in the target folder.
            for file1 in LOAD_MODULE_PATH.iterdir():
                # If file starts from letter and ends with .py
                if file1.is_file() and file1.suffix == ".py":
                    # Import each file as a module from it's full path.
                    spec = importlib.util.spec_from_file_location(
                        ".", LOAD_MODULE_PATH.absolute() / file1.name
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore

                    # For each object definition that is a class.
                    for _, obj in inspect.getmembers(mod, inspect.isclass):
                        if issubclass(obj, Complainer) and obj != Complainer:
                            self.all_complainers.append(obj())

        if not self.all_complainers:
            raise ValueError(
                f"No Complainers found in module from {LOAD_MODULE_PATH.absolute()}."
            )

        logger.info(color_txt("Found Complainers:", BColors.OKGREEN))
        for c in self.all_complainers:
            logger.info(
                color_txt(f"  - {type(c).__module__}.{type(c).__name__}", BColors.OKGREEN)
            )


    def __index_files_by_complainer(self, ANALYZE_DIR: Path):
        """
        Indexes all the files that each complainer accesses.
        """
        logger.info(color_txt(f"Running renag analyzer on '{ANALYZE_DIR}'..", BColors.OKGREEN))

        self.file_to_complainers = defaultdict(set)
        self.capture_to_complainer = defaultdict(list)
        self.complainer_to_files = defaultdict(set)

        # Get all the captures and globs of all complainers
        for complainer in self.all_complainers:
            # Make sure that glob is not an empty list
            if not complainer.glob:
                raise ValueError(f"Empty glob inside {complainer}: {complainer.glob}")

            # Avoid later issue with complainer.capture being empty for the 'Regex' from pyparsing.
            # Note: Has to do it this early, because below we start mapping it to the complainers by capture.
            if isinstance(complainer.capture, str) and not complainer.capture:
                complainer.capture = Empty()
            elif isinstance(complainer.capture, str):
                complainer.capture = Regex(
                    complainer.capture, flags=complainer.regex_options
                )

            # Map the capture to all complainers
            self.capture_to_complainer[complainer.capture].append(complainer)

            # Get all the files to analyze
            all_files: Set[Path] = set()
            for g in complainer.glob:
                if not g:
                    raise ValueError(
                        f"Empty glob value inside {complainer} ({complainer.glob}): {g}"
                    )
                all_files |= set(ANALYZE_DIR.rglob(g))

            if complainer.exclude_glob:
                for g in complainer.exclude_glob:
                    if not g:
                        raise ValueError(
                            f"Empty exclude glob value inside {complainer} ({complainer.exclude_glob}): {g}"
                        )
                    all_files -= set(ANALYZE_DIR.rglob(g))

            # Add all files and captures to the dicts
            for file1 in all_files:
                self.file_to_complainers[file1].add(complainer)
                self.complainer_to_files[complainer].add(file1)


def parse_files(staged_only: bool, include_untracked: bool, gitidx: GitIndex, cidx: ComplainerIndex) -> Iterable[Complaint]:
    """
    Parses the files using the complainers capture field.
    Yields the complaints.
    """
    # Iterate over all captures and globs
    # N_WARNINGS, N_CRITICAL = 0, 0
    for file2, complainers in cidx.file_to_complainers.items():
        # Check if file is staged for git commit if args.git is true
        if staged_only and file2 not in gitidx.staged_files:
            continue

        # Check if file is untracked if we are in a git repo
        if (not include_untracked) and (file2.absolute() in gitidx.untracked_files):
            continue

        # Open the file
        logger.debug(f"Reading file: {file2}")
        with file2.open("r") as f2:
            try:
                txt: str = f2.read()
            except UnicodeDecodeError:
                continue

        # Get the or of all captures
        # Then Iterate over all captures
        for complainer in complainers:
            capture = complainer.capture

            # Then Get all matches in the file
            logger.debug(f"Parsing file {file2} with complainer {type(complainer)}")
            for match, start, stop in capture.scanString(txt):

                # Then iterate over all complainers
                for complainer in cidx.capture_to_complainer[capture]:

                    # Skip if this file is not specifically globbed by this complainer
                    if file2 not in cidx.complainer_to_files[complainer]:
                        continue

                    yield from complainer.check(
                        txt=txt,
                        capture_span=(start, stop),
                        path=file2,
                        capture_data=match,
                    )

    # In the end, we try to call .finalize() on each complainer. Its purpose is
    # to allow for complainers to have methods that will be called once, in the end.
    for complainer in cidx.all_complainers:
        if not hasattr(complainer, "finalize"):
            continue

        yield from complainer.finalize()


if __name__ == "__main__":
    main()
