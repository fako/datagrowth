from datetime import datetime

from unittest.mock import patch, call
import requests

from django.test import TestCase

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http.tasks import send, send_mass, get_resource_link, load_session

from resources.mocks.requests import MockRequestsWithAgent, MockRequests
from resources.models import HttpResourceMock


class TestHTTPTasksBase(TestCase):

    fixtures = ["test-http-resource-mock"]
    method = ""

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(
            namespace="http_resource",
            private=["_resource", "_continuation_limit"],
        )
        self.config.update({
            "resource": "resources.HttpResourceMock",
        })
        self.session = MockRequests

    def get_args_list(self, queries):
        if self.method == "get":
            return [[query] for query in queries]
        elif self.method == "post":
            return [[] for query in queries]
        else:
            raise Exception("{} does not have a valid method specified.".format(self.__class__.__name__))

    def get_kwargs_list(self, queries):
        if self.method == "get":
            return [{} for query in queries]
        elif self.method == "post":
            return [{"query": query} for query in queries]
        else:
            raise Exception("{} does not have a valid method specified.".format(self.__class__.__name__))

    def check_results(self, results, expected_length):
        self.assertEqual(len(results), expected_length)
        for pk in results:
            self.assertIsInstance(pk, int)
            self.assertGreater(pk, 0)


class TestSendMassTaskBase(TestHTTPTasksBase):
    """
    This test case also covers send_serie as that is the main implementation of send_mass
    """

    def test_send_mass(self):
        args_list = self.get_args_list(["test", "test2", "404"])
        kwargs_list = self.get_kwargs_list(["test", "test2", "404"])
        start = datetime.now()
        scc, err = send_mass(args_list, kwargs_list, method=self.method, config=self.config, session=MockRequests)
        end = datetime.now()
        duration = (end - start).total_seconds()
        self.assertLess(duration, 0.1)
        self.check_results(scc, 2)
        self.check_results(err, 1)

    @patch("datagrowth.resources.http.generic.sleep")
    def test_send_mass_intervals(self, sleep_mock):
        # First with an interval
        self.config.interval_duration = 250  # 0.25 secs
        args_list = self.get_args_list(["test", "test2"])
        kwargs_list = self.get_kwargs_list(["test", "test2"])
        scc, err = send_mass(args_list, kwargs_list, method=self.method, config=self.config, session=MockRequests)
        self.assertEqual(sleep_mock.call_args_list, [call(0.25), call(0.25)])
        self.check_results(scc, 2)
        self.check_results(err, 0)
        # Now without an interval
        sleep_mock.reset_mock()
        self.config.interval_duration = 0
        args_list = self.get_args_list(["test", "test2"])
        kwargs_list = self.get_kwargs_list(["test", "test2"])
        scc, err = send_mass(args_list, kwargs_list, method=self.method, config=self.config, session=MockRequests)
        self.assertFalse(sleep_mock.called)
        self.check_results(scc, 2)
        self.check_results(err, 0)

    def test_send_mass_continuation_prohibited(self):
        args_list = self.get_args_list(["test", "next", "404"])
        kwargs_list = self.get_kwargs_list(["test", "next", "404"])
        scc, err = send_mass(args_list, kwargs_list, method=self.method, config=self.config, session=MockRequests)
        self.check_results(scc, 2)
        self.check_results(err, 1)

    def test_send_mass_continuation(self):
        self.config.continuation_limit = 10
        args_list = self.get_args_list(["test", "next", "404"])
        kwargs_list = self.get_kwargs_list(["test", "next", "404"])
        scc, err = send_mass(
            args_list,
            kwargs_list,
            method=self.method,
            config=self.config,
            session=MockRequests
        )
        self.check_results(scc, 3)
        self.check_results(err, 1)

    @patch("datagrowth.resources.http.tasks.send_serie", return_value=([], [],))
    def test_send_mass_concat_arguments(self, send_serie):
        self.config.concat_args_size = 3
        self.config.concat_args_symbol = "|"
        send_mass(
            [[1], [2], [3], [4], [5, 5], [6], [7]],
            [{}, {}, {}, {}, {}, {}, {}],
            method=self.method,
            config=self.config,
            session=MockRequests
        )
        send_serie.assert_called_with(
            [["1|2|3"], ["4|5|5|6"], ["7"]], [{}, {}, {}],
            method=self.method,
            config=self.config,
            session=MockRequests
        )

    @patch("datagrowth.resources.http.tasks.send_serie", return_value=([], [],))
    def test_send_inserted_session_provider(self, send_serie):
        send_mass([1], [{}], method=self.method, config=self.config, session="ProcessorMock")
        args, kwargs = send_serie.call_args
        self.assertEqual(args, ([1], [{}],))
        self.assertEqual(kwargs["method"], self.method)
        self.assertEqual(kwargs["config"], self.config)
        self.assertTrue(kwargs["session"].from_provider)


