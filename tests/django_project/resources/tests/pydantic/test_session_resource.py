from typing import ClassVar, Type, Self, cast
import re
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, UTC
import pytest
from pydantic import ValidationError

from datagrowth.exceptions import DGSessionInputRequired, DGHttpError40X, DGSessionNotReady, DGSessionNotCompleted
from datagrowth.registry import Tag
from datagrowth.resources.pydantic import Result
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.signatures import InputsValidator, DataMode, Signature
from datagrowth.resources.http.signature import HttpSignature, HttpMethod, HttpAuth
from datagrowth.resources.http.pydantic import HttpResource
from datagrowth.resources.session.pydantic import SessionResource, Session, ResourceStep


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

    def update(self, other: ResourceProtocol) -> None:
        super().update(other)
        # Django login returns 200 even on failure, check for sessionid cookie
        if self.result is None:
            return
        cookies = self.result.head.get("set-cookie", "")
        if "sessionid" not in cookies:
            self.status = 403
            self.result = Result(
                content_type=self.result.content_type,
                head=self.result.head,
                body=None,
                errors="Login failed (no session cookie)"
            )


class AdminPageInputsValidator(InputsValidator):
    page_type: str
    page: int


class AdminPageResource(HttpResource):

    EXTRACTOR: ClassVar[Tag | None] = Tag(category="extractor", value="django_client")
    URI_TEMPLATE: ClassVar[str] = "/admin/"
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = AdminPageInputsValidator
    METHOD: ClassVar[HttpMethod] = HttpMethod.GET
    PARAMETERS: ClassVar[dict[str, str] | None] = {
        "page_type": "{page_type}",
        "page": "{page}",
    }

    def next(self) -> Self | None:
        if not self.signature:
            return None
        inputs = self.INPUTS_VALIDATOR.from_inputs(*self.signature.args, **self.signature.kwargs)
        current_page = inputs.get_argument("page")
        if current_page >= 2:
            return None
        next_kwargs = dict(self.signature.kwargs)
        next_kwargs["page"] += 1
        next_signature = self.signature.model_copy(update={"kwargs": next_kwargs})
        return self.__class__(signature=next_signature)


class AdminSessionResource(SessionResource[AdminPageResource]):

    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")
    main: AdminPageResource
    SESSION_STEPS: ClassVar[list[ResourceStep]] = [
        ResourceStep(name="login", resource=AdminLoginResource)
    ]

    def prepare_main_signature(self, signature: Signature) -> HttpSignature:
        # Patch the signature with session auth (cookies stored in session.headers)
        auth = HttpAuth(headers=dict(self.session.headers), parameters=dict(self.session.parameters))
        return cast(HttpSignature, signature.model_copy(update={"auth": auth}))

    def login_update_session(self, login_resource: AdminLoginResource, session: Session) -> None:
        assert login_resource.result is not None and not login_resource.result.errors, "Session update callback unexpectedly called."  # noqa: E501
        cookies = login_resource.result.head.get("set-cookie", "")
        session.headers["Cookie"] = cookies
        session.expire_at = self._parse_cookie_expiration(cookies)
        session.is_ready = True

    @staticmethod
    def _parse_cookie_expiration(cookies: str) -> datetime | None:
        """
        Parse expiration time from cookie string.
        Looks for 'expires=' or 'max-age=' attributes in sessionid cookie.
        Returns None if no expiration found (session cookie).
        """

        # Try to find max-age first (more reliable)
        max_age_match = re.search(r"max-age=(\d+)", cookies, re.IGNORECASE)
        if max_age_match:
            max_age_seconds = int(max_age_match.group(1))
            return datetime.now(UTC) + timedelta(seconds=max_age_seconds)

        # Try to find expires attribute
        expires_match = re.search(r"expires=([^;,]+)", cookies, re.IGNORECASE)
        if expires_match:
            try:
                expires_str = expires_match.group(1).strip()
                expire_dt = parsedate_to_datetime(expires_str)
                # Ensure timezone-aware (parsedate_to_datetime should return aware datetime)
                if expire_dt.tzinfo is None:
                    expire_dt = expire_dt.replace(tzinfo=UTC)
                return expire_dt
            except (ValueError, TypeError):
                pass

        # No expiration found - session cookie (valid until browser closes)
        return None


# ==============================
# Pydantic helpers
# ==============================


def test_resource_step_name_must_start_with_letter():
    with pytest.raises(ValidationError, match="Expected ResourceStep.name to start with a letter"):
        ResourceStep(name="1st step", resource=AdminLoginResource)


def test_resource_step_sets_identity_from_name():
    step = ResourceStep(name="Session Login Step", resource=AdminLoginResource)
    assert step.identity == "session_login_step"


