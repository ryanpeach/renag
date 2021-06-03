import argparse
import importlib
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, List, Optional, Tuple, TypeVar, Dict, Set

from iregex import Regex

from renag.complainer import Complainer
from renag.types import (
    AnyRegex,
    Complaint,
    GlobStr,
    OriginalIdx,
    RegexStr,
    OriginalSlice,
    OriginalTxt,
    PartialIdx,
    PartialSlice,
    PartialTxt,
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


# ============== Converters / Complainers ==============

T = TypeVar("T", bound=HasContext)


def _get_all_contexts(all: List[T]) -> DefaultDict[Regex, List[T]]:
    """
    Gets all contexts from the list of HasContext objects, and returns a dictionary mapping between context and all
    objects using that context.
    """
    by_context: DefaultDict[Regex, List[T]] = defaultdict(list)
    for c in all:
        by_context[c.context].append(c)
    return by_context

def _handle_complaints(file_txt: OriginalTxt) -> List[Complaint]:
    """Handles all complainers and returns the complaints made by those complainers."""
    # First we will get all contexts of all the converters
    complainers_by_context = _get_all_contexts(ALL_COMPLAINERS)

    # This will get all replacements via the converters
    complaints: List[Complaint] = []
    for context, complainers in complainers_by_context.items():
        if context is None:
            context = Regex().anything()
        for match in context.compile().finditer(file_txt):
            for complainer in complainers:
                complaints += complainer.check_rcpp(
                    original_txt=file_txt, context_range=(match.start(), match.end())
                )

    return complaints

def _to_cpp(file: Path) -> None:
    """to_cpp but for one file at a time."""
    # Some impossible assertions
    assert file.is_file(), f"{str(file)} does not exist."

    # Create the replacement file name
    if file.suffix == ".rcpp":
        renamed: Path = file.with_suffix(".cpp")
    elif file.suffix == ".rhpp":
        renamed = file.with_suffix(".hpp")
    else:
        raise TypeError(f"Extension not in (.rcpp, .rhpp), found {file.suffix}")

    # Read the file
    with file.open("r") as f:
        file_txt: OriginalTxt = OriginalTxt(f.read())

    # ====== Run all Complainers ======
    complaints = _handle_complaints(file_txt)

    if complaints:
        print("Complaints Found:")
        print()
        for c in complaints:
            print(str(c))
            print()
        exit(1)

def main(
    load_module: str,
    analyze_dir: Path
) -> None:
    """Runs all Complainers found in `load_dir` on all files found in `analyze_dir` recursive."""
    mod = importlib.import_module(load_module)
    all = getattr(mod, "__all__")
    all_complainers: List[Complainer] = []
    for item_name in all:
        assert isinstance(item_name, str)
        item = getattr(mod, item_name)
        if isinstance(item, type):
            # Initialize the item
            try:
                item_init = item()
            except:
                continue

            # Check if its a Complainer
            # If it is add it to the list.
            if isinstance(item_init, Complainer):
                all_complainers.append(item_init)

    if not all_complainers:
        raise ValueError(f"No Complainers found in module {load_module}.")
    
    # Get all the contexts and globs of all complainers
    all_contexts_globs: Dict[GlobStr, Set[RegexStr]] = defaultdict(set)
    context_to_complainer: Dict[RegexStr, List[Complainer]] = defaultdict(list)
    for complainer in all_complainers:
        # Set default values for glob and context
        if not complainer.glob:
            complainer.glob = ["*"]
        if not complainer.context:
            complainer.context = "*"

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
            with file.open('r') as f:
                txt = OriginalTxt(f.read())

            # Then Iterate over all contexts
            for context in contexts:

                # Then Get all matches in the file
                for match in Regex(context).compile().finditer(txt):
                    original_slice: OriginalSlice = (match.start(), match.end())

                    # Then iterate over all complainers
                    for complainer in context_to_complainer[str(context)]:

                        complaints = complainer.check(
                            context_txt=match.txt,
                            original_slice=original_slice,
                            file_path=file
                        )

                        for complaint in complaints:
                            N += 1
                            if complaint.level is Severity.CRITICAL:
                                N_CRITICAL += 1
                                exitcode = 1
                            else:
                                N_WARNINGS += 1
                                exitcode = max(exitcode, 0)
                            print(complaint.pformat())

    # End by exiting the program
    if N == 0:
        print("No complaints. Enjoy the rest of your day!")
    else:
        print(f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.")
    exit(exitcode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--load_module", type=str, default='.complainers',
        help="A local python module (folder) containing all complainers. "
             "In order to import a locally defined module, use relative import notation: "
             "For example, if the directory you are running this cli from contains a "
             "directory with an __init__.py inside it called `complainers` which is the default name "
             "suggested by this package, the value of this argument should be `.complainers`. "
             "The module needs to supply all complainers via `from $load_module import *`."
    )
    parser.add_argument(
        "--analyze_dir", type=str, default=".",
        help="The directory to run all globs and issue complaints about."
    )
    args = parser.parse_args()
    args.analyze_dir = Path(args.analyze_dir).absolute()
    if not args.analyze_dir.is_dir():
        raise ValueError(f"{args.analyze_dir} is not a directory.")

    main(
        load_module=args.load_module,
        analyze_dir=args.analyze_dir
    )