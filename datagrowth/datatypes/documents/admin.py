from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse


class DataStorageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'created_at', 'modified_at']


class DocumentAdmin(DataStorageAdmin):
    search_fields = ["properties"]


class TaskDataStorageAdmin(admin.ModelAdmin):

    list_display = ['__str__', 'task_result_info', 'finished_at', 'pending_at']

    def resource_admin_html(self, resource_label, resource_serialization):
        resource_url_name = resource_serialization["resource"].replace(".", "_").lower()
        resource_change_url = reverse(f"admin:{resource_url_name}_change", args=(resource_serialization["id"],))
        color = "green" if resource_serialization["success"] else "red"
        return format_html(
            '<a style="color:{}; text-decoration: underline" href="{}">{}</a>',
            color, resource_change_url, resource_label
        )

    def task_result_info(self, obj):
        if not obj.tasks:
            return "(no tasks)"
        if not obj.task_results:
            return "(no results)"
        tasks_html = []
        for task_name, task_info in obj.task_results.items():
            if "resource" in task_info:
                task_html = self.resource_admin_html(task_name, task_info)
            else:
                color = "green" if task_info["success"] else "red"
                task_html = format_html('<span style="color:{}">{}</span>', color, task_name)
            tasks_html.append(task_html)
        return format_html(", ".join(tasks_html))


class DatasetVersionAdmin(TaskDataStorageAdmin):

    list_display = (
        '__str__', 'state_info', 'seeding_errors', 'growth_overview', 'task_result_info', 'finished_at', 'pending_at',
    )
    list_per_page = 10

    def state_info(self, obj):
        state_info = "<ul>"
        for attr in ["growth_strategy", "state", "is_current"]:
            state_info += f"<li>{attr}={getattr(obj, attr)}</li>"
        state_info += "</ul>"
        return format_html(state_info)

    def growth_overview(self, obj):
        overview = ""
        for task_name, states in obj.errors["tasks"].items():
            if not states:
                continue
            color = "green"
            if states["fail"]:
                color = "red"
            elif states["skipped"]:
                color = "orange"
            overview += f"<p style='color:{color}'>{task_name}</p><ul>"
            for state, count in states.items():
                overview += f"<li>{state}={count}</li>"
            overview += "</ul>"
        if not overview:
            overview = "-"
        return format_html(overview)

    def seeding_errors(self, obj):
        errors_html = []
        for resource_label, resource_info in obj.errors["seeding"]:
            errors_html.append(self.resource_admin_html(resource_label, resource_info))
        if not errors_html:
            return format_html("-")
        return format_html(", ".join(errors_html))


class CollectionAdmin(TaskDataStorageAdmin):
    pass


class TaskDocumentAdmin(TaskDataStorageAdmin):
    search_fields = ["properties"]
