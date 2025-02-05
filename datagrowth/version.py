import json


VERSION = "0.19.9"


def create_package_json(file_path):
    with open(file_path, "w") as json_file:
        json.dump({"name": "datagrowth", "version": VERSION}, json_file, indent=4)
