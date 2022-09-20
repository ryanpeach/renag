from dataclasses import dataclass
from typing import Set
from pathlib import Path
from renag.types.custom_types import Severity, BColors
from renag.types.complaint import Complaint
from renag.types.complainer import Complainer
from renag.utils import color_txt
import importlib
import inspect
from typing import List, Dict, Iterable, Set
from pyparsing import Regex, Empty, ParserElement
from collections import defaultdict
import logging

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

logger = logging.getLogger(__name__)

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

