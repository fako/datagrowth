from datagrowth.datatypes import DocumentBase


class Document(DocumentBase):

    def apply_resource(self, resource):
        self.reference = resource.status
