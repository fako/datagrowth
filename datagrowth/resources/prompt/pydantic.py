from typing import ClassVar, Type, Any, Self
from enum import Enum
from pydantic import BaseModel, Field, ValidationInfo, model_validator, field_validator

from datagrowth.exceptions import DGPromptMaxTokensExceeded, DGTemplateNotFound, DGTemplateRenderError
from datagrowth.llm import LLMModel
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.signatures import InputsValidator, DataMode
from datagrowth.resources.pydantic import Result
from datagrowth.resources.http.pydantic import HttpResource, HttpInputsValidator
from datagrowth.resources.http.signature import HttpSignature, HttpMethod, HttpAuth


class PromptErrorCodes(Enum):
    TEMPLATE_DOES_NOT_EXIST = 1
    TEMPLATE_RENDER_ERROR = 2
    MAX_TOKENS_ESTIMATE_EXCEEDED = 3
    MAX_TOKENS_EXCEEDED = 5
    CONTENT_FILTER = 6
    CONTENT_VALIDATION_ERROR = 7


class PromptInputsValidator(HttpInputsValidator):

    POSITIONAL_NAMES = ("template", "output",)

    method: HttpMethod | None = Field(default=HttpMethod.POST)
    template: str
    output: Type[BaseModel] | None = Field(default=None)
    context: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, str | int | float] = Field(default_factory=dict)

    @classmethod
    def from_llm(cls, llm: LLMModel, *args, **kwargs) -> Self:
        values = {name: args[index] for index, name in enumerate(cls.POSITIONAL_NAMES) if index < len(args)}
        values.update(kwargs)
        values["args"] = tuple(args)
        values["kwargs"] = dict(kwargs)
        return cls.model_validate(values, context={"from_inputs": True, "llm": llm})

    #####################
    # Pydantic plumbing
    #####################

    @field_validator("template")
    @classmethod
    def validate_template_name(cls, template_name: str) -> str:
        if not template_name.endswith(".tpl"):
            raise ValueError("PromptResource expected template name to have the .tpl or json.tpl extension")
        return template_name

    @field_validator("method")
    @classmethod
    def validate_method(cls, method: HttpMethod | None) -> HttpMethod:
        if method is None:
            return HttpMethod.POST
        if method != HttpMethod.POST:
            raise ValueError("PromptResource only supports POST method")
        return method

    @field_validator("options")
    @classmethod
    def validate_options(
            cls, options: dict[str, str | int | float], info: ValidationInfo) -> dict[str, str | int | float]:
        context = info.context if isinstance(info.context, dict) else {}
        llm = context.get("llm")
        if not isinstance(llm, LLMModel):
            return options

        allowed = dict(llm.options)
        for option, value in options.items():
            expected_type = allowed.get(option)
            if expected_type is None:
                expected = ", ".join(allowed.keys()) if allowed else "none"
                raise ValueError(
                    f"PromptResource received unsupported option '{option}' for llm '{llm.identifier}'. "
                    f"Allowed options are: {expected}"
                )
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"PromptResource option '{option}' for llm '{llm.identifier}' expected type "
                    f"'{expected_type.__name__}' but got '{type(value).__name__}'"
                )
        return options

    @model_validator(mode="after")
    def validate_output_with_template(self) -> Self:
        template = self.template
        output = self.output
        if isinstance(template, str) and template.endswith(".json.tpl"):
            if output is None:
                raise ValueError("PromptResource requires output to be set when using a .json.tpl template")
            self.context["json_schema"] = output.model_json_schema()
            if "context" in self.kwargs:
                self.kwargs["context"] = self.context
        return self


