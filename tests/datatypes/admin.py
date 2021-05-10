from django.contrib import admin

from datagrowth.datatypes.documents.admin import DocumentAdmin, DataStorageAdmin

from datatypes.models import Document, Collection


admin.site.register(Document, DocumentAdmin)
admin.site.register(Collection, DataStorageAdmin)
