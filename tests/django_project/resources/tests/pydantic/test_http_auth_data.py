from typing import Any, ClassVar, Type

import pytest

from datagrowth.registry import Tag
from datagrowth.resources.http.pydantic import HttpResource
from datagrowth.resources.http.signature import HttpMethod
from datagrowth.resources.storage.file_system import FileSystemStorage
from datagrowth.signatures import DataMode, InputsValidator


class AdminLoginInputsValidator(InputsValidator):
    SENSITIVE_NAMES = ("password",)

    username: str
    password: str


class AdminLoginResource(HttpResource):
    EXTRACTOR: ClassVar[Tag | None] = Tag(category="extractor", value="django_client")
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = AdminLoginInputsValidator
    URI_TEMPLATE: ClassVar[str] = "/admin/login/"
    METHOD: ClassVar[HttpMethod] = HttpMethod.POST
    MODE: ClassVar[DataMode] = DataMode.NONE

    def data(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "username": kwargs.get("username"),
            "password": kwargs.get("password"),
            "next": "/admin/",
        }


@pytest.fixture(autouse=True)
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )


@pytest.mark.django_db
def test_admin_login_sends_sensitive_data_without_adding_it_to_signature() -> None:
    resource = AdminLoginResource()
    signature = resource.prepare_extract(username="admin", password="adminpass")

    assert signature.kwargs == {"username": "admin"}
    assert signature.data == {"username": "admin", "password": None, "next": "/admin/"}
    assert signature.auth is not None
    assert signature.auth.data == {"password": "adminpass"}
    assert signature.get_data() == {"username": "admin", "password": "adminpass", "next": "/admin/"}
    assert "adminpass" not in signature.model_dump_json()

    resource.signature = signature
    extracted = resource.extract()

    assert extracted.status == 200
    assert extracted.result is not None
    assert extracted.result.body is not None
    assert "Site administration" in extracted.result.body


@pytest.mark.django_db
def test_admin_login_password_is_absent_from_snapshot_storage(tmp_path) -> None:
    resource = AdminLoginResource()
    assert isinstance(resource.storage, FileSystemStorage)
    resource.storage.config.update({
        "allow_read": True,
        "allow_write": True,
        "allow_save": True,
        "allow_load": False,
        "snapshots": True,
        "directories": {
            "project": None,
            "data": str(tmp_path / "data"),
            "snapshots": str(tmp_path / "snapshots"),
            "tmp": str(tmp_path / "tmp"),
        },
    })

    extracted = resource.extract(username="admin", password="adminpass").close()

    assert extracted.status == 200
    snapshot_files = list((tmp_path / "snapshots").rglob("data.json"))
    assert len(snapshot_files) == 1
    assert "adminpass" not in snapshot_files[0].read_text(encoding="utf-8")
