from invoke import Collection

from commands.utils import assert_repo_root_directory
from commands.testing import test_collection


assert_repo_root_directory()


namespace = Collection(
    test_collection,
)
