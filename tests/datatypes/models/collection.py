from datagrowth.datatypes import CollectionBase


class Collection(CollectionBase):

    @property
    def documents(self):
        return self.document_set