class PromptResource(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="prompt_resource")
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = PromptInputsValidator
    MODE = DataMode.JSON

    # Prompt specific control attributes
    ErrorCodes: ClassVar[type[PromptErrorCodes]] = PromptErrorCodes
    DEFAULT_MODEL: Tag | None = Field(default=None)
    # Prompt specific data attributes
    llm: Tag

    ########################
    # Prompt implementation
    ########################

    def prepare_prompt(self, inputs: PromptInputsValidator) -> str:
        assert self.storage, "Expected PromptResource to declare a Storage"
        llm = self._get_llm_definition()
        prompt = self.storage.render_template(inputs.template, inputs.context)
        if len(prompt) / 4 > llm.max_inputs:
            raise DGPromptMaxTokensExceeded("Prompt is estimated to contain too many tokens.", resource=self)
        return prompt

    def prepare_inputs(self, inputs: InputsValidator, prompt: str | None = None) -> HttpSignature:
        positional_count = min(len(PromptInputsValidator.POSITIONAL_NAMES), len(inputs.POSITIONAL_NAMES))
        url_arguments = inputs.args[positional_count:] if len(inputs.args) > positional_count else tuple()
        url, data_arguments = self._create_url(*url_arguments, **inputs.kwargs)
        auth = HttpAuth(headers=self.auth_headers(), parameters=self.auth_parameters())
        llm = self._get_llm_definition()
        return HttpSignature(
            uri=self.uri_from_url(url),
            args=inputs.args,
            kwargs=inputs.kwargs,
            data=self.data(
                prompt=prompt, model=llm.identifier, template=inputs.get_argument("template"),
                **data_arguments
            ),
            type=self.type.value,
            method=HttpMethod.POST,
            url=url,
            headers=self.headers(*inputs.args, **inputs.kwargs),
            auth=auth if auth.headers or auth.parameters else None,
            mode=DataMode.JSON,
        )

    def prepare_extract(self, *args: Any, **kwargs: Any) -> HttpSignature:
        assert issubclass(self.INPUTS_VALIDATOR, PromptInputsValidator), \
            f"PromptResource needs PromptInputsValidator as INPUTS_VALIDATOR, but found '{self.INPUTS_VALIDATOR}'"
        llm = self._get_llm_definition()
        inputs = self.INPUTS_VALIDATOR.from_llm(llm, *args, **kwargs)
        prompt = self.prepare_prompt(inputs)
        return self.prepare_inputs(inputs, prompt)

    ########################
    # Error handling
    ########################

    @classmethod
    def _error_resource(cls, llm: Tag, signature: HttpSignature | None, status: int, message: str) -> Self:
        return cls(
            llm=llm,
            signature=signature,
            status=status,
            result=Result(
                content_type="unknown/unknown",
                head={},
                body="",
                errors=message,
            ),
        )

    def extract(self, *args: Any, **kwargs: Any) -> Self:
        # Validate the inputs to arrive at a Signature used for extraction
        # Create early error Results when validation fails
        signature = None or self.signature
        if self.signature is None or args or kwargs:
            try:
                signature = self.prepare_extract(*args, **kwargs)
            except DGTemplateNotFound as error:
                error_code = self.ErrorCodes.TEMPLATE_DOES_NOT_EXIST.value
                return self._error_resource(self.llm, signature, error_code, str(error))
            except DGTemplateRenderError as error:
                error_code = self.ErrorCodes.TEMPLATE_RENDER_ERROR.value
                return self._error_resource(self.llm, signature, error_code, str(error))
            except DGPromptMaxTokensExceeded as error:
                error_code = self.ErrorCodes.MAX_TOKENS_ESTIMATE_EXCEEDED.value
                return self._error_resource(self.llm, signature, error_code, str(error))
        self.signature = signature
        return super().extract()

    #####################
    # Pydantic plumbing
    #####################

    def _get_llm_definition(self) -> LLMModel:
        return DATAGROWTH_REGISTRY.get_llm(self.llm)

    @field_validator("llm", mode="before")
    @classmethod
    def set_llm_or_default(cls, value, info) -> Tag:
        if value is not None:
            return value
        if cls.DEFAULT_MODEL is not None:
            return cls.DEFAULT_MODEL
        raise ValueError("llm must be set or DEFAULT_MODEL must be provided")
