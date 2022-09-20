"""
This module runs the code from the commandline.
"""
import argparse
import importlib.util
import inspect
from logging import Logger
import os
from collections import defaultdict
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Set

from pyparsing import Empty, ParserElement, Regex

from renag.types.complainer import Complainer
from renag.types.complaint import Complaint
from renag.types.custom_types import BColors, Severity
from renag.utils import color_txt


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
