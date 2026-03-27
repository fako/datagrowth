from django.contrib import admin


class HttpResourceAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'uri', 'status', 'created_at', 'modified_at']
    search_fields = ['uri', 'head', 'body', 'request']
    list_filter = ['status']
