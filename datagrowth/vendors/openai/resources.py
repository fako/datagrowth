from typing import Any, ClassVar

from pydantic import BaseModel

from datagrowth.exceptions import DGHttpNoAuthentication
from datagrowth.llm import LLMModel, LLMVendors
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.prompt.pydantic import PromptResource


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
    DEFAULT_MODEL: Tag | None = OPENAI_DEFAULT_TAG

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
