from django.contrib import admin

from datagrowth.resources.admin import HttpResourceAdmin, ShellResourceAdmin

from resources.models import HttpResourceMock, ShellResourceMock


admin.site.register(HttpResourceMock, HttpResourceAdmin)
admin.site.register(ShellResourceMock, ShellResourceAdmin)