def test_resource_step_accepts_valid_identity():
    step = ResourceStep(name="Session Login Step", identity="custom_identity", resource=AdminLoginResource)
    assert step.identity == "custom_identity"


def test_resource_step_rejects_invalid_identity():
    with pytest.raises(ValidationError, match="Expected ResourceStep.identity to be lowercase"):
        ResourceStep(name="Session Login Step", identity="CustomIdentity", resource=AdminLoginResource)


# ==============================
# extract_session
# ==============================


@pytest.mark.django_db
class TestExtractSession:

    @pytest.fixture(autouse=True)
    def setup_admin_user(self, django_user_model):
        self.admin_user = django_user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )

    def test_extract_session_success(self) -> None:
        admin_page = AdminPageResource()
        admin_session = AdminSessionResource(main=admin_page)
        session: Session = admin_session.extract_session(username="admin", password="adminpass")

        # Verify session is ready and has auth cookies
        assert session.is_ready is True
        assert session.is_valid() is True
        assert "Cookie" in session.headers
        assert "sessionid" in session.headers["Cookie"]
        assert "csrftoken" in session.headers["Cookie"]

        # Verify that session steps have been completed
        assert "login" in admin_session.session_steps_completed
        login_completion = admin_session.session_steps_completed["login"]
        assert login_completion.step == "login"
        assert login_completion.status == 200
        assert login_completion.is_success is True
        assert login_completion.is_valid() is True
        assert login_completion.hash != 0

    def test_extract_session_login_failure_raises_error(self) -> None:
        admin_page = AdminPageResource()
        admin_session = AdminSessionResource(main=admin_page)

        with pytest.raises(DGHttpError40X, match=r"403[\s\S]*Login failed"):
            admin_session.extract_session(username="admin", password="wrongpassword")

        # Verify step was marked as completed but with failure
        assert "login" in admin_session.session_steps_completed
        login_completion = admin_session.session_steps_completed["login"]
        assert login_completion.is_success is False
        assert login_completion.is_valid() is False

        # Verify SessionResource status indicates which step failed (negative = step index + 1)
        assert admin_session.status == -1  # first step failed

    def test_extract_session_step_completion_has_correct_hash(self) -> None:
        """Verify that step completion records the signature hash for cache invalidation."""
        admin_page = AdminPageResource()
        admin_session = AdminSessionResource(main=admin_page)
        admin_session.extract_session(username="admin", password="adminpass")

        login_completion = admin_session.session_steps_completed["login"]

        # Build a login resource to get its expected signature hash
        login_resource = AdminLoginResource()
        expected_signature = login_resource.prepare_extract(username="admin", password="adminpass")

        assert login_completion.hash == expected_signature.hash

    def test_extract_session_invalid_inputs_raises_input_required(self) -> None:
        """Verify that wrong inputs raise DGSessionInputRequired with schema info."""
        admin_page = AdminPageResource()
        admin_session = AdminSessionResource(main=admin_page)

        with pytest.raises(DGSessionInputRequired, match="Missing or invalid inputs") as exc_info:
            admin_session.extract_session(key="some_value")  # wrong input name

        # Verify the exception contains the resource
        assert exc_info.value.resource is not None
        step_resource = exc_info.value.resource

        # Verify that login step did not complete
        assert "login" not in admin_session.session_steps_completed

        # Verify the resource exposes its INPUTS_VALIDATOR for schema introspection
        inputs_validator = step_resource.INPUTS_VALIDATOR
        assert inputs_validator is not None

        # Get the JSON schema from Pydantic to expose required inputs
        schema = inputs_validator.model_json_schema()
        assert "properties" in schema

        # Verify the schema contains the expected fields (username and password)
        properties = schema["properties"]
        assert "username" in properties
        assert "password" in properties

        # Verify required fields are marked
        assert "required" in schema
        assert "username" in schema["required"]
        assert "password" in schema["required"]


# ==============================
# extract
# ==============================


