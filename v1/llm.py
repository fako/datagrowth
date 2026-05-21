from enum import Enum
from pydantic import BaseModel, Field


class LLMVendors(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    UNKNOWN = "unknown"


class LLMCosts(BaseModel):
    input_tokens: float = Field(default=0)
    output_tokens: float = Field(default=0)
    cache_tokens: float = Field(default=0)


class LLMModel(BaseModel):
    identifier: str
    vendor: LLMVendors = Field(default=LLMVendors.UNKNOWN)
    max_inputs: int
    max_outputs: int
    costs: LLMCosts = Field(default_factory=lambda: LLMCosts())
    options: list[tuple[str, type]] = Field(default_factory=list)
    token_encoding: str | None = Field(default=None)

    model_config = {
        "frozen": True
    }
