from typing import Any

from datagrowth.resources.base import Resource


def serialize_resources(resources: list[Resource] | None = None) -> dict[str, Any]:
    if not resources:
        return {
            "success": False,
            "resource": None,
            "id": None,
            "ids": []
        }
    resources = resources if isinstance(resources, list) else [resources]
    resource = resources[0]
    return {
        "success": all([rsc.success for rsc in resources]),
        "resource": "{}.{}".format(resource._meta.app_label, resource._meta.model_name),
        "id": resource.id,
        "ids": [rsc.id for rsc in resources]
    }


def update_serialized_resources(serialization: dict[str, dict[str, Any]],
                                resources: list[Resource] | None = None) -> None:
    if not resources:
        return
    resource_info = serialize_resources(resources)
    if (resource := resource_info["resource"]) in serialization:
        serialization[resource]["success"] = serialization[resource]["success"] and resource_info["success"]
        serialization[resource]["ids"] += resource_info["ids"]
        return
    serialization[resource] = resource_info
