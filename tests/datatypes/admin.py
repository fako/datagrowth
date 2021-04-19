from django.contrib import admin

from datagrowth.datatypes.documents.admin import DocumentAdmin

from datatypes.models import Document


admin.site.register(Document, DocumentAdmin)
