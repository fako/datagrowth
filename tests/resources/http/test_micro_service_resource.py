from __future__ import annotations

from typing import ClassVar
from unittest.mock import Mock

import pytest
import requests

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.pydantic import MicroServiceResource
from datagrowth.resources.http.signature import HttpMode, HttpSignature


class MockMicroTikaResource(MicroServiceResource):

    MICRO_SERVICE: ClassVar[str | None] = "tika"
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json",
    }
    MODE: ClassVar[HttpMode] = HttpMode.JSON


class MicroServiceUnknownName(MicroServiceResource):
    """Subclass that inherits MICRO_SERVICE = None from the base."""


class MockMicroDoesNotExistServiceResource(MicroServiceResource):
    MICRO_SERVICE: ClassVar[str | None] = "does_not_exist"


@pytest.fixture
def mocked_session() -> Mock:
    session = Mock(spec=requests.Session)
    real_session = requests.Session()
    session.prepare_request.side_effect = real_session.prepare_request
    return session


@pytest.fixture
def micro_service_config() -> ConfigurationType:
    config = ConfigurationType(namespace=["micro_service", "http_resource", "global"])
    config.update({
        "connections": {
            "tika": {
                "protocol": "http",
                "host": "localhost:9998",
                "path": "/rmeta/text",
            },
        },
    })
    return config


@pytest.fixture
def resource(mocked_session: Mock, micro_service_config: ConfigurationType) -> MockMicroTikaResource:
    resource = MockMicroTikaResource(config=micro_service_config)
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    resource.extractor.config.update({
        "backoff_delays": [],
        "requests_proxies": None,
        "requests_verify": True,
        "allow_redirects": True,
        "timeout": 30,
        "user_agent": "DataGrowth (test)",
    })
    return resource


# ==============================
# prepare_inputs
# ==============================


def test_prepare_inputs_creates_http_signature_with_connection_template_data(resource: MockMicroTikaResource) -> None:
    signature = resource.prepare_inputs("get")

    assert isinstance(signature, HttpSignature)
    assert signature.url == "http://localhost:9998/rmeta/text"
    assert signature.uri == "localhost:9998/rmeta/text"
    assert signature.mode == HttpMode.JSON
    assert signature.data == {}
    assert signature.headers == {"Accept": "application/json"}


def test_prepare_inputs_rejects_extra_positional_url_arguments(resource: MockMicroTikaResource) -> None:
    with pytest.raises(ValueError, match="expects no positional args"):
        resource.prepare_inputs("get", "unexpected-path-segment")


def test_prepare_inputs_raises_when_micro_service_name_not_set(micro_service_config: ConfigurationType) -> None:
    resource = MicroServiceUnknownName(config=micro_service_config)
    with pytest.raises(AssertionError, match="You should specify a micro service name"):
        resource.prepare_inputs("get")


def test_prepare_inputs_raises_for_unknown_micro_service_connection(micro_service_config: ConfigurationType) -> None:
    resource = MockMicroDoesNotExistServiceResource(config=micro_service_config)
    with pytest.raises(AssertionError, match='"does_not_exist" is an unknown micro service'):
        resource.prepare_inputs("get")


def test_prepare_inputs_raises_when_connection_missing_protocol(micro_service_config: ConfigurationType) -> None:
    micro_service_config.update({
        "connections": {
            "tika": {
                "host": "localhost:9998",
                "path": "/rmeta/text",
            },
        },
    })
    resource = MockMicroTikaResource(config=micro_service_config)
    with pytest.raises(AssertionError, match="protocol should be specified"):
        resource.prepare_inputs("get")


def test_prepare_inputs_raises_when_connection_missing_host(micro_service_config: ConfigurationType) -> None:
    micro_service_config.update({
        "connections": {
            "tika": {
                "protocol": "http",
                "host": "",
                "path": "/rmeta/text",
            },
        },
    })
    resource = MockMicroTikaResource(config=micro_service_config)
    with pytest.raises(AssertionError, match="host should be specified"):
        resource.prepare_inputs("get")


def test_prepare_inputs_raises_when_connection_missing_path(micro_service_config: ConfigurationType) -> None:
    micro_service_config.update({
        "connections": {
            "tika": {
                "protocol": "http",
                "host": "localhost:9998",
                "path": None,
            },
        },
    })
    resource = MockMicroTikaResource(config=micro_service_config)
    with pytest.raises(AssertionError, match="path should be specified"):
        resource.prepare_inputs("get")


def test_prepare_inputs_kwarg_overrides_connection_fields(resource: MockMicroTikaResource) -> None:
    signature = resource.prepare_inputs("get", protocol="https", host="tika.example.com", path="/custom")

    assert signature.url == "https://tika.example.com/custom"
