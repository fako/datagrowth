from datagrowth.resources import ShellResource


class ShellResourceMock(ShellResource):

    CMD_TEMPLATE = ["grep", "-R", "CMD_FLAGS", "{}", "{}"]
    FLAGS = {
        "context": "--context="
    }
    VARIABLES = {
        "environment": "production"
    }

    DIRECTORY_SETTING = "DATAGROWTH_MEDIA_ROOT"

    SCHEMA = {
        "arguments": {
            "title": "shell mock arguments",
            "type": "array",  # a single alphanumeric element
            "items": [
                {
                    "type": "string"
                },
                {
                    "type": "string"
                }
            ],
            "additionalItems": False,
            "minItems": 2
        },
        "flags": {
            "title": "shell mock keyword arguments",
            "type": "object",
            "properties": {
                "context": {"type": "number"}
            },
            "required": ["context"]
        }
    }

    def run(self, *args, **kwargs):
        if len(args) == 1:
            args += tuple(".")
        return super().run(*args, **kwargs)

    def variables(self, *args):
        vars = super().variables(*args)
        input = vars["input"]
        vars["dir"] = input[1] if len(input) > 1 else None
        return vars
