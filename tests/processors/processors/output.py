from datagrowth.configuration import ConfigurationProperty
from datagrowth.processors import Processor


class MockProcessor(Processor):

    config = ConfigurationProperty(namespace="mock_processor")


class MockNumberProcessor(MockProcessor):

    def number_documents(self, documents):
        def number_individual(individual, number):
            individual["number"] = number
            return individual
        return (number_individual(individual, idx+1) for idx, individual in enumerate(documents))


class MockFilterProcessor(MockProcessor):

    def filter_documents(self, documents):
        for document in documents:
            if self.config.include_odd and document.get("number") % 2:
                yield document
            elif self.config.include_even and not document.get("number") % 2:
                yield document
            elif self.config.include_odd and self.config.include_even:
                yield document
