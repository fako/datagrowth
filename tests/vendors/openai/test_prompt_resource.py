import pytest

from pathlib import Path
from typing import ClassVar
from uuid import uuid4
from pydantic import BaseModel

from datagrowth.exceptions import DGHttpNoAuthentication
from datagrowth.configuration import create_config
from datagrowth.llm import LLMModel, LLMVendors
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.http.signature import HttpMethod
from datagrowth.resources.prompt.pydantic import PromptInputsValidator
from datagrowth.resources.storage.file_system import FileSystemStorage
from datagrowth.vendors.openai.resources import OPENAI_DEFAULT_MODEL, OPENAI_DEFAULT_TAG, OpenaiPromptResource


class MockOpenaiPromptResource(OpenaiPromptResource):
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")


PROMPTS_DIRECTORY = Path(__file__).parent / "prompts"


@pytest.fixture
def resource() -> MockOpenaiPromptResource:
    config = create_config("openai", {"api_key": "openai-test-key"})
    return MockOpenaiPromptResource(config=config, llm=OPENAI_DEFAULT_TAG)


def configure_storage(resource: MockOpenaiPromptResource) -> None:
    assert isinstance(resource.storage, FileSystemStorage)
    resource.storage.config.update({
        "directories": {
            "project": None,
            "data": str(Path("/tmp/data")),
            "snapshots": str(Path("/tmp/snapshots")),
            "tmp": str(Path("/tmp")),
            "templates": str(PROMPTS_DIRECTORY),
        },
    })


# ==============================
# validate_inputs
# ==============================


def test_validate_inputs_accepts_llm_allowed_options() -> None:
    inputs = PromptInputsValidator.from_llm(
        OPENAI_DEFAULT_MODEL,
        "chat.tpl",
        options={"n": 1, "temperature": 0.7, "top_p": 0.95},
    )

    assert inputs.args == ("chat.tpl", None)
    assert inputs.kwargs["options"] == {"n": 1, "temperature": 0.7, "top_p": 0.95}


def test_validate_inputs_rejects_unsupported_option() -> None:
    with pytest.raises(ValueError, match="unsupported option 'frequency_penalty'"):
        PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.tpl", options={"frequency_penalty": 0.1})


def test_validate_inputs_rejects_option_with_invalid_type() -> None:
    with pytest.raises(ValueError, match="option 'temperature'.*expected type 'float'"):
        PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.tpl", options={"temperature": "high"})


def test_validate_inputs_accepts_template_name_with_tpl_extension() -> None:
    inputs = PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.tpl")
    assert inputs.template == "chat.tpl"


def test_validate_inputs_rejects_template_name_without_tpl_extension() -> None:
    with pytest.raises(ValueError, match="expected template name to have the .tpl or json.tpl extension"):
        PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.txt")


def test_validate_inputs_defaults_method_to_post() -> None:
    inputs = PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.tpl")
    assert inputs.method == HttpMethod.POST


def test_validate_inputs_rejects_non_post_method() -> None:
    with pytest.raises(ValueError, match="only supports POST method"):
        PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.tpl", method=HttpMethod.GET)


def test_validate_inputs_rejects_json_template_without_output() -> None:
    with pytest.raises(ValueError, match="requires output to be set"):
        PromptInputsValidator.from_llm(OPENAI_DEFAULT_MODEL, "chat.json.tpl")


def test_validate_inputs_sets_json_schema_for_json_template() -> None:
    class JsonOutput(BaseModel):
        answer: str

    inputs = PromptInputsValidator.from_llm(
        OPENAI_DEFAULT_MODEL,
        "chat.json.tpl",
        output=JsonOutput,
        context={"name": "DataGrowth"},
    )

    assert "json_schema" in inputs.context
    assert inputs.context["json_schema"] == JsonOutput.model_json_schema()


# ==============================
# prepare_extract
# ==============================


