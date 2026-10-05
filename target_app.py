"""
Client for the agent's target application: the SailPoint SaaS Connectivity Demo API.

This is where invoice-bot "acts". Quarantine disables the agent's account here,
so containment happens on the target system as well as in governance.

Credential: OS credential store, service "saas-demo-api", account "api_key" (sck_...).
"""

import os
from typing import Any, Optional

import httpx
import keyring

from isc_client import TIMEOUT, logger

TARGET_BASE_URL = os.getenv("TARGET_APP_BASE_URL", "https://dugfer5z7k.execute-api.us-east-1.amazonaws.com/v1")
TARGET_KEY_SERVICE = os.getenv("TARGET_APP_KEY_SERVICE", "saas-demo-api")


class TargetAppError(Exception):
    """Safe, user-facing error for the target app."""


def configured() -> bool:
    return bool(keyring.get_password(TARGET_KEY_SERVICE, "api_key"))


async def _call(method: str, path: str, **kwargs: Any) -> httpx.Response:
    key = keyring.get_password(TARGET_KEY_SERVICE, "api_key")
    if not key:
        raise TargetAppError(f"No target-app API key in credential store (service '{TARGET_KEY_SERVICE}', account 'api_key').")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.request(method, f"{TARGET_BASE_URL}{path}", headers={"Authorization": f"Bearer {key.strip()}"}, **kwargs)
    logger.info(f"event=target_app_call method={method} path={path} status={resp.status_code}")
    if resp.status_code == 401:
        raise TargetAppError("Target app rejected the API key (demo keys expire after 7 days).")
    return resp


async def find_account(user_name: str) -> Optional[dict]:
    cursor: Optional[str] = None
    while True:
        params: dict = {"limit": 50}
        if cursor:
            params["cursor"] = cursor
        resp = await _call("GET", "/users", params=params)
        if resp.status_code >= 400:
            raise TargetAppError(f"Target app list failed (HTTP {resp.status_code}).")
        body = resp.json()
        for item in body.get("items", []):
            if item.get("userName") == user_name:
                return item
        cursor = body.get("cursor")
        if not cursor:
            return None


async def create_account(account: dict) -> dict:
    resp = await _call("POST", "/users", json=account)
    if resp.status_code not in (200, 201):
        raise TargetAppError(f"Target app create failed (HTTP {resp.status_code}): {resp.text[:200]}")
    return resp.json()


async def disable_account(account_id: str) -> dict:
    resp = await _call("POST", f"/users/{account_id}/disable")
    if resp.status_code >= 400:
        raise TargetAppError(f"Target app disable failed (HTTP {resp.status_code}).")
    return resp.json() if resp.content else {"id": account_id, "active": False}


async def enable_account(account_id: str) -> dict:
    resp = await _call("POST", f"/users/{account_id}/enable")
    if resp.status_code >= 400:
        raise TargetAppError(f"Target app enable failed (HTTP {resp.status_code}).")
    return resp.json() if resp.content else {"id": account_id, "active": True}
