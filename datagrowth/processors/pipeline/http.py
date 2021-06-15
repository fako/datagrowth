from datagrowth.processors.pipeline.base import PipelineProcessor


class HttpPipelineProcessor(PipelineProcessor):

    def process_batch(self, batch):
        print("processing:", batch)

    def merge_batch(self, batch):
        print("merging:", batch)

    def full_merge(self, queryset):
        print("full merge", queryset.count())
