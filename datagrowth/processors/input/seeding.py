from typing import Iterator, List, Dict, Union
from copy import deepcopy
from collections import OrderedDict

from datagrowth.datatypes import CollectionBase
from datagrowth.configuration import create_config, ConfigurationType
from datagrowth.resources.http.iterators import send_serie_iterator
from datagrowth.processors import Processor
from datagrowth.processors.input.iterators import content_iterator
from datagrowth.utils import ibatch


class ResourceSeedingProcessor(Processor):

    Document = None

    resource_type = None
    contribute_type = "extract_processor"

    initial = None
    contents = {}
    buffer = []
    batch = []

    def should_skip_phase(self, phase):
        if not self.contents:
            return False
        highest_content_phase = max(self.contents.keys())
        return phase["phase"].index < highest_content_phase

    def build_seed_iterator(self, phase, *args, **kwargs) -> Iterator:
        resource_config = phase["retrieve"]
        if not len(self.batch):
            # This is the initial case where there is no input from a buffer.
            # So we just use args and kwargs as given to the call to the processor.
            args_list = [args]
            kwargs_list = [kwargs]
        else:
            # Here we have input from the batch as well as args and kwargs from the call to the processor.
            # Together these inputs need to be given to the Resource as configured by retrieve_data.
            # First we interpret the args and kwargs given to the retrieve_data configuration,
            # using the args and kwargs from call to the processor, but only for keys starting with "#".
            args, kwargs = self.Document.output_from_content(
                {
                    "args": args,
                    "kwargs": kwargs
                },
                resource_config.args, resource_config.kwargs,
                replacement_character="#"
            )
            # Then we use the interpreted args and kwargs from retrieve_data to built args and kwargs,
            # that can be given to the Resource, for all content in the batch.
            # Here we replace args and kwargs values coming through the processor call,
            # for data coming from the batch if a value starts with "$".
            args_list = []
            kwargs_list = []
            for content in self.batch:
                content_args, content_kwargs = self.Document.output_from_content(content, args, kwargs)
                args_list.append(content_args)
                kwargs_list.append(content_kwargs)

        # Sending the parsed args and kwargs, possibly with batch data to the Resource
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method=resource_config.method,
            config=resource_config
        )
        seed_iterator = content_iterator(resource_iterator, phase["contribute"].objective)
        batch_size = phase["phase"].batch_size
        return ibatch(seed_iterator, batch_size=batch_size)

    def build_callback_iterator(self, phase, *args) -> Iterator:
        callback = phase["contribute"].callback
        for seed in self.batch:
            yield callback(seed, *args)

    def flush_buffer(self, phase, force=False) -> None:
        if not self.buffer and not force:
            raise ValueError(f"Did not expect to encounter an empty buffer with strategy for phase {phase['phase']}")

        strategy = phase["phase"].strategy

        if strategy in ["initial", "replace", "back_fill"]:
            self.batch = deepcopy(self.buffer)
        elif strategy == "merge":
            merge_on = phase["contribute"].merge_on
            buffer = {
                content[merge_on]: content
                for content in self.buffer
            }
            for content in self.batch:
                content.update(buffer.get(content[merge_on], {}))

        self.buffer = []

    def batch_to_documents(self) -> Iterator:
        documents = [
            self.Document.build(seed, collection=self.collection)
            for seed in self.batch
        ]
        return self.collection.update_batches(documents, self.collection.identifier)

    def __init__(self, collection: CollectionBase, config: Union[ConfigurationType, Dict],
                 initial: List[Dict] = None) -> None:
        super().__init__(config)
        assert len(self.config.phases), \
            "ResourceSeedingProcessor needs at least one phase configured to be able to retrieve seed data"
        assert collection.identifier, (
            "ResourceSeedingProcessor expects a Collection with the identifier set to a Document property "
            "that has a unique value across Documents in the Collection."
        )
        self.collection = collection
        self.Document = collection.get_document_model()
        self.resources = {}
        self.buffer = None  # NB: "None" ensures the forever while loop runs at least once
        self.batch = initial or []
        self.contents = {}
        if not initial:
            phases_selection = self.config.phases
        else:
            phases_selection = [phase for phase in self.config.phases if phase.get("is_post_initialization", False)]
        self.phases = OrderedDict()
        for ix, phase in enumerate(phases_selection):
            phase = deepcopy(phase)
            phase["index"] = ix
            retrieve_data = phase.pop("retrieve_data", None)
            contribute_data = phase.pop("contribute_data")
            phase_config = create_config("seeding_processor", phase)
            retrieve_config = create_config(self.resource_type, retrieve_data) if retrieve_data else None
            contribute_config = create_config(self.contribute_type, contribute_data)
            self.phases[phase_config.phase] = {
                "phase": phase_config,
                "retrieve": retrieve_config,
                "contribute": contribute_config
            }

    def __call__(self, *args, **kwargs) -> Iterator:
        while self.contents or self.buffer is None:
            self.buffer = self.batch  # prevents forever loop when initial seeds are set for webhooks
            for phase_index, phase in enumerate(self.phases.values()):
                if self.should_skip_phase(phase):
                    continue
                strategy = phase["phase"].strategy
                if strategy in ["initial", "replace"]:
                    if phase_index not in self.contents:
                        self.contents[phase_index] = self.build_seed_iterator(phase, *args, **kwargs)
                    try:
                        self.buffer = next(self.contents[phase_index])
                    except StopIteration:
                        # The contents iterator is exhausted.
                        # We'll flush the currently empty buffer
                        self.flush_buffer(phase, force=True)
                        # We remove the iterator from memory
                        del self.contents[phase_index]
                        # And retry phases before this phase (if any)
                        break
                elif strategy == "merge":
                    self.buffer = [
                        content
                        for batch in self.build_seed_iterator(phase, *args, **kwargs)
                        for content in batch
                    ]
                elif strategy == "back_fill":
                    self.buffer = [
                        content
                        for batch in self.build_callback_iterator(phase, self.collection)
                        for content in batch
                    ]
                self.flush_buffer(phase)
            if not self.batch:
                return
            for batch in self.batch_to_documents():
                yield batch


class HttpSeedingProcessor(ResourceSeedingProcessor):
    resource_type = "http_resource"
