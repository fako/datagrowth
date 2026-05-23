"""
Tests for the DjangoClientExtractor which uses Django's TestClient to extract data.
Mostly used to test composition Resources like SessionResource.
"""
from typing import ClassVar, Type
from unittest.mock import MagicMock

import pytest
from django.test import Client

from datagrowth.configuration import create_config
from datagrowth.registry import Tag
from datagrowth.signatures import InputsValidator, DataMode
from datagrowth.resources.pydantic import Resource
from datagrowth.resources.http.signature import HttpSignature, HttpMethod, HttpAuth
from datagrowth.resources.http.pydantic import HttpResource
from datagrowth.django.resources.extractors import DjangoClientExtractor


class AdminLoginInputsValidator(InputsValidator):
    username: str
    password: str


class AdminLoginResource(HttpResource):

    EXTRACTOR: ClassVar[Tag | None] = Tag(category="extractor", value="django_client")
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = AdminLoginInputsValidator
    URI_TEMPLATE: ClassVar[str] = "/admin/login/"
    METHOD: ClassVar[HttpMethod] = HttpMethod.POST
    MODE: ClassVar[DataMode] = DataMode.NONE

    def data(self, **kwargs) -> dict:
        return {
            "username": kwargs.get("username"),
            "password": kwargs.get("password"),
            "next": "/admin/",
        }


class AdminPageResource(HttpResource):

    EXTRACTOR: ClassVar[Tag | None] = Tag(category="extractor", value="django_client")
    URI_TEMPLATE: ClassVar[str] = "/admin/"
    METHOD: ClassVar[HttpMethod] = HttpMethod.GET


def create_auth_from_cookies(resource: HttpResource) -> HttpAuth:
    """
    Create an HttpAuth object from the cookies in a resource's response headers.
    """
    if resource.result is None:
        raise ValueError("Resource has no result to extract cookies from")
    cookies = resource.result.head.get("set-cookie", "")
    if not cookies:
        return HttpAuth()
    return HttpAuth(headers={"Cookie": cookies})


def patch_signature_auth(resource: Resource[HttpSignature], auth: HttpAuth) -> Resource[HttpSignature]:
    """
    Patch the signature.auth field on a resource to use the provided auth object.
    Useful for transferring authentication (like cookies) from one resource to another.
    """
    if resource.signature is None:
        raise ValueError("Cannot patch auth on a resource without a signature")
    patched_signature = resource.signature.model_copy(update={"auth": auth})
    resource.signature = patched_signature
    return resource


