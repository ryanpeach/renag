The reason I am archiving this library is because the approach I used is way too slow when scanning big repos.

Also I have seen this tool https://github.com/semgrep/ which you may want to check out.

Another thing you can do is just use `pytest`, or any languages testing framework, and put it in a subfolder of your code. Write a fixture to get file contents over an iterator. It's much simpler. The power of testing frameworks beyond their standard use is eye opening to me. A lot of these frameworks also provide parallelism out of the box.

However, if I was doing this over, I would do it in rust and implement some kind of YAML config most likely. This was a little more flexible than that, but again it was slow.

# renag

![TravisCI Build Status](https://travis-ci.com/ryanpeach/renag.svg?branch=master)
[![codecov](https://codecov.io/gh/ryanpeach/py_idiomatic_regex/branch/master/graph/badge.svg)](https://codecov.io/gh/ryanpeach/renag)

[Documentation Available Here](https://ryanpeach.github.io/renag)

Short for **Regex** (re) **Nag** (like "one who complains").

Now also [PEGs (Parsing Expression Grammars)](https://en.wikipedia.org/wiki/Parsing_expression_grammar) compatible with [pyparsing](https://pypi.org/project/pyparsing/)!

A Regex based linter tool that works for any language and works exclusively with custom linting rules.

# Complainers

`renag` is based on the concept of `Complainer`s. See `renag/complainer.py` for the interface to create your own `Complainer` and `examples` for some prebuilt examples.

Complainers can be as simple as the following:

```python
class PrintComplainer(Complainer):
    """Print statements can slow down code."""

    capture = r"print\(.*\)"
    severity = Severity.WARNING
    glob = ["*.py"]
```

This has 4 fundamental parts:

* `docstring` - The docstring of the class automatically becomes the description of the error.
* `capture` - A regex statement that, if matched, will raise the complaint.
* `severity` - Either `WARNING` which will return exit code 0, or `CRITICAL` which will return exit code 1.
* `glob` - A list of glob wildcards that define what files to run the `Complainer` on.

Next you can add a `check` method to your `Complainer` if you would like something more complicated than simple regex.

```python
class PrintComplainer(Complainer):
    """Print statements can slow down code."""
    ...

    def check(self, txt: str, path: Path, capture_span: Span) -> List[Complaint]:
          """Check that the print statement is not commented out before complaining."""
          # Get the line number
          lines, line_numbers = get_lines_and_numbers(txt, capture_span)

          # Check on the first line of the capture_span that the capture is not preceded by a '#'
          # In such a case, the print has been commented out
          if lines[0].count("#") > 0 and lines[0].index("#") < capture_span[0]:

              # If it is the case that the print was commented out, we do not need to complain
              # So we will return an empty list of complaints
              return []

          # Otherwise we will do as normal
          return super().check(txt=txt, path=path, capture_span=capture_span)
```

## Adding to your project

Simply put this complainer in a python module in your project like so:

```
root/
  complainers_dir_name/  # Default is "complainers"
    __init__.py
    custom_complainer1.py
    custom_complainer2.py
    ...
  the-rest-of-your-project
  ...
```

Optionally, you can just put them inside a folder without `__init__.py` and they will be imported individually (but not within subfolders). Do this for most simple projects.

If you choose to use the module method, import each complainer inside `__init__.py` so it can be imported via `from .{complainers_dir_name} import *`.

Regardless of which method you chose, next you need to add the following to your `.pre-commit-hooks.yaml` file:

```yaml
- repo: https://github.com/ryanpeach/renag
  rev: "0.4.4"
  hooks:
    - id: renag
      args:
        - "--load_module"
        - "{complainers_dir_name}"
        - "--staged"
```

Run `renag --help` to see a list of command line arguments you can add to the hook.

## Output

Complaint printout modeled after `rust` error reporting. Example of a Complaint:

```
Severity.WARNING - EasyPrintComplainer: Print statements can slow down code.
  --> renag/__main__.py
   147|                                 )
   148|                                 print()
   149|
   150|     # End by exiting the program
   151|     if N == 0:
   152|         print(color_txt("No complaints. Enjoy the rest of your day!", BColors.OKGREEN))
   152|         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   153|         exit(0)
   154|     if N_WARNINGS > 0 and N_CRITICAL == 0:
   155|         print(
   156|             color_txt(
   157|                 f"{N} Complaints found: {N_WARNINGS} Warnings, {N_CRITICAL} Critical.",
```

# [iregex](https://github.com/ryanpeach/iregex)

All regex captures in this module default to using `iregex`.
`iregex` can help make your regex more understandable to readers, and allow you to compose large regex statements (see `examples/regex.py` for examples).

# Contribution

Feel free to make a contribution! Here are some instructions for getting setup.

## Virtual Environment

This project uses [Poetry](https://python-poetry.org/). So you pretty much just use `poetry run ${YOUR_COMMAND_HERE}` from the project root directory to run stuff.

## CICD

This project uses [TravisCI](https://www.travis-ci.com/). The steps are explained in `.travis.yaml`. Basically automatically runs `poetry publish`

## Documentation

Documentation is provided via Sphinx and [autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html). Meaning properly formatted docstrings become documentation. However, if you create a new file in `renag` you need to create a new file in `docsrc/renag` of the same name following the formatting of the other `.rst` files.

## Testing

We use `pytest`, `mypy`, and `flake8`, running `renag` itself on the `complaints` directory, and then I have strategically set up a few runtime warnings in the code to pick out based on the examples inside `examples`.

`mypy` and `flake8` are part of the pre-commit hooks.

So a full test involves running:

```bash
poetry run pytest
poetry run renag
poetry run renag --load_module examples
```

## Making a new release

This project uses [Bumpversion](https://github.com/peritus/bumpversion).

To make a patch release (for example) run:

```bash
poetry run bumpversion patch
git push && git push --tags
```

Then push it (with tags)! Travis will take care of the rest.

When it's all done I like to author a "[Release](https://github.com/ryanpeach/renag/releases)" on GitHub manually.
