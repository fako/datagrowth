from datagrowth.configuration import create_config
from datagrowth.processors.input import ExtractProcessor


def content_iterator(resource_iterator, objective):
    config = create_config("extract_processor", {
        "objective": objective
    })
    extractor = ExtractProcessor(config=config)
    for resource in resource_iterator:
        for content in extractor.extract_from_resource(resource):
            yield content