@pytest.mark.django_db
class TestExtract:

    @pytest.fixture(autouse=True)
    def setup_admin_user(self, django_user_model):
        django_user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )

    @staticmethod
    def _skip_when_recording_snapshots(resource: AdminSessionResource) -> None:
        if resource.storage is not None and resource.storage.config.snapshots:
            pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    def test_extract_progresses_session_state(self) -> None:
        session_resource = AdminSessionResource(main=AdminPageResource())
        session_resource = session_resource.extract(page_type="new", page=1)
        assert session_resource.is_ready() is False
        assert session_resource.is_completed() is False
        extracted = session_resource.extract(username="admin", password="adminpass")
        assert extracted.is_ready() is True
        assert extracted.is_completed() is True

    @pytest.mark.snapshots
    def test_extract_completes_session_and_main(self) -> None:
        session_resource = AdminSessionResource(main=AdminPageResource())
        session_resource = session_resource.extract(page_type="complete", page=1)
        extracted = session_resource.extract(username="admin", password="adminpass")
        extracted.close()

        self._skip_when_recording_snapshots(session_resource)

        assert isinstance(extracted, AdminSessionResource)
        assert extracted.session.is_ready is True
        assert extracted.session.is_valid() is True
        assert "login" in extracted.session_steps_completed
        assert extracted.signature is not None
        assert extracted.main.result is not None
        assert extracted.main.result.body is not None
        assert "Site administration" in extracted.main.result.body
        assert "Log in" not in extracted.main.result.body
        assert extracted.status == 200
        assert extracted.success is True

    @pytest.mark.snapshots
    def test_extract_reuses_session_on_second_extract(self) -> None:
        session_resource = AdminSessionResource(main=AdminPageResource())
        session_resource = session_resource.extract(page_type="reuse", page=1)
        first = session_resource.extract(username="admin", password="adminpass")
        first.close()
        login_steps = dict(first.session_steps_completed)
        session_headers = dict(first.session.headers)

        second = first.extract()
        second.close()

        self._skip_when_recording_snapshots(session_resource)

        assert second.session_steps_completed == login_steps
        assert second.session.headers == session_headers
        assert second.main.result is not None
        assert second.main.result.body is not None
        assert "Site administration" in second.main.result.body
        assert second.status == 200
        assert second.success is True

    @pytest.mark.snapshots
    def test_extract_next_reuses_session(self) -> None:
        session_resource = AdminSessionResource(main=AdminPageResource())
        session_resource = session_resource.extract(page_type="next", page=1)
        extracted = session_resource.extract(username="admin", password="adminpass")
        extracted.close()
        login_steps = dict(extracted.session_steps_completed)

        next_session = extracted.next()
        assert next_session is not None
        next_extracted = next_session.extract()
        next_extracted.close()

        self._skip_when_recording_snapshots(session_resource)

        assert isinstance(next_extracted, AdminSessionResource)
        assert next_extracted is not extracted
        assert next_extracted.session_steps_completed == login_steps
        assert next_extracted.session.headers == extracted.session.headers
        assert isinstance(next_extracted.main, AdminPageResource)
        assert next_extracted.main.signature is not None
        assert next_extracted.main.signature.kwargs["page_type"] == "next"
        assert next_extracted.main.signature.kwargs["page"] == 2
        assert next_extracted.main.result is not None
        assert next_extracted.main.result.body is not None
        assert "Site administration" in next_extracted.main.result.body
        assert next_extracted.status == 200
        assert next_extracted.success is True


# ==============================
# next
# ==============================


@pytest.mark.django_db
class TestSessionResourceNext:

    @pytest.fixture(autouse=True)
    def setup_admin_user(self, django_user_model):
        django_user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )

    def _completed_session(self) -> AdminSessionResource:
        admin_session = AdminSessionResource(main=AdminPageResource())
        admin_session = admin_session.extract(page_type="next", page=1)
        return admin_session.extract(username="admin", password="adminpass")

    def test_next_returns_new_session_resource_with_carried_session(self) -> None:
        admin_session = self._completed_session()
        original_session = admin_session.session.model_copy()
        original_steps = dict(admin_session.session_steps_completed)

        next_session = admin_session.next()
        assert next_session is not None
        assert isinstance(next_session, AdminSessionResource)
        assert next_session is not admin_session
        assert next_session.main is not admin_session.main
        assert isinstance(next_session.main, AdminPageResource)
        assert next_session.main.signature is not None
        assert next_session.main.signature.kwargs["page_type"] == "next"
        assert next_session.main.signature.kwargs["page"] == 2
        assert next_session.session == original_session
        assert next_session.session_steps_completed == original_steps
        assert next_session.main.result is None
        assert next_session.status == 0

    def test_next_returns_none_when_main_has_no_follow_up(self) -> None:
        admin_session = self._completed_session()
        page2_session = admin_session.next()
        assert page2_session is not None
        page2_session = page2_session.extract()

        assert page2_session.next() is None

    def test_next_requires_completed_session(self) -> None:
        admin_session = AdminSessionResource(main=AdminPageResource())

        with pytest.raises(DGSessionNotReady):
            admin_session.next()

    def test_next_requires_completed_main(self) -> None:
        admin_session = AdminSessionResource(main=AdminPageResource())
        admin_session.extract_session(username="admin", password="adminpass")

        with pytest.raises(DGSessionNotCompleted):
            admin_session.next()
