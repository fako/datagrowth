from datagrowth.configuration import ConfigurationProperty
from datagrowth.processors import Processor


class MockProcessor(Processor):

    config = ConfigurationProperty(namespace="mock_processor")


class MockNumberProcessor(MockProcessor):

    def number_individuals(self, individuals):
        def number_individual(individual, number):
            individual["number"] = number
            return individual
        return (number_individual(individual, idx+1) for idx, individual in enumerate(individuals))


class MockFilterProcessor(MockProcessor):

    def filter_individuals(self, individuals):
        for individual in individuals:
            if self.config.include_odd and individual.get("number") % 2:
                yield individual
            elif self.config.include_even and not individual.get("number") % 2:
                yield individual
            elif self.config.include_odd and self.config.include_even:
                yield individual
