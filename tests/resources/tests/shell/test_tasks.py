from unittest.mock import patch, call

from django.test import TestCase

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.shell.tasks import run, run_serie

from resources.models import ShellResourceMock


class TestRunTask(TestCase):

    fixtures = ["test-shell-resource-mock"]

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(
            namespace="shell_resource",
            private=["_resource", "_continuation_limit"],
        )
        self.config.update({
            "resource": "resources.ShellResourceMock",
        })

    def check_results(self, results, expected_length):
        self.assertEqual(len(results), expected_length)
        for pk in results:
            self.assertIsInstance(pk, int)
            self.assertGreater(pk, 0)

    def test_run(self):
        scc, err = run("test", context=5, config=self.config)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # Similar but with a cached result
        scc, err = run("success", context=5, config=self.config)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # And with an error result
        scc, err = run("fail", context=5, config=self.config)
        self.check_results(scc, 0)
        self.check_results(err, 1)
        # In total there should be three Resources (two old, one new)
        self.assertEqual(
            ShellResourceMock.objects.count(), 3,
            "Expected three ShellResourceMock instances. Two from cache and one new"
        )


class TestRunSerieTask(TestCase):

    fixtures = ["test-shell-resource-mock"]

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(
            namespace="shell_resource",
            private=["_resource", "_continuation_limit"],
        )
        self.config.update({
            "resource": "resources.ShellResourceMock",
        })
        self.args_list = [["test"], ["success"], ["fail"]]
        self.kwargs_list = [
            {"context": 5}
            for _ in range(len(self.args_list))
        ]

    def check_results(self, results, expected_length):
        self.assertEqual(len(results), expected_length)
        for pk in results:
            self.assertIsInstance(pk, int)
            self.assertGreater(pk, 0)

    @patch("datagrowth.resources.shell.tasks.run", wraps=run)
    def test_run_serie(self, run_mock):
        scc, err = run_serie(self.args_list, self.kwargs_list, config=self.config)
        self.check_results(scc, 2)
        self.check_results(err, 1)
        run_mock.assert_has_calls([
            call("test", context=5, config=self.config),
            call("success", context=5, config=self.config),
            call("fail", context=5, config=self.config)
        ])
