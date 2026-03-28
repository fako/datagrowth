from unittest.mock import patch
import requests

from django.test import TestCase

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http.tasks import send, get_resource_link, load_session

from resources.mocks.requests import MockRequestsWithAgent
from resources.models import HttpResourceMock
from resources.tests.http import task_base


class TestSendMassTaskGet(task_base.TestSendMassTaskBase):
    method = "get"


class TestSendMassTaskPost(task_base.TestSendMassTaskBase):
    method = "post"


class TestSendTaskGet(task_base.TestHTTPTasksBase):

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

    def test_send_injected_session(self):
        scc, err = send("test", method=self.method, config=self.config, session=MockRequestsWithAgent)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        link = HttpResourceMock.objects.get(id=scc[0])
        self.assertIn("user-agent", link.head)

    @patch("datagrowth.resources.http.iterators.get_resource_link")
    def test_send_injected_session_provider(self, get_resource_link_mock):
        send("test", method=self.method, config=self.config, session="ProcessorMock")
        args, kwargs = get_resource_link_mock.call_args
        config, session = args
        self.assertTrue(session.from_provider)


class TestSendTaskPost(task_base.TestHTTPTasksBase):

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

    def test_send_injected_session(self):
        scc, err = send(query="test", method=self.method, config=self.config, session=MockRequestsWithAgent)
        self.check_results(scc, 1)
        self.check_results(err, 0)
        link = HttpResourceMock.objects.get(id=scc[0])
        self.assertIn("user-agent", link.head)

    @patch("datagrowth.resources.http.iterators.get_resource_link")
    def test_send_injected_session_provider(self, get_resource_link_mock):
        send("test", method=self.method, config=self.config, session="ProcessorMock")
        args, kwargs = get_resource_link_mock.call_args
        config, session = args
        self.assertTrue(session.from_provider)


class TestGetResourceLink(task_base.TestHTTPTasksBase):

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
