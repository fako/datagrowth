from invoke.tasks import task
from invoke import Collection


@task(help={
    "test_file": "A path to a file containing a subset of tests to run",
    "test_method": "An expression of which test methods to run",
    "warnings": "Whether to print warnings in the test report",
    "fast": "Whether to exclude tests marked as slow",
    "parallel": "Whether to run the tests in parallel on multiple cpus",
    "fail_fast": "Fails at first failing test when enabled",
})
def run(ctx, test_file=None, test_method=None, warnings=False, fast=False, parallel=False, fail_fast=False):
    """
    Runs the tests for the harvester
    """
    # Specify some flags we'll be passing on to pytest based on command line arguments
    test_file = test_file if test_file else ""
    test_method_flag = f"-x -k {test_method}" if test_method else ""
    warnings_flag = "--disable-warnings" if not warnings else ""
    fail_fast_flag = "" if not fail_fast else "-x"

    # Assert that inputs make sense
    assert not test_file or not parallel, "You shouldn't run tests from a single file in parallel"
    assert not fast or not parallel, \
        "Running --fast with --parallel is slower than just --fast due to multiprocessing overhead"
    assert not test_method or test_file, "Can't specify a test method without specifying the test file"

    # Determine value of marks flag which filters flags
    if test_file:
        # Selecting happening through specifying the tests file.
        # Ignoring other mark filtering
        marks_flag = ""
    else:
        marks_operators = []
        if fast:
            marks_operators.append("not slow")
        if parallel:
            # Excluding search for parallel, because manipulating indices in parallel will not be atomic
            marks_operators.append("not search")
        marks_flag = f'-m "{" and ".join(marks_operators)}"' if marks_operators else ""

    # Run pytest command
    with ctx.cd("tests"):
        if not parallel:
            ctx.run(
                f"pytest {test_file} {test_method_flag} {warnings_flag} {marks_flag} {fail_fast_flag}",
                echo=True, pty=True
            )
        else:
            # Running all tests in parallel except for search, because manipulating indices is not atomic
            ctx.run(
                f"pytest {warnings_flag} {marks_flag} {fail_fast_flag} -n auto --create-db",
                echo=True, pty=True
            )
            ctx.run(f"pytest {warnings_flag} {fail_fast_flag} -m search --reuse-db", echo=True, pty=True)


test_collection = Collection("test", run)
