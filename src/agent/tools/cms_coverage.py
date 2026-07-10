from __future__ import annotations

import json
import time
import random
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
        # Retry/backoff configuration
        max_attempts = int(self.settings.retries.get("cms_tool", 3))
        backoff_base = float(self.settings.cms.get("retry_backoff_seconds", 0.5))
        max_backoff = float(self.settings.cms.get("max_backoff_seconds", 10.0))

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.get(url, params={param_name: code}, headers=headers)

                # Handle unauthorized: try refresh once
                if response.status_code == 401 and policy_type != "ncd":
                    self._reset_license_token()
                    headers["Authorization"] = f"Bearer {self._get_license_token()}"
                    response = self._client.get(url, params={param_name: code}, headers=headers)

                # Raise for 4xx/5xx to be handled accordingly
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = getattr(exc.response, "status_code", None)
                last_exc = exc
                # Retry on 5xx server errors or transient network issues
                if status is not None and 500 <= status < 600 and attempt < max_attempts:
                    backoff = min(max_backoff, backoff_base * (2 ** (attempt - 1)))
                    jitter = backoff * (0.5 * random.random())
                    time.sleep(backoff + jitter)
                    continue
                # For other HTTP errors, do not retry
                raise
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < max_attempts:
                    backoff = min(max_backoff, backoff_base * (2 ** (attempt - 1)))
                    jitter = backoff * (0.5 * random.random())
                    time.sleep(backoff + jitter)
                    continue
                raise

        # Exhausted retries
        if last_exc:
            raise last_exc
        return {}

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
        candidates = []
        if isinstance(response, dict):
            # Prefer a populated `data` array
            data_arr = response.get("data")
            if isinstance(data_arr, list) and len(data_arr) > 0:
                candidates = data_arr
            else:
                results_arr = response.get("results")
                if isinstance(results_arr, list) and len(results_arr) > 0:
                    candidates = results_arr
                else:
                    # If the top-level response looks like a single document, use it
                    if any(k in response for k in ("document_id", "lcd_id", "article_id", "id")):
                        candidates = [response]
                    else:
                        candidates = []
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
