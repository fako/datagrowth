from collections import defaultdict

from datagrowth.management.base import DatasetCommand
from datagrowth.utils import ibatch


class Command(DatasetCommand):
    """
    Copies a dataset by signature to a new dataset instance
    """

    def handle_dataset(self, dataset, *args, **options):
        # First we prepare all QuerySets and instances that we want to copy
        growths = dataset.growth_set.all()
        kernel_key = (type(dataset.kernel), dataset.kernel.id)
        collections = dataset.collections.all()
        documents = dataset.documents.all()
        # Then we copy the dataset
        dataset.id = None
        dataset.pk = None
        dataset.save()
        # Going over all growths and create initial copies
        growth_by_output = defaultdict(list)
        for growth in growths:
            growth_output_key = (type(growth.output), growth.output_id,)
            growth.id = None
            growth.pk = None
            growth.output = None
            growth.community_id = dataset.id
            growth.save()
            growth_by_output[growth_output_key].append(growth)
        # Going over all collections and creating the copies as well as updating growths
        collections_by_id = {}
        for collection in collections:
            # Store the original id info
            collection_key = (type(collection), collection.id,)
            collections_by_id[collection.id] = collection
            # Clone the collection
            collection.id = None
            collection.pk = None
            collection.community_id = dataset.id
            collection.save()
            # Check for kernel equality and update the dataset
            if collection_key == kernel_key:
                dataset.kernel = collection
                dataset.save()
            # Check for growth output and update the growth
            if collection_key in growth_by_output:
                for growth in growth_by_output[collection_key]:
                    growth.output = collection
                    growth.save()
        # Going over all documents in batches and creating the copies as well as updating growths
        document_model = None
        for batch in ibatch(documents.iterator(), batch_size=100, progress_bar=True, total=documents.count()):
            documents = []
            for document in batch:
                # Setting the correct document model to use later
                if document_model is None:
                    document_model = type(document)
                # Store the original id info
                document_key = (type(document), document.id,)
                # Prepare the document clone
                document.id = None
                document.pk = None
                document.community_id = dataset.id
                document.collection_id = collections_by_id[document.collection_id].id
                # Check for kernel equality and update the dataset
                if document_key == kernel_key:
                    document.save()
                    dataset.output = document
                    dataset.save()
                # Check for growth output and update the growth
                if document_key in growth_by_output:
                    document.save()
                    for growth in growth_by_output[document_key]:
                        growth.kernel = document
                        growth.save()
                else:
                    documents.append(document)
            # Write the cloned batch to the database
            document_model.objects.bulk_create(documents)
