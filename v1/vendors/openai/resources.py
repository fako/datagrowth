from typing import Any, ClassVar

from datagrowth.exceptions import DGHttpNoAuthentication
from datagrowth.llm import LLMModel, LLMVendors
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.prompt.pydantic import PromptResource, PromptInputsValidator


OPENAI_DEFAULT_TAG = Tag(category="llm", value="openai/default")
OPENAI_DEFAULT_MODEL = LLMModel(
    identifier="gpt-4.1-2025-04-14", vendor=LLMVendors.OPENAI,
    max_inputs=1_047_576, max_outputs=32_768,
    options=[("n", int,), ("temperature", float,), ("top_p", float,)],
)
DATAGROWTH_REGISTRY.register_llm(OPENAI_DEFAULT_TAG, OPENAI_DEFAULT_MODEL)


class OpenaiPromptResource(PromptResource):

    URI_TEMPLATE = "https://api.openai.com/v1/chat/completions"
    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="openai")
    DEFAULT_MODEL: ClassVar[Tag | None] = OPENAI_DEFAULT_TAG

    def auth_headers(self) -> dict:
        api_key = self.config.api_key
        if api_key is None:
            raise DGHttpNoAuthentication("Missing DATAGROWTH_OPENAI_API_KEY setting", resource=self)
        return {"Authorization": f"Bearer {api_key}"}

    def data(self, prompt: str | None = None, model: str | None = None, **kwargs: Any) -> dict[str, Any]:
        assert model, "Data method expected to get a model name"
        assert prompt, "Data method expected to get a prompt"
        options = kwargs.get("options", {})
        data = dict(options) if isinstance(options, dict) else {}

        data["model"] = model
        data["messages"] = [{"role": "user", "content": prompt}]

        template = kwargs.get("template")
        if isinstance(template, str) and template.endswith(".json.tpl"):
            context = kwargs.get("context", {})
            schema = context["json_schema"]
            data["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema["title"],
                    "schema": schema,
                },
            }

        return data

    @property
    def success(self) -> bool:
        is_http_success = super().success
        if not is_http_success:
            return False
        _, data = super().content
        choices = data.get("choices", [])
        if not choices:
            return False
        return all(choice.get("finish_reason") == "stop" for choice in choices if isinstance(choice, dict))

    def handle_errors(self) -> None:
        # High-over checks of HTTP errors and wrong types
        super().handle_errors()
        if not super().success:  # failure in http layer, we don't need to handle anything else
            return None
        if self.success:  # all (generated) data ia valid, we don't need to handle anything
            return None
        _, data = super().content
        assert isinstance(data, dict), f"OpenaiPromptResource has unexpected content of type: {type(data)}"

        # Read response and set errors based on first error dict
        choices = data.get("choices", [])
        error = next(
            (choice for choice in choices if isinstance(choice, dict) and choice.get("finish_reason") != "stop")
        )
        error_message = None
        error_code = None
        if error.get("finish_reason") == "length":
            error_code = self.ErrorCodes.MAX_TOKENS_EXCEEDED.value
            error_message = "OpenAI response exceeded maximum output tokens."
        if error.get("finish_reason") == "content_filter":
            error_code = self.ErrorCodes.CONTENT_FILTER.value
            error_message = "OpenAI response was blocked by content filtering."
        if error_code is not None and error_message is not None:
            self.update(self._error_resource(self.llm, self.signature, error_code, error_message))
        return None

    @property
    def content(self) -> tuple[str | None, Any]:
        # Do not try to render content when something went wrong
        if not self.success or not self.signature:
            return None, None
        content_type, data = super().content
        assert isinstance(data, dict), f"OpenaiPromptResource has unexpected content of type: {type(data)}"

        # Get all generated messages as strings
        choices = data.get("choices", [])
        if not isinstance(choices, list):
            return content_type, data
        messages = [
            choice["message"]["content"]
            for choice in choices
            if isinstance(choice, dict)
            and choice.get("finish_reason") == "stop"
            and isinstance(choice.get("message"), dict)
            and isinstance(choice["message"].get("content"), str)
        ]

        # Parse and return messages
        assert issubclass(self.INPUTS_VALIDATOR, PromptInputsValidator), \
            f"PromptResource needs PromptInputsValidator as INPUTS_VALIDATOR, but found '{self.INPUTS_VALIDATOR}'"
        llm = self._get_llm_definition()
        inputs = self.INPUTS_VALIDATOR.from_llm(llm, *self.signature.args, **self.signature.kwargs)
        if inputs.output:
            content_type = "application/json"
            messages = [inputs.output.model_validate_json(message) for message in messages]
        else:
            content_type = "text/plain"
        return (content_type, messages[0]) if len(messages) == 1 else (content_type, messages)

    ########################
    # Prompt helpers
    ########################

    def get_token_usage(self) -> dict[str, int]:
        if not self.success:
            raise RuntimeError("Can't calculate token usage for failed Resource")
        _, data = super().content
        assert isinstance(data, dict), f"OpenaiPromptResource has unexpected content of type: {type(data)}"
        usage = data["usage"]
        return {
            "prompt": usage["prompt_tokens"],
            "completion": usage["completion_tokens"],
            "reasoning": usage["completion_tokens_details"]["reasoning_tokens"],
            "total": usage["total_tokens"],
        }
