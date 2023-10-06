from django.apps import apps
from celery import current_app as app, chord
from celery.exceptions import SoftTimeLimitExceeded

from datagrowth.configuration import load_config
from datagrowth.processors.base import Processor
from datagrowth.utils import ibatch, DatabaseConnectionResetTask


def load_pipeline_models(app_label, models):
    Batch = apps.get_model(
        models["batch"] if "." in models["batch"] else f"{app_label}.{models['batch']}"
    )
    Document = apps.get_model(
        models["document"] if "." in models["document"] else f"{app_label}.{models['document']}"
    )
    ProcessResult = apps.get_model(
        models["process_result"] if "." in models["process_result"] else f"{app_label}.{models['process_result']}"
    )
    return Batch, Document, ProcessResult


@app.task(
    name="growth.full_merge",
    base=DatabaseConnectionResetTask,
    soft_time_limit=60*30,
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_kwargs={"max_retries": 3}
)
@load_config()
def full_merge(config, batch_ids, processor_name):
    app_label = config.pipeline_app_label
    models = config.pipeline_models
    Batch, Document, ProcessResult = load_pipeline_models(app_label, models)
    processor = Processor.create_processor(processor_name, config)
    return processor.full_merge(Document.objects.filter(processresult__batch_id__in=batch_ids))


@app.task(
    name="growth.process_and_merge",
    base=DatabaseConnectionResetTask,
    soft_time_limit=60*30,
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_kwargs={"max_retries": 3}
)
@load_config()
def process_and_merge(config, batch_id):
    app_label = config.pipeline_app_label
    models = config.pipeline_models
    Batch, Document, ProcessResult = load_pipeline_models(app_label, models)
    batch = Batch.objects.get(id=batch_id)
    processor = Processor.create_processor(batch.processor, config)
    processor.process_batch(batch)
    processor.merge_batch(batch)
    return batch.id


class PipelineProcessor(Processor):

    Document = None
    Batch = None
    ProcessResult = None

    result_type = None  # ContentType of the model that holds result data for growth

    def filter_documents(self, queryset):
        return queryset

    def process_batch(self, batch):
        pass

    def merge_batch(self, batch):
        pass

    def full_merge(self, queryset):
        self.ProcessResult.objects.filter(document__in=queryset).delete()

    def _dispatch_tasks(self, tasks, finish, asynchronous=True):
        if not tasks:
            return
        if asynchronous:
            return chord(tasks)(finish)
        batch_ids = [task() for task in tasks]
        return finish(batch_ids)

    def __init__(self, config):
        super().__init__(config)
        app_label = self.config.pipeline_app_label
        models = self.config.pipeline_models
        self.Batch, self.Document, self.ProcessResult = load_pipeline_models(app_label, models)

    def __call__(self, queryset):
        # Prepare some values for serialization
        processor = self.__class__.__name__
        config = self.config.to_dict(private=True, protected=True)
        # Allow derived classes to filter the target Documents
        queryset = self.filter_documents(queryset)
        # Only target Documents that have no ProcessResult associated
        queryset = queryset.exclude(processresult__result_type=self.result_type)
        # Create batches of documents with no processing results
        batches = []
        for document_batch in ibatch(queryset, batch_size=self.config.batch_size):
            batch = self.Batch.objects.create(processor=processor)
            results = [
                self.ProcessResult(document=document, batch=batch)
                for document in document_batch
            ]
            self.ProcessResult.objects.bulk_create(results)
            batches.append(batch)
        # Create tasks and dispatch
        tasks = [process_and_merge.s(batch.id, config=config) for batch in batches]
        finish = full_merge.s(processor, config=config)
        return self._dispatch_tasks(tasks, finish, asynchronous=self.config.asynchronous)
