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
    "django": "Whether to run Django tests",
    "generic": "Whether to run generic tests",
    "snapshots": "Whether to store Resource snapshots instead of testing (generic only)",
})
def run(ctx, test_file=None, test_method=None, warnings=False, fail_fast=False, debug: bool = False,
        django: bool = True, generic: bool = True, snapshots: bool = False) -> None:
    """
    Runs the tests for the harvester
    """
    # Specify some flags we'll be passing on to pytest based on command line arguments
    test_file = test_file if test_file else ""
    test_method_flag = f"-x -k {test_method}" if test_method else ""
    warnings_flag = "--disable-warnings" if not warnings else ""
    fail_fast_flag = "" if not fail_fast else "-x"
    debug_flag = "" if not debug else "-s"

    # Assert that inputs make sense
    assert not test_method or test_file, "Can't specify a test method without specifying the test file"

    # Run pytest command for generic functionality
    if generic:
        with ctx.cd(Path("tests")):
            test_env = dict(os.environ)
            if snapshots:
                test_env["DATAGROWTH_STORAGE_SNAPSHOTS"] = "1"
                test_env["DATAGROWTH_STORAGE_ALLOW_LOAD"] = "0"
                test_env["DATAGROWTH_STORAGE_ALLOW_SAVE"] = "1"
            disable_django = "--ignore=django_project -p no:django"
            ctx.run(
                f"pytest {test_file} {test_method_flag} {warnings_flag} {fail_fast_flag} {debug_flag} {disable_django}",
                env=test_env, echo=True, pty=True
            )

    # Run pytest command for Django functionality
    if django:
        with ctx.cd(Path("tests", "django_project")):
            ctx.run(
                f"pytest {test_file} {test_method_flag} {warnings_flag} {fail_fast_flag} {debug_flag}",
                echo=True, pty=True
            )


test_collection = Collection("test", run)
