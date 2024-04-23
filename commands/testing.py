from invoke.tasks import task
from invoke import Collection


@task(help={
    "test_file": "A path to a file containing a subset of tests to run",
    "test_method": "An expression of which test methods to run",
    "warnings": "Whether to print warnings in the test report",
    "fail_fast": "Fails at first failing test when enabled",
})
def run(ctx, test_file=None, test_method=None, warnings=False, fail_fast=False):
    """
    Runs the tests for the harvester
    """
    # Specify some flags we'll be passing on to pytest based on command line arguments
    test_file = test_file if test_file else ""
    test_method_flag = f"-x -k {test_method}" if test_method else ""
    warnings_flag = "--disable-warnings" if not warnings else ""
    fail_fast_flag = "" if not fail_fast else "-x"

    # Assert that inputs make sense
    assert not test_method or test_file, "Can't specify a test method without specifying the test file"

    # Run pytest command
    with ctx.cd("tests"):
        ctx.run(
            f"pytest {test_file} {test_method_flag} {warnings_flag} {fail_fast_flag}",
            echo=True, pty=True
        )


test_collection = Collection("test", run)