class TestDjangoClientExtractor:

    def test_extractor_initialization(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)
        assert extractor.config._namespace == config._namespace
        assert isinstance(extractor._client, Client)

    def test_extractor_set_client(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)
        custom_client = Client()
        extractor.set_client(custom_client)
        assert extractor._client is custom_client

    def test_extractor_tag(self):
        assert DjangoClientExtractor.tag == Tag(category="extractor", value="django_client")

    def test_build_request_kwargs_get(self):
        config = create_config("http_resource", {"allow_redirects": True})
        extractor = DjangoClientExtractor(config)

        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.GET,
            url="/test/",
            headers={"Accept": "application/json"},
            mode=DataMode.NONE,
        )
        kwargs = extractor._build_request_kwargs(signature)

        assert kwargs["path"] == "/test/"
        assert kwargs["follow"] is True
        assert kwargs["headers"] == {"Accept": "application/json"}
        assert "data" not in kwargs

    def test_build_request_kwargs_with_auth_headers(self):
        config = create_config("http_resource", {"allow_redirects": False})
        extractor = DjangoClientExtractor(config)

        # Non-Cookie auth headers should be passed through
        auth = HttpAuth(headers={"Authorization": "Bearer token123"})
        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.GET,
            url="/test/",
            headers={},
            auth=auth,
            mode=DataMode.NONE,
        )
        kwargs = extractor._build_request_kwargs(signature)

        assert kwargs["headers"]["Authorization"] == "Bearer token123"
        assert kwargs["follow"] is False

    def test_apply_auth_cookies_to_client(self):
        """Cookie auth headers are applied to the client's cookie jar, not request headers."""
        config = create_config("http_resource", {"allow_redirects": False})
        extractor = DjangoClientExtractor(config)

        auth = HttpAuth(headers={"Cookie": "sessionid=abc123; csrftoken=xyz789"})
        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.GET,
            url="/test/",
            headers={},
            auth=auth,
            mode=DataMode.NONE,
        )

        # Apply cookies to client
        extractor._apply_auth_cookies(signature)

        # Verify cookies are set on the client (cookies are Morsel objects)
        assert extractor._client.cookies["sessionid"].value == "abc123"
        assert extractor._client.cookies["csrftoken"].value == "xyz789"

        # Verify Cookie header is NOT passed in request kwargs
        kwargs = extractor._build_request_kwargs(signature)
        assert "headers" not in kwargs or "Cookie" not in kwargs.get("headers", {})

    def test_build_request_kwargs_with_auth_parameters(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)

        auth = HttpAuth(parameters={"api_key": "secret"})
        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.GET,
            url="/test/?existing=param",
            headers={},
            auth=auth,
            mode=DataMode.NONE,
        )
        kwargs = extractor._build_request_kwargs(signature)

        assert "api_key=secret" in kwargs["path"]
        assert "existing=param" in kwargs["path"]

    def test_build_request_kwargs_post_json(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)

        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.POST,
            url="/test/",
            headers={},
            data={"key": "value"},
            mode=DataMode.JSON,
        )
        kwargs = extractor._build_request_kwargs(signature)

        assert kwargs["data"] == '{"key":"value"}'
        assert kwargs["content_type"] == "application/json; charset=utf-8"

    def test_build_request_kwargs_post_form_data(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)

        signature = HttpSignature(
            uri="/login/",
            method=HttpMethod.POST,
            url="/login/",
            headers={},
            data={"username": "test", "password": "secret"},
            mode=DataMode.NONE,
        )
        kwargs = extractor._build_request_kwargs(signature)

        assert kwargs["data"] == {"username": "test", "password": "secret"}
        assert "content_type" not in kwargs

    def test_extract_handles_exception(self):
        config = create_config("http_resource", {})
        extractor = DjangoClientExtractor(config)

        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection failed")
        extractor.set_client(mock_client)

        signature = HttpSignature(
            uri="/test/",
            method=HttpMethod.GET,
            url="/test/",
            headers={},
            mode=DataMode.NONE,
        )
        result = extractor.extract(signature)
        assert isinstance(result, Resource)

        assert result.status == 500
        assert result.result is not None
        assert result.result.errors == "Connection failed"


@pytest.mark.django_db
class TestDjangoClientAdminLogin:
    """
    Tests that demonstrate a full auth flow with admin login using TestClientExtractor.
    """

    @pytest.fixture(autouse=True)
    def setup_admin_user(self, django_user_model):
        self.admin_user = django_user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )

    def test_login_succeeds_and_reaches_admin(self):
        resource = AdminLoginResource()
        resource = resource.extract(username="admin", password="adminpass").close()
        assert resource.status == 200
        assert resource.result is not None
        assert resource.result.body is not None
        assert "Site administration" in resource.result.body
        assert "Log in" not in resource.result.body

    def test_admin_page_without_auth_shows_login(self):
        resource = AdminPageResource()
        resource = resource.extract().close()
        assert resource.status == 200
        assert resource.result is not None
        assert resource.result.body is not None
        assert "Log in" in resource.result.body
        assert "Site administration" not in resource.result.body

    def test_admin_page_accessible_through_auth_flow(self):
        """Test the auth flow: login, extract cookies, patch signature, access admin."""
        # Step 1: Login and get cookies
        login_resource = AdminLoginResource()
        login_resource = login_resource.extract(username="admin", password="adminpass").close()
        assert login_resource.status == 200

        # Step 2: Extract auth from login cookies
        auth = create_auth_from_cookies(login_resource)
        assert auth.headers is not None
        assert "Cookie" in auth.headers

        # Step 3: Create admin resource and prepare its signature
        admin_resource = AdminPageResource()
        signature = admin_resource.prepare_extract()
        admin_resource.signature = signature

        # Step 4: Patch auth onto the signature
        admin_resource = patch_signature_auth(admin_resource, auth)
        assert admin_resource.signature is not None
        assert admin_resource.signature.auth is not None
        assert admin_resource.signature.auth.headers is not None
        assert "Cookie" in admin_resource.signature.auth.headers

        # Step 5: Extract with the patched signature (no args = uses existing signature)
        admin_resource = admin_resource.extract().close()
        assert admin_resource.status == 200
        assert admin_resource.result is not None
        assert admin_resource.result.body is not None
        assert "Site administration" in admin_resource.result.body
        assert "Log in" not in admin_resource.result.body
