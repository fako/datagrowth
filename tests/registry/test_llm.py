import pytest

from datagrowth.llm import LLMModel, LLMVendors
from datagrowth.registry import Registry, Tag


@pytest.fixture
def registry() -> Registry:
    return Registry()


def get_test_llm() -> LLMModel:
    return LLMModel(
        identifier="gpt-test",
        vendor=LLMVendors.OPENAI,
        max_inputs=10_000,
        max_outputs=1_000,
    )


def test_register_llm_with_string_tag(registry: Registry) -> None:
    llm = get_test_llm()
    tag = registry.register_llm("llm:test", llm)
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("llm:test")
    assert "llm:test" in registry.tags
    assert tag in registry.llms
    assert registry.llms[tag] == llm


def test_register_llm_with_tag_object(registry: Registry) -> None:
    llm = get_test_llm()
    tag_input = Tag(category="llm", value="test")
    tag = registry.register_llm(tag_input, llm)
    assert tag == tag_input
    assert "llm:test" in registry.tags
    assert tag in registry.llms


def test_unregister_llm_with_string_tag(registry: Registry) -> None:
    tag = registry.register_llm("llm:test", get_test_llm())
    registry.unregister_llm("llm:test")
    assert tag not in registry.llms


def test_unregister_llm_with_tag_object(registry: Registry) -> None:
    tag = registry.register_llm("llm:test", get_test_llm())
    registry.unregister_llm(tag)
    assert tag not in registry.llms


def test_get_llm_returns_model(registry: Registry) -> None:
    llm = get_test_llm()
    registry.register_llm("llm:test", llm)
    loaded = registry.get_llm("llm:test")
    assert loaded == llm


def test_get_llm_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="llm", value="test")
    llm = get_test_llm()
    registry.register_llm(tag, llm)
    loaded = registry.get_llm(tag)
    assert loaded == llm


def test_llm_methods_raise_for_wrong_category(registry: Registry) -> None:
    llm = get_test_llm()
    expected = "Expected a tag with 'llm' category but found 'wrong'"
    with pytest.raises(ValueError, match=expected):
        registry.register_llm("wrong:test", llm)
    with pytest.raises(ValueError, match=expected):
        registry.unregister_llm("wrong:test")
    with pytest.raises(ValueError, match=expected):
        registry.get_llm("wrong:test")
