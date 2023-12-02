from time import sleep

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from datagrowth.configuration import create_config
from datagrowth.resources.http.tasks import send
from datagrowth.resources.shell.tasks import run
from datagrowth.processors import ProcessorFactory
from datagrowth.processors.growth import GrowthProcessor


class ResourceGrowthProcessor(GrowthProcessor):

    resource_type = None

    def __init__(self, config):
        super().__init__(config)
        resource_app_label, resource_model = self.config.retrieve_data["resource"].split(".")
        self.result_type = ContentType.objects.get_by_natural_key(resource_app_label, resource_model)

    def resource_is_empty(self, resource):
        return False

    def dispatch_resource(self, config, *args, **kwargs):
        return [], []

    def filter_documents(self, queryset):
        depends_on = self.config.depends_on
        growth_phase = self.config.growth_phase
        filters = Q(**{f"task_results__{growth_phase}__success": False})
        filters |= Q(**{f"task_results__{growth_phase}__isnull": True})
        if depends_on:
            filters &= Q(**{f"task_results__{depends_on}__success": True})
        return queryset.filter(filters)

    def process_batch(self, batch):

        config = create_config(self.resource_type, self.config.retrieve_data)

        for process_result in batch.processresult_set.all():
            args, kwargs = process_result.document.output(config.args, config.kwargs)
            successes, fails = self.dispatch_resource(config, *args, **kwargs)
            results = successes + fails
            if not len(results):
                continue
            result_id = results.pop(0)
            process_result.result_type = self.result_type
            process_result.result_id = result_id
            process_result.save()
            creates = [
                self.ProcessResult(document=process_result.document, batch=batch, result_id=result_id,
                                   result_type=self.result_type)
                for result_id in results
            ]
            if creates:
                self.ProcessResult.objects.bulk_create(creates)

    def merge_batch(self, batch):
        growth_phase = self.config.growth_phase
        config = create_config("extract_processor", self.config.contribute_data)
        contribution_processor = self.config.extractor
        contribution_field = "derivatives"
        contribution_property = self.config.to_property or growth_phase
        if contribution_property and "/" in contribution_property:
            contribution_field, contribution_property = contribution_property.split("/")
            contribution_property = contribution_property or None

        attempts = 0
        while attempts < 3:

            documents = []
            for process_result in batch.processresult_set.filter(result_id__isnull=False):
                result = process_result.result
                # Write results to the task_results
                process_result.document.task_results[growth_phase] = {
                    "success": result.success,
                    "resource": f"{result._meta.app_label}.{result._meta.model_name}",
                    "id": result.id
                }
                # Possibly "apply" the Resource to the Document to allow custom updates
                if self.config.apply_resource_to:
                    process_result.document.apply_resource(process_result.result)

                documents.append(process_result.document)
                # Write data to the Document
                extract_processor, extract_method = \
                    ProcessorFactory(contribution_processor).build_with_callable(config)
                contributions = list(extract_method(result)) if not self.resource_is_empty(result) else []
                if len(contributions):
                    contribution = contributions.pop(0)
                    field_attribute = getattr(process_result.document, contribution_field)
                    if contribution_property is None:
                        field_attribute.update(contribution)
                    else:
                        field_attribute[contribution_property] = contribution

            # We'll be locking the Documents for update to prevent accidental overwrite of parallel results
            with transaction.atomic():
                try:
                    list(
                        self.Document.objects
                        .filter(id__in=[doc.id for doc in documents])
                        .select_for_update(nowait=True)
                    )
                except transaction.DatabaseError:
                    attempts += 1
                    warning = f"Failed to acquire lock to merge growth batch (attempt={attempts})"
                    # capture_message(warning, level="warning")
                    sleep(5)
                    continue
                fields = ["task_results", contribution_field] + self.config.apply_resource_to
                self.Document.objects.bulk_update(documents, fields)
                break


class HttpGrowthProcessor(ResourceGrowthProcessor):

    resource_type = "http_resource"

    def dispatch_resource(self, config, *args, **kwargs):
        return send(*args, **kwargs, config=config, method=config.method)

    def resource_is_empty(self, resource):
        return resource.status == 204


class ShellGrowthProcessor(ResourceGrowthProcessor):

    resource_type = "shell_resource"

    def dispatch_resource(self, config, *args, **kwargs):
        return run(*args, **kwargs, config=config)

    def resource_is_empty(self, resource):
        return False
