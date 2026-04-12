from invoke.collection import Collection

from commands.utils import assert_repo_root_directory
from commands.testing import test_collection
from commands.documentation import docs_collection


assert_repo_root_directory()


namespace = Collection(
    test_collection,
    docs_collection,
)
