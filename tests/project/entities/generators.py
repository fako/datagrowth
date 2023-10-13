from copy import copy

from datagrowth.utils import ibatch

from project.entities.constants import Entities, SEED_DEFAULTS, SEED_SEQUENCE_PROPERTIES, SEED_CYCLE_PROPERTIES
from datatypes.models import Collection, Document


def seed_generator(entity: Entities, size: int) -> list[dict]:
    for ix in range(0, size):
        seed = copy(SEED_DEFAULTS[entity])
        sequenced = {
            key: value.format(ix=ix) if value != "{ix}" else ix
            for key, value in SEED_SEQUENCE_PROPERTIES.items() if key in seed
        }
        seed.update(sequenced)
        for key, values in SEED_CYCLE_PROPERTIES.items():
            if key not in seed:
                continue
            value = values[ix % len(values)]
            if key == "url":
                value = value.format(ix=ix)
            elif key == "email":
                value = value.format(first_name=seed["first_name"].lower(), last_name=seed["last_name"].lower())
            seed[key] = value
        yield seed


def document_generator(entity: Entities, size: int, batch_size: int, collection: Collection):
    documents = [
        Document.build(seed, collection=collection)
        for seed in seed_generator(entity, size)
    ]
    for batch in ibatch(documents, batch_size=batch_size):
        Document.objects.bulk_create(batch)
        yield batch
