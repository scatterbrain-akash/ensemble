from __future__ import annotations

import json
import time
from typing import Any

import httpx

from src.agent.config import Settings
from src.agent.tools.base import BaseTool


class CMSCoverageTool(BaseTool):
    name = "cms_coverage"
    description = "Retrieve CMS coverage policy evidence for CMS coverage policy queries."
    BASE_URL = "https://api.coverage.cms.gov"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._license_token: str | None = None
        self._token_obtained_at: float | None = None
        self._token_ttl_seconds = int(self.settings.cms.get("license_token_ttl_seconds", 3600))
        self._client = httpx.Client(timeout=self.settings.timeouts.get("tool_call_seconds", 20))

    def run(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        code = query.get("code")
        if not code:
            return []

        policy_type = str(query.get("policy_type", "ncd")).lower()
        try:
            response = self._fetch_policy(code=str(code), policy_type=policy_type)
        except httpx.HTTPError:
            return []

        return self._parse_policy_response(response, query, policy_type)

    def _fetch_policy(self, code: str, policy_type: str) -> Any:
        headers: dict[str, str] = {"Accept": "application/json"}
        # Map to the documented data endpoints and parameter names
        param_name_map = {
            "ncd": "ncdid",
            "lcd": "lcdid",
            "article": "articleid",
        }

        endpoint = f"/v1/data/{policy_type}/"
        url = f"{self.BASE_URL}{endpoint}"

        # LCD and Article endpoints require license-agreement token
        if policy_type in ("lcd", "article"):
            headers["Authorization"] = f"Bearer {self._get_license_token()}"

        param_name = param_name_map.get(policy_type, "code")
        response = self._client.get(url, params={param_name: code}, headers=headers)
        if response.status_code == 401 and policy_type != "ncd":
            self._reset_license_token()
            headers["Authorization"] = f"Bearer {self._get_license_token()}"
            response = self._client.get(url, params={param_name: code}, headers=headers)

        response.raise_for_status()
        return response.json()

    def _reset_license_token(self) -> None:
        self._license_token = None
        self._token_obtained_at = None

    def _token_expired(self) -> bool:
        if self._token_obtained_at is None:
            return True
        return time.time() - self._token_obtained_at >= self._token_ttl_seconds

    def _get_license_token(self) -> str:
        if self._license_token and not self._token_expired():
            return self._license_token

        url = f"{self.BASE_URL}/v1/metadata/license-agreement"
        response = self._client.get(url)
        response.raise_for_status()
        data = response.json()
        # API returns a `data` array with a MetadataLicenseAgreement object
        token = None
        if isinstance(data, dict):
            # check top-level common fields
            token = (
                data.get("token")
                or data.get("access_token")
                or data.get("bearer_token")
                or data.get("license_token")
            )
            # check data array
            arr = data.get("data") if isinstance(data.get("data"), list) else None
            if not token and arr:
                for entry in arr:
                    if isinstance(entry, dict) and entry.get("token"):
                        token = entry.get("token")
                        break
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get("token"):
                    token = entry.get("token")
                    break

        if not token:
            raise httpx.HTTPError("CMS license agreement token not found")

        self._license_token = token
        self._token_obtained_at = time.time()
        return token

    def _parse_policy_response(self, response: Any, query: dict[str, Any], policy_type: str) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            candidates = response.get("data") or response.get("results") or [response]
        elif isinstance(response, list):
            candidates = response
        else:
            candidates = []

        evidence: list[dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            # Prefer documented identifiers
            source_id = (
                item.get("document_id")
                or item.get("lcd_id")
                or item.get("article_id")
                or item.get("id")
                or item.get("source_id")
                or f"cms-{policy_type}-{query.get('code')}"
            )

            title = (
                item.get("title")
                or item.get("document_display_id")
                or item.get("name")
                or f"CMS {policy_type.upper()} evidence for {query.get('code')}"
            )

            # Fields that commonly contain the policy text
            excerpt = (
                item.get("cms_cov_policy")
                or item.get("doc_text")
                or item.get("excerpt")
                or item.get("summary")
                or item.get("description")
                or json.dumps(item)
            )

            url = item.get("url") or item.get("link") or item.get("transmittal_url") or ""
            relevance = "direct" if str(query.get("code")) in str(excerpt) else "weak"

            evidence.append(
                {
                    "source_id": str(source_id),
                    "source_type": policy_type,
                    "title": str(title),
                    "excerpt": str(excerpt),
                    "relevance": relevance,
                    "retrieval_query": query,
                    "url": str(url),
                }
            )

        return evidence
