import os
from invoke import Exit


def assert_repo_root_directory():
    root_directory = os.getcwd()
    project_file = os.path.join(root_directory, "pyproject.toml")
    if not os.path.exists(project_file):  # apparently we're not executing from root directory
        raise Exit("Command should be run from repository root")
