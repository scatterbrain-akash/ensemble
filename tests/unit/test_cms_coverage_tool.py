import httpx
from src.agent.config import Settings
from src.agent.tools.cms_coverage import CMSCoverageTool


class MockResponse:
    def __init__(self, status_code=200, json_data=None, url=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.url = url

    def json(self):
        return self._json

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise httpx.HTTPStatusError("HTTP error", request=None, response=self)


class MockClient:
    def __init__(self, responses: list):
        # responses is a queue of MockResponse objects returned sequentially
        self._responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params or {}, headers or {}))
        if not self._responses:
            return MockResponse(200, {})
        resp = self._responses.pop(0)
        return resp


def make_settings():
    return Settings(env="test")


def test_successful_fetch_returns_evidence():
    settings = make_settings()
    tool = CMSCoverageTool(settings)
    resp = MockResponse(200, {"data": [{"document_id": "cms-ncd-123", "cms_cov_policy": "policy text", "title": "Example"}]})
    tool._client = MockClient([resp])

    out = tool.run({"code": "123", "policy_type": "ncd"})
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["source_id"] == "cms-ncd-123"


def test_empty_data_returns_empty_list():
    settings = make_settings()
    tool = CMSCoverageTool(settings)
    resp = MockResponse(200, {"data": []})
    tool._client = MockClient([resp])

    out = tool.run({"code": "nope", "policy_type": "ncd"})
    assert out == []


def test_retries_on_5xx_then_success():
    settings = make_settings()
    # set retries low for test
    settings.retries["cms_tool"] = 3
    tool = CMSCoverageTool(settings)

    resp1 = MockResponse(500, {})
    resp2 = MockResponse(200, {"data": [{"document_id": "cms-ncd-500", "cms_cov_policy": "ok"}]})
    client = MockClient([resp1, resp2])
    tool._client = client

    out = tool.run({"code": "500", "policy_type": "ncd"})
    assert len(out) == 1
    assert out[0]["source_id"] == "cms-ncd-500"
    # ensure two calls were made (one failed, one succeeded)
    assert len(client.calls) == 2


def test_license_token_flow_and_header_set():
    settings = make_settings()
    tool = CMSCoverageTool(settings)

    # First response is the license token fetch, second is data
    license_resp = MockResponse(200, {"data": [{"token": "fake-token"}]}, url="/v1/metadata/license-agreement")
    data_resp = MockResponse(200, {"data": [{"document_id": "lcd-1", "cms_cov_policy": "policy text"}]}, url="/v1/data/lcd/")
    client = MockClient([license_resp, data_resp])
    tool._client = client

    out = tool.run({"code": "lcd-1", "policy_type": "lcd"})
    assert len(out) == 1
    # second call headers should include Authorization with token
    assert len(client.calls) >= 2
    _, _, headers = client.calls[1]
    assert "Authorization" in headers
    assert "fake-token" in headers["Authorization"]
