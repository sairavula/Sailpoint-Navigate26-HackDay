"""
Shared SailPoint ISC client for the Navigate Hack Day MCP server.

Cross-platform: keyring reads macOS Keychain or Windows Credential Manager.
Service: sailpoint-isc-hackday, accounts: client_id, client_secret.
"""

import asyncio
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
import keyring

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

BASE_URL = os.getenv("HACKDAY_BASE_URL", "https://devrel-ga-25087.api.identitynow-demo.com")
KEYCHAIN_SERVICE = os.getenv("HACKDAY_KEYCHAIN_SERVICE", "sailpoint-isc-hackday")
PAGE_SIZE = 250
MAX_RETRIES = 3
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
EXPERIMENTAL = {"X-SailPoint-Experimental": "true"}

# Lifecycle states treated as "not accountable"
INACTIVE_LIFECYCLE_STATES = {"inactive", "terminated", "leave", "disabled", "offboarded"}

LOG_DIR = Path.home() / ".sailpoint-hackday-mcp"
LOG_DIR.mkdir(exist_ok=True, mode=0o700)

_REDACT = re.compile(r"(client_secret|access_token|api_key|bearer)\s*[=:]?\s*\S+", re.IGNORECASE)


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _REDACT.sub(r"\1=[REDACTED]", str(record.msg))
        return True


logger = logging.getLogger("sailpoint_hackday")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.FileHandler(LOG_DIR / "server.log")
    _handler.setFormatter(logging.Formatter("time=%(asctime)s level=%(levelname)s %(message)s"))
    _handler.addFilter(_RedactFilter())
    logger.addHandler(_handler)
logging.getLogger("httpx").setLevel(logging.WARNING)


class ISCError(Exception):
    """Safe, user-facing error (no internal state)."""


class ISCClient:
    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expiry = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _credentials() -> tuple[str, str]:
        client_id = keyring.get_password(KEYCHAIN_SERVICE, "client_id")
        client_secret = keyring.get_password(KEYCHAIN_SERVICE, "client_secret")
        if not client_id or not client_secret:
            raise ISCError(
                f"Missing OS credential-store entries for service '{KEYCHAIN_SERVICE}' "
                "(accounts: client_id, client_secret). macOS: security add-generic-password; "
                "Windows: python store_credentials.py"
            )
        return client_id.strip(), client_secret.strip()

    async def get_token(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            if self._token and time.time() < self._token_expiry - 60:
                return self._token
            client_id, client_secret = self._credentials()
            resp = await client.post(
                f"{BASE_URL}/oauth/token",
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            )
            if resp.status_code != 200:
                logger.error(f"event=token_failed status={resp.status_code}")
                raise ISCError(f"Token request failed (HTTP {resp.status_code}). Check the PAT in the credential store.")
            body = resp.json()
            self._token = body["access_token"]
            self._token_expiry = time.time() + int(body.get("expires_in", 600))
            logger.info("event=token_acquired")
            return self._token

    async def request(
        self, method: str, path: str, headers: Optional[dict] = None, **kwargs: Any
    ) -> httpx.Response:
        cid = uuid.uuid4().hex[:8]
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                start = time.perf_counter()
                try:
                    token = await self.get_token(client)
                    resp = await client.request(
                        method,
                        f"{BASE_URL}{path}",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", **(headers or {})},
                        **kwargs,
                    )
                except httpx.HTTPError as exc:
                    logger.warning(f"event=http_error cid={cid} path={path} attempt={attempt} error={type(exc).__name__}")
                    if attempt == MAX_RETRIES:
                        raise ISCError(f"Network error calling ISC ({type(exc).__name__}).") from exc
                    await asyncio.sleep(2 ** attempt)
                    continue

                ms = int((time.perf_counter() - start) * 1000)
                logger.info(f"event=api_call cid={cid} method={method} path={path} status={resp.status_code} ms={ms}")

                if resp.status_code == 401 and attempt < MAX_RETRIES:
                    self._token = None
                    continue
                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt == MAX_RETRIES:
                        break
                    await asyncio.sleep(float(resp.headers.get("Retry-After", 2 ** attempt)))
                    continue
                if resp.status_code >= 400:
                    raise ISCError(f"ISC returned HTTP {resp.status_code} for {path}.")
                return resp
        raise ISCError(f"ISC request to {path} failed after {MAX_RETRIES} attempts.")

    async def list_all(self, path: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> list[dict]:
        """Offset-paginate a list endpoint."""
        items: list[dict] = []
        offset = 0
        while True:
            page_params = {**(params or {}), "limit": PAGE_SIZE, "offset": offset}
            page = (await self.request("GET", path, headers=headers, params=page_params)).json()
            items.extend(page)
            if len(page) < PAGE_SIZE:
                return items
            offset += PAGE_SIZE

    async def search(self, index: str, query: str, limit: int = 250) -> list[dict]:
        body = {"indices": [index], "query": {"query": query}}
        resp = await self.request("POST", "/v3/search", params={"limit": min(limit, 250)}, json=body)
        return resp.json()

    async def search_all(self, index: str, query: str) -> list[dict]:
        """Paginated search across every matching document."""
        out: list[dict] = []
        offset = 0
        while True:
            resp = await self.request(
                "POST", "/v3/search", params={"limit": PAGE_SIZE, "offset": offset},
                json={"indices": [index], "query": {"query": query}, "sort": ["id"]},
            )
            page = resp.json()
            out.extend(page)
            if len(page) < PAGE_SIZE:
                return out
            offset += PAGE_SIZE

    async def identity_by_name(self, name: str) -> Optional[dict]:
        """Exact name match first, then free-text fallback."""
        docs = await self.search("identities", f'name:"{name}"', limit=1)
        if not docs:
            docs = await self.search("identities", name, limit=1)
        return docs[0] if docs else None


def lifecycle_state(doc: Optional[dict]) -> Optional[str]:
    return ((doc or {}).get("attributes") or {}).get("cloudLifecycleState")


def is_inactive(doc: Optional[dict]) -> bool:
    return bool(doc) and (bool(doc.get("inactive")) or (lifecycle_state(doc) or "").lower() in INACTIVE_LIFECYCLE_STATES)


isc = ISCClient()
