from django.contrib import admin


class DatasetAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'created_at', 'modified_at']
