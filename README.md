# renag

A Regex based linter tool that works for any language and works exclusively with custom linting rules.

![TravisCI Build Status](https://travis-ci.com/ryanpeach/renag.svg?branch=master)
[![codecov](https://codecov.io/gh/ryanpeach/py_idiomatic_regex/branch/master/graph/badge.svg)](https://codecov.io/gh/ryanpeach/renag)

[Documentation Available Here](https://ryanpeach.github.io/renag)

Complaint printout modeled after `rust` error reporting. Example of a Complaint:

```
Severity.WARNING - ComplexPrintComplainer: Print statements can slow down code.
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

All regex captures in this module default to using [`iregex`](https://github.com/ryanpeach/iregex).
[`iregex`](https://github.com/ryanpeach/iregex) can help make your regex more understandable to readers, and allow you to compose large regex statements (see `examples/regex.py` for examples).
[`iregex`](https://github.com/ryanpeach/iregex) defaults to multiline regex using the `re` module.
