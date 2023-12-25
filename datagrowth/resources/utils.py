from typing import List, Dict

from datagrowth.resources.base import Resource


def serialize_resources(resources: List[Resource] = None) -> Dict:
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


def update_serialized_resources(serialization: Dict[str, Dict], resources: List[Resource] = None):
    if not resources:
        return
    resource_info = serialize_resources(resources)
    if (resource := resource_info["resource"]) in serialization:
        serialization[resource]["success"] = serialization[resource]["success"] and resource_info["success"]
        serialization[resource]["ids"] += resource_info["ids"]
        return
    serialization[resource] = resource_info