class TestSendMassTaskGet(TestSendMassTaskBase):
    method = "get"


class TestSendMassTaskPost(TestSendMassTaskBase):
    method = "post"


class TestSendTaskGet(TestHTTPTasksBase):

    method = "get"

    def test_send(self):
        # Test makes equivalent call of HttpResourceProcessor.fetch.delay("test")
        scc, err = send("test", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # Similar but with a cached result
        scc, err = send("success", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # And with an error response
        scc, err = send("404", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 0)
        self.check_results(err, 1)
        scc, err = send("500", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 0)
        self.check_results(err, 1)

    def test_send_continuation_prohibited(self):
        scc, err = send("next", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)

    def test_send_continuation(self):
        self.config.continuation_limit = 10
        scc, err = send("next", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 2)
        self.check_results(err, 0)

    def test_send_inserted_session(self):
        scc, err = send("test", method=self.method, config=self.config, session=MockRequestsWithAgent)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        link = HttpResourceMock.objects.get(id=scc[0])
        self.assertIn("user-agent", link.head)

    @patch("datagrowth.resources.http.tasks.get_resource_link")
    def test_send_inserted_session_provider(self, get_resource_link_mock):
        send("test", method=self.method, config=self.config, session="ProcessorMock")
        args, kwargs = get_resource_link_mock.call_args
        config, session = args
        self.assertTrue(session.from_provider)


class TestSendTaskPost(TestHTTPTasksBase):

    method = "post"

    def test_send(self):
        # Test makes equivalent call of HttpResourceProcessor.fetch.delay("test")
        scc, err = send(query="test", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # Similar but with a cached result
        scc, err = send(query="success", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        # And with an error response
        scc, err = send(query="404", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 0)
        self.check_results(err, 1)
        scc, err = send(query="500", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 0)
        self.check_results(err, 1)

    def test_send_continuation_prohibited(self):
        scc, err = send(query="next", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 1)
        self.check_results(err, 0)

    def test_send_continuation(self):
        self.config.continuation_limit = 10
        scc, err = send(query="next", method=self.method, config=self.config, session=self.session)
        self.check_results(scc, 2)
        self.check_results(err, 0)

    def test_send_inserted_session(self):
        scc, err = send(query="test", method=self.method, config=self.config, session=MockRequestsWithAgent)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        link = HttpResourceMock.objects.get(id=scc[0])
        self.assertIn("user-agent", link.head)

    @patch("datagrowth.resources.http.tasks.get_resource_link")
    def test_send_inserted_session_provider(self, get_resource_link_mock):
        send("test", method=self.method, config=self.config, session="ProcessorMock")
        args, kwargs = get_resource_link_mock.call_args
        config, session = args
        self.assertTrue(session.from_provider)


class TestGetResourceLink(TestHTTPTasksBase):

    def test_get_link(self):
        self.config.update({"test": "test"})
        session = requests.Session()
        session.cookies = {"test": "test"}
        link = get_resource_link(config=self.config, session=session)
        self.assertIsInstance(link, HttpResourceMock)
        self.assertIsNone(link.id)
        self.assertIsNone(link.request)
        self.assertFalse(hasattr(link.config, 'resource'))
        self.assertEqual(link.config.test, 'test')
        self.assertEqual(link.session.cookies, {"test": "test"})


@load_session()
def load_session_function(config, session):
    return config, session


class TestLoadSession(TestCase):

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(namespace="test",)

    def test_load_session(self):
        config, session = load_session_function(self.config)
        self.assertIsInstance(session, requests.Session)
        preload_session = requests.Session()
        preload_session.preload = True
        config, session = load_session_function(self.config, session=preload_session)
        self.assertIsInstance(session, requests.Session)
        self.assertTrue(session.preload)
        config, session = load_session_function(self.config, session="ProcessorMock")
        self.assertTrue(session.from_provider)
