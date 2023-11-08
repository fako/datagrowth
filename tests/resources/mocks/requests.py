import json
from copy import deepcopy

import requests
from requests.models import Response
from requests.structures import CaseInsensitiveDict

from unittest.mock import Mock, NonCallableMock

from project.mocks.data import MOCK_DATA, MOCK_FILE_DATA


ok_response = NonCallableMock(spec=Response)
ok_response.headers = CaseInsensitiveDict(data={"content-type": "application/json"})
ok_response.content = json.dumps(MOCK_DATA)
ok_response.status_code = 200

next_response = NonCallableMock(spec=Response)
next_response.headers = CaseInsensitiveDict(data={"content-type": "application/json"})
NEXT_MOCK_DATA = deepcopy(MOCK_DATA)
NEXT_MOCK_DATA["list"] = ["value 3", "value 4", "value 5"]
next_response.content = json.dumps(NEXT_MOCK_DATA)
next_response.status_code = 200

agent_response = NonCallableMock(spec=Response)
agent_response.headers = CaseInsensitiveDict(data={
    "content-type": "application/json",
    "user-agent": "Mozilla /5.0 (Compatible MSIE 9.0;Windows NT 6.1;WOW64; Trident/5.0)"
})
agent_response.content = json.dumps(MOCK_DATA)
agent_response.status_code = 200

not_found_response = NonCallableMock(spec=Response)
not_found_response.headers = CaseInsensitiveDict(data={"content-type": "application/json"})
not_found_response.content = json.dumps({"error": "not found"})
not_found_response.status_code = 404

error_response = NonCallableMock(spec=Response)
error_response.headers = CaseInsensitiveDict(data={"content-type": "application/json"})
error_response.content = json.dumps({"error": "internal error"})
error_response.status_code = 500

ok_file_response = NonCallableMock(spec=Response)
ok_file_response.headers = CaseInsensitiveDict(data={"content-type": "image/png"})
ok_file_response.content = MOCK_FILE_DATA
ok_file_response.status_code = 200


def prepare_request(request):
    return requests.Session().prepare_request(request)


def return_response(prepared_request, proxies, verify, timeout, allow_redirects):
    if "404" in prepared_request.url:
        return not_found_response
    elif "500" in prepared_request.url:
        return error_response
    elif "next=1" in prepared_request.url:
        return next_response
    else:
        return ok_response


MockRequests = NonCallableMock(spec=requests)
MockRequestsSend = Mock(side_effect=return_response)
MockRequests.send = MockRequestsSend
MockRequests.prepare_request = Mock(side_effect=prepare_request)

MockRequestsWithAgent = NonCallableMock(spec=requests)
MockRequestsSendWithAgent = Mock(return_value=agent_response)
MockRequestsWithAgent.send = MockRequestsSendWithAgent
MockRequestsWithAgent.prepare_request = Mock(side_effect=prepare_request)

MockFileRequests = NonCallableMock(spec=requests)
MockFileRequestsSend = Mock(return_value=ok_file_response)
MockFileRequests.send = MockFileRequestsSend
MockFileRequests.prepare_request = Mock(side_effect=prepare_request)


def get_erroneous_requests_mock(prepared_exception):
    MockRequests = NonCallableMock(spec=requests)
    MockRequestsSend = Mock(side_effect=prepared_exception)
    MockRequests.send = MockRequestsSend
    MockRequests.prepare_request = Mock(side_effect=prepare_request)
    return MockRequests
