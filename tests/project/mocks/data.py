import os
from copy import deepcopy

from datagrowth import settings as datagrowth_settings


MOCK_DATA = {
    "dict": {
        "test": "nested value",
        "list": ["nested value 0", "nested value 1", "nested value 2"],
        "dict": {"test": "test"}
    },
    "list": ["value 0", "value 1", "value 2"],
    "dotted.key": "another value",
    "unicode": ["überhaupt"]
}
MOCK_DATA_WITH_NEXT = deepcopy(MOCK_DATA)
MOCK_DATA_WITH_NEXT["next"] = 1
MOCK_DATA_WITH_RECORDS = deepcopy(MOCK_DATA)
MOCK_DATA_WITH_RECORDS["records"] = [
    {"id": 1, "record": "Hallelujah"},
    {"id": 2, "record": "The Beatles"},
    {"id": 3, "record": "The Stones"},
]
MOCK_DATA_WITH_KEYS = deepcopy(MOCK_DATA)
MOCK_DATA_WITH_KEYS['keys'] = {
    data['id']: deepcopy(data)
    for data in MOCK_DATA_WITH_RECORDS["records"]
}
MOCK_JSON_DATA_CONTEXT = {
    "unicode": "überhaupt",
    "goal": "test"
}
MOCK_JSON_DATA = [
    dict(record, **MOCK_JSON_DATA_CONTEXT) for record in MOCK_DATA_WITH_RECORDS["records"]
]


MOCK_HTML = """
<!doctype html>
<html>

<head>
    <title>Test</title>
</head>

<body>

</body>

<div id="content">
    <p>
        A list with links:
        <ul>
            <li><a href="/test">test</a></li>
            <li><a href="/test2">test 2</a></li>
            <li><a href="/test3">test 3</a></li>
            <li>That's it!</li>
        </ul>
    </p>
</div>

</html>
"""
MOCK_XML = """
<xml>
    <meta>
        <title>Test</title>
    </meta>

    <results>
        <result>
            <label>test</label>
            <url>/test</url>
        </result>
        <result>
            <label>test 2</label>
            <url>/test2</url>
        </result>
        <result>
            <label>test 3</label>
            <url>/test3</url>
        </result>
    </results>

</xml>
"""
MOCK_SCRAPE_DATA = [
    {'text': 'test', 'link': '/test', 'page': 'Test'},
    {'text': u'test 2', 'link': '/test2', 'page': 'Test'},
    {'text': u'test 3', 'link': '/test3', 'page': 'Test'}
]

with open(os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, "image-file.png"), "rb") as img:
    MOCK_FILE_DATA = img.read()
