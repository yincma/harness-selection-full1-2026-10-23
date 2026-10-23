Resolve the following issue, reported on GitHub for the pytest repository (pytest-dev/pytest). The repository is in `repo/`, at the commit the issue was reported against.

<issue>
caplog fixture doesn't restore log level after test
From the documentation at https://docs.pytest.org/en/6.0.0/logging.html#caplog-fixture, "The log levels set are restored automatically at the end of the test".
It used to work, but looks broken in new 6.0 release. Minimal example to reproduce:

```
def test_foo(caplog):
    caplog.set_level(42)

def test_bar(caplog):
    print(caplog.handler.level)
```

It prints "0" for pytest<6, "42" after.
</issue>

Goal: change the code in `repo/` so that the issue is resolved. Afterwards, hidden tests written for this issue are run (they are not in the workspace; they replace any test file they touch), and the repository's existing tests must keep passing. Fix the library code; adding tests under `repo/testing/` is optional.

Environment: a Python 3.9 virtualenv in which `repo/` is installed in editable mode, so your edits take effect at once. Only the packages pytest itself needs are installed; there is no network access and nothing else can be installed.

Commands (run them from the workspace root; any other command is rejected):
- `./run_tests.sh <pytest arguments>` runs pytest inside `repo/` with the task's Python, for example `./run_tests.sh testing/test_foo.py -q -x`, `./run_tests.sh testing/test_foo.py::TestBar::test_baz --tb=short` or `./run_tests.sh testing/test_foo.py -k word` (test_foo, TestBar and test_baz stand for real names). A test file you wrote under `scratch/` runs with `./run_tests.sh scratch/test_example.py` (pytest then runs from the workspace root; do not mix it with `repo/` test paths). One call stops after 300 s, so run single files or single tests, not the whole test suite.
- `./run_py.sh scratch/<file>.py` runs a Python script you wrote under `scratch/` with the same Python, with the repository importable (working directory: the workspace root; stopped after 60 s).
- `./search.sh <text> [<dir>]` prints the lines containing <text> (fixed string, case-sensitive) under <dir> (default `repo`), e.g. `./search.sh def_main repo/src`.
- `ls [-options] [<dir>]`.
Arguments must be plain words: quotes, brackets, `*`, `?`, `..`, `$`, `|`, `;`, `&`, `<`, `>`, `~`, `!`, `#` and other shell operators are rejected, so a parametrized test id such as `test_x[1]` cannot be given (select it with `-k` instead), and a `-k` expression can only be a single word. Absolute paths, `--basetemp` and `--rootdir` are refused.

Files: you can read anything inside the workspace. You can write only under `repo/` and `scratch/`, and the file `NOTES.md`.
