from typing import Type, ClassVar, Any, Self, Generic, get_args, get_origin
from typing_extensions import TypeVar
import json
import logging
import re
from datetime import datetime, UTC
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from datagrowth.configuration.types import create_config
from datagrowth.exceptions import (DGResourceException, DGExtractionDisabled, DGSessionNotReady,
                                   DGSessionNotCompleted, DGSessionInputRequired)
from datagrowth.registry import Tag
from datagrowth.signatures import Signature
from datagrowth.resources.protocols import ResourceProtocol, ResourceExtractorProtocol, ResourceStorageProtocol
from datagrowth.resources.pydantic import Resource


MainResourceSignatureType = TypeVar("MainResourceSignatureType", bound=Signature, default=Signature)
MainResourceType = TypeVar("MainResourceType", bound=Resource)


log = logging.getLogger("datagrowth")


class Session(BaseModel):
    parameters: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    is_ready: bool = Field(default=False)
    expire_at: datetime | None = None

    def is_valid(self, now: datetime | None = None) -> bool:
        if not self.is_ready:
            return False
        if not self.expire_at:
            return True
        now = now or datetime.now(UTC)
        return self.expire_at > now


class ResourceStep(BaseModel):
    name: str
    resource: Type[Resource]
    identity: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict, description="Configuration for the Resource.")
    initialization: dict[str, Any] = Field(default_factory=dict, description="Construction kwargs apart from config.")

    def build_resource(self) -> Resource:
        config = create_config(self.resource.NAMESPACE.value, self.configuration)
        return self.resource(config=config, **self.initialization)

    #####################
    # Pydantic plumbing
    #####################

    @staticmethod
    def python_variable_string(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.match(r"^[A-Za-z]", value):
            raise ValueError(f"Expected ResourceStep.name to start with a letter, got: {value}")
        return value

    @model_validator(mode="after")
    def set_and_validate_identity(self) -> Self:
        if not self.identity:
            self.identity = self.python_variable_string(self.name)
        if not self.identity:
            raise ValueError(f"Could not derive ResourceStep.identity from name: {self.name}")
        if not re.match(r"^[a-z][a-z0-9_]*$", self.identity):
            raise ValueError(
                "Expected ResourceStep.identity to be lowercase and a python variable name, "
                f"got: {self.identity}"
            )
        return self


class ResourceStepCompleted(BaseModel):
    step: str
    hash: int
    status: int
    is_success: bool
    expire_at: datetime | None = None

    def is_valid(self, now: datetime | None = None) -> bool:
        if not self.is_success:
            return False
        if not self.expire_at:
            return True
        now = now or datetime.now(UTC)
        return self.expire_at > now


class SessionResource(Resource[MainResourceSignatureType], Generic[MainResourceType, MainResourceSignatureType]):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="session_resource")
    SESSION_STEPS: ClassVar[list[ResourceStep]]

    session: Session = Field(default_factory=lambda: Session())
    session_steps_completed: dict[str, ResourceStepCompleted] = Field(default_factory=dict)
    main: MainResourceType

    #####################
    # Implementation
    #####################

    def prepare_extract(self, *args: Any, **kwargs: Any) -> MainResourceSignatureType:
        inputs = self.main.INPUTS_VALIDATOR.from_inputs(*args, **kwargs)
        return self.main.prepare_inputs(inputs)  # type: ignore[return-value]

    def extract(self, *args: Any, **kwargs: Any) -> Self:
        # Use Resource base class to possibly restore a previous SessionResource and generate the signature
        session_args = args
        session_kwargs = kwargs
        start_session = False
        if self.signature:
            session_args = self.signature.args
            session_kwargs = self.signature.kwargs
            start_session = True
        try:
            resource = super().extract(*session_args, **session_kwargs)
        except DGExtractionDisabled:
            log.debug("Unable to get SessionResource from storage. Moving on to extracting using delegates.")
            resource = self
        self.signature = resource.signature

        # Return if the SessionResource has completed successfully and was loaded from disk
        if resource.main.success:
            return resource
        # Retry and return the main Resource when it failed, but session is still valid.
        elif not resource.main.success and resource.session.is_valid():
            resource.extract_main()
            return resource
        # Reset session and session steps if the session is expired.
        elif resource.session.is_ready and not resource.session.is_valid():
            resource.session = Session()
            resource.session_steps_completed = {}
        # Return if session was only getting prepared. Use is_ready to detect session state.
        elif not start_session:
            return resource

        # Extract a Session instance possibly raising DGSessionNotReady when extra input is needed.
        resource.session = resource.extract_session(*args, **kwargs)
        # The handle_errors method is called here to allow child classes to check the session process.
        resource.handle_errors()
        resource.close()  # preserve updates from handle_errors
        # Extract main content with a valid session
        resource.extract_main()

        return resource

    def _require_delegated_access(self) -> None:
        if not self.is_ready():
            raise DGSessionNotReady("SessionResource is not ready.", resource=self)
        if not self.is_completed():
            raise DGSessionNotCompleted("SessionResource is not completed.", resource=self)

    @property
    def success(self) -> bool:
        self._require_delegated_access()
        return self.main.success

    @property
    def content(self) -> tuple[str | None, Any]:
        self._require_delegated_access()
        return self.main.content

    def next(self) -> Self | None:
        self._require_delegated_access()
        next_main = self.main.next()
        if next_main is None:
            return None
        update: dict[str, Any] = {
            "main": next_main,
            "session": self.session.model_copy(),
            "session_steps_completed": dict(self.session_steps_completed),
            "result": None,
            "status": 0,
            "metadata": {},
        }
        # When calling extract on the next Resource we need it to use correct kwargs from main.
        if self.signature is not None and next_main.signature is not None:
            update["signature"] = self.signature.model_copy(update={"kwargs": dict(next_main.signature.kwargs)})
        return self.model_copy(update=update)

    def update(self, other: ResourceProtocol) -> None:
        if not isinstance(other, self.main.__class__):
            raise TypeError(f"Expected a {self.main.__class__} as input to update with, got {other.__class__.__name__}.")  # noqa: E501
        self.status = other.status
        self.metadata = dict(other.metadata)

    def handle_errors(self) -> None:
        if not self.session.is_valid():
            raise DGSessionNotReady("No valid Session after extraction.", resource=self)

    def close_snapshot(self, storage: ResourceStorageProtocol) -> None:
        assert self.signature is not None, "Expected signature to be set before closing snapshot."
        if not self.is_completed():
            return
        content_type, data = self.main.content
        if not data:
            return
        extension = self._snapshot_extension(content_type)
        storage.write(self.signature, f"main.{extension}", self._serialize_snapshot_content(data, extension))

    #####################
    # Specialization
    #####################

    def is_ready(self) -> bool:
        if len(self.session_steps_completed) < len(self.SESSION_STEPS):
            return False
        return all(
            step.identity in self.session_steps_completed
            and self.session_steps_completed[step.identity].is_valid()
            for step in self.SESSION_STEPS
            if step.identity
        )

    def is_completed(self) -> bool:
        if not self.is_ready():
            return False
        if self.main.result is None:
            return False
        return True

    def prepare_main_signature(self, signature: MainResourceSignatureType) -> MainResourceSignatureType:
        """
        Prepare the main resource's signature using the state from the Session.
        Override this method to customize how session state is applied to the main resource.
        """
        raise NotImplementedError

    def extract_main(self) -> None:
        assert self.signature, "Cannot extract main when SessionResource.signature is not set"
        # Prepare the initial signature from the stored args/kwargs
        initial_signature = self.main.prepare_extract(*self.signature.args, **self.signature.kwargs)
        # Let the subclass apply session auth to the signature
        main_signature = self.prepare_main_signature(initial_signature)
        self.main.signature = main_signature
        # Extract using the prepared signature (no args = uses existing signature)
        main = self.main.extract()
        self.update(main)
        return None

    def _update_session(self, session_step: ResourceStep, session_resource: Resource, session: Session) -> None:
        # Early exit when something went wrong during iterating session steps
        if not session_resource.success:
            return None
        # Use child class callback to update the Session
        step_update_callback = f"{session_step.identity}_update_session"
        callback = getattr(self, step_update_callback, None)
        if callback is None:
            raise RuntimeError(f"Update callback '{step_update_callback}' does not exist.")
        callback(session_resource, session)
        return None

    def _set_step_completed(self, step: ResourceStep, resource: Resource, is_success: bool | None = None) -> None:
        assert step.identity, "Expected identity to get set based on step name before completing steps."
        assert resource.signature, "Expected signature to be set to use it for step completion."
        success = is_success if is_success is not None else resource.success
        completion = ResourceStepCompleted(
            step=step.identity,
            hash=resource.signature.hash,
            status=resource.status,
            is_success=success,
            expire_at=resource.purge_at if success else None
        )
        self.session_steps_completed[completion.step] = completion

    def extract_session(self, *args: Any, **kwargs: Any) -> Session:
        # Iterate over steps and try to build session state through session steps progress using inputs
        # Note that invalid inputs will raise DGSessionInputRequired,
        # which is meant to get caught for human-in-loop flows
        for ix, step in enumerate(self.SESSION_STEPS):
            assert step.identity, "Expected identity to get set based on step name"
            # Continue to next step if the step was completed and is still valid
            if completion := self.session_steps_completed.get(step.identity):
                if completion and completion.is_valid():
                    continue
            # Start step extraction if we hit a non-completed step
            step_resource = step.build_resource()
            try:
                step_resource = step_resource.extract(*args, **kwargs)
                step_resource.close()
            except ValidationError:
                raise DGSessionInputRequired(f"Missing or invalid inputs for step: {step.name}", resource=step_resource)
            except DGResourceException:
                self.status = (ix + 1) * -1
                self._set_step_completed(step, step_resource, is_success=False)
                self.close()
                raise
            self._update_session(step, step_resource, self.session)
            self._set_step_completed(step, step_resource)
            self.close()
        return self.session

    #####################
    # Override plumbing
    #####################

    @property
    def extractor(self) -> ResourceExtractorProtocol[MainResourceSignatureType] | None:
        """
        This override forces a SessionResource to leave extraction to session and main delegates.
        """
        return None

    def __class_getitem__(cls, params: Any) -> Any:
        """
        Derive the main resource's Resource[Sig] type parameter when only the main resource type is given.
        """
        if not isinstance(params, tuple):
            params = (params,)
        if len(params) == 1:
            main_type = params[0]
            params = (main_type, cls._resource_signature_type(main_type))
        return super().__class_getitem__(params)

    #####################
    # Helpers
    #####################

    @staticmethod
    def _resource_signature_type(resource_type: type) -> type[Signature]:
        for cls in resource_type.__mro__:
            for base in getattr(cls, "__orig_bases__", ()):
                if get_origin(base) is Resource:
                    args = get_args(base)
                    if args and not isinstance(args[0], TypeVar):
                        return args[0]
        return Signature

    @staticmethod
    def _snapshot_extension(content_type: str | None) -> str:
        if content_type is None:
            return "txt"
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type in ("application/json", "application/ld+json") or media_type.endswith("+json"):
            return "json"
        if media_type == "text/html":
            return "html"
        if media_type == "text/plain":
            return "txt"
        if media_type.startswith("text/"):
            return "txt"
        return "txt"

    @staticmethod
    def _serialize_snapshot_content(data: Any, extension: str) -> bytes | str:
        if extension == "json":
            if isinstance(data, (dict, list)):
                return json.dumps(data, indent=4)
            if isinstance(data, str):
                try:
                    return json.dumps(json.loads(data), indent=4)
                except (json.JSONDecodeError, TypeError):
                    return data
            return json.dumps(data, indent=4, default=str)
        if isinstance(data, bytes):
            return data
        if data is None:
            return ""
        return str(data)
