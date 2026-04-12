import os
from pathlib import Path
from invoke.tasks import task
from invoke.collection import Collection


@task(help={
    "test_file": "A path to a file containing a subset of tests to run",
    "test_method": "An expression of which test methods to run",
    "warnings": "Whether to print warnings in the test report",
    "fail_fast": "Fails at first failing test when enabled",
    "debug": "Whether to output stdout regardless of test outcomes",
})
def library(ctx, test_file=None, test_method=None, warnings=False, fail_fast=False, debug: bool = False,
            snapshots: bool = False) -> None:
    """
    Runs the tests for the library
    """
    # Specify some flags we'll be passing on to pytest based on command line arguments.
    # These are common flags that we want a shorthand for.
    test_file = test_file if test_file else ""
    test_method_flag = f"-x -k {test_method}" if test_method else ""
    warnings_flag = "--disable-warnings" if not warnings else ""
    fail_fast_flag = "" if not fail_fast else "-x"
    debug_flag = "" if not debug else "-s"

    # Assert that inputs make sense
    assert not test_method or test_file, "Can't specify a test method without specifying the test file"

    # Some special flags and setup to use when only testing the library
    test_env = dict(os.environ)
    if snapshots:
        test_env["DATAGROWTH_STORAGE_SNAPSHOTS"] = "1"
        test_env["DATAGROWTH_STORAGE_ALLOW_LOAD"] = "0"
        test_env["DATAGROWTH_STORAGE_ALLOW_SAVE"] = "1"
    disable_django = "--ignore=django_project -p no:django"

    # Run pytest command for generic library functionality
    with ctx.cd(Path("tests")):
        ctx.run(
            f"pytest {test_file} {test_method_flag} {warnings_flag} {fail_fast_flag} {debug_flag} {disable_django}",
            env=test_env, echo=True, pty=True
        )


@task(help={
    "test_file": "A path to a file containing a subset of tests to run",
    "test_method": "An expression of which test methods to run",
    "warnings": "Whether to print warnings in the test report",
    "fail_fast": "Fails at first failing test when enabled",
    "debug": "Whether to output stdout regardless of test outcomes",
})
def django(ctx, test_file=None, test_method=None, warnings=False, fail_fast=False, debug: bool = False) -> None:
    """
    Runs the tests for Django integration
    """
    # Specify some flags we'll be passing on to pytest based on command line arguments.
    # These are common flags that we want a shorthand for.
    test_file = test_file if test_file else ""
    test_method_flag = f"-x -k {test_method}" if test_method else ""
    warnings_flag = "--disable-warnings" if not warnings else ""
    fail_fast_flag = "" if not fail_fast else "-x"
    debug_flag = "" if not debug else "-s"

    # Assert that inputs make sense
    assert not test_method or test_file, "Can't specify a test method without specifying the test file"

    # Run pytest command for Django functionality
    with ctx.cd(Path("tests", "django_project")):
        ctx.run(
            f"pytest {test_file} {test_method_flag} {warnings_flag} {fail_fast_flag} {debug_flag}",
            echo=True, pty=True
        )


@task
def syntax(ctx) -> None:
    """
    Run syntax as well as type-checkers to assure code quality
    """
    ctx.run("flake8 .", echo=True, pty=True)
    # For now runs BasedPyright only in fixed directories to prevent regressions,
    # but allows non-runtime problems in non-fixed directories.
    ctx.run("basedpyright --project pyrightconfig.fixed.json", echo=True, pty=True)


@task
def run(ctx) -> None:
    """
    Runs all code quality and test commands: syntax, library tests and Django tests
    """
    syntax(ctx)
    library(ctx)
    django(ctx)


test_collection = Collection(
    "test",
    library,
    django,
    syntax,
    run,
)