def test_prepare_extract_renders_template_and_builds_signature(resource: MockOpenaiPromptResource) -> None:
    configure_storage(resource)
    signature = resource.prepare_extract("hello_world.tpl", context={"name": "DataGrowth"}, options={"n": 1})

    assert signature.method == HttpMethod.POST
    assert signature.url == "https://api.openai.com/v1/chat/completions"
    assert signature.kwargs["context"] == {"name": "DataGrowth"}
    assert signature.kwargs["options"] == {"n": 1}
    assert isinstance(signature.data, dict)
    assert signature.data["n"] == 1
    assert signature.data["model"] == OPENAI_DEFAULT_MODEL.identifier
    assert signature.data["messages"][0]["role"] == "user"
    assert signature.data["messages"][0]["content"].strip() == "Hello DataGrowth!"


def test_prepare_extract_builds_json_response_format_for_json_template(resource: MockOpenaiPromptResource) -> None:
    class JsonOutput(BaseModel):
        answer: str

    configure_storage(resource)
    schema = JsonOutput.model_json_schema()
    signature = resource.prepare_extract(
        "json_response.json.tpl",
        output=JsonOutput,
        context={"name": "DataGrowth"},
        options={"n": 1},
    )

    assert isinstance(signature.data, dict)
    assert signature.data["messages"][0]["role"] == "user"
    message = signature.data["messages"][0]["content"]
    assert schema["title"] in message
    assert str(schema) in message
    assert signature.kwargs["context"]["json_schema"] == schema
    assert signature.data["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": schema["title"],
            "schema": schema,
        },
    }


def test_prepare_extract_raises_without_openai_api_key() -> None:
    config = create_config("openai", {"api_key": None})
    resource = MockOpenaiPromptResource(config=config, llm=OPENAI_DEFAULT_TAG)
    configure_storage(resource)

    with pytest.raises(DGHttpNoAuthentication, match="Missing DATAGROWTH_OPENAI_API_KEY setting"):
        resource.prepare_extract("hello_world.tpl", context={"name": "DataGrowth"})


# ==============================
# extract
# ==============================


def test_extract_returns_template_not_found_error_resource(resource: MockOpenaiPromptResource) -> None:
    configure_storage(resource)

    extracted = resource.extract("missing.tpl")

    assert extracted.status == resource.ErrorCodes.TEMPLATE_DOES_NOT_EXIST.value
    assert extracted.result is not None
    assert extracted.result.errors is not None
    assert "missing.tpl" in extracted.result.errors


def test_extract_returns_template_render_error_resource(resource: MockOpenaiPromptResource) -> None:
    configure_storage(resource)
    extracted = resource.extract("broken.tpl", context={"name": "DataGrowth"})

    assert extracted.status == resource.ErrorCodes.TEMPLATE_RENDER_ERROR.value
    assert extracted.result is not None
    assert extracted.result.errors is not None
    assert "broken.tpl" in extracted.result.errors


def test_extract_returns_max_tokens_estimate_exceeded_error_resource() -> None:
    token_limited_tag = Tag(category="llm", value=f"openai/test-max-inputs-{uuid4().hex}")
    token_limited_llm = LLMModel(
        identifier="gpt-4.1-2025-04-14",
        vendor=LLMVendors.OPENAI,
        max_inputs=3,
        max_outputs=32_768,
        options=[("n", int), ("temperature", float), ("top_p", float)],
    )
    DATAGROWTH_REGISTRY.register_llm(token_limited_tag, token_limited_llm)
    try:
        resource = MockOpenaiPromptResource(llm=token_limited_tag)
        configure_storage(resource)
        extracted = resource.extract("long.tpl")

        assert extracted.status == resource.ErrorCodes.MAX_TOKENS_ESTIMATE_EXCEEDED.value
        assert extracted.result is not None
        assert extracted.result.errors is not None
        assert "too many tokens" in extracted.result.errors
    finally:
        DATAGROWTH_REGISTRY.unregister_llm(token_limited_tag)
