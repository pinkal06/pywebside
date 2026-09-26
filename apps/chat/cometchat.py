import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger("apps.chat.cometchat")


class CometChatError(RuntimeError):
    """Raised when a CometChat call fails."""


def get_cometchat_base_url() -> str:
    region = (settings.COMETCHAT_REGION or "").strip()
    if not region:
        raise CometChatError("CometChat region is not configured.")
    return f"https://api-{region}.cometchat.io/v3"


def get_cometchat_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    rest_api_key = (settings.COMETCHAT_REST_API_KEY or "").strip()
    if rest_api_key:
        headers["apiKey"] = rest_api_key
    return headers


def _request_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not settings.COMETCHAT_APP_ID:
        raise CometChatError("CometChat App ID is not configured.")

    url = f"{get_cometchat_base_url()}{path}"
    headers = get_cometchat_headers()
    headers["appId"] = str(settings.COMETCHAT_APP_ID)

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.exception("CometChat request failed for %s %s", method, path)
        raise CometChatError(f"CometChat request failed: {exc}") from exc

    if response.status_code in {200, 201, 202, 204}:
        if response.content:
            try:
                return response.json()
            except ValueError:
                return {}
        return {}

    text = response.text[:500]
    logger.warning("CometChat API error %s for %s %s: %s", response.status_code, method, path, text)
    raise CometChatError(f"CometChat API returned status {response.status_code}: {text}")


def ensure_cometchat_user(uid: str, name: str) -> Dict[str, Any]:
    payload = {
        "uid": uid,
        "name": name[:80] if name else uid,
    }
    try:
        return _request_json("POST", "/users", payload)
    except CometChatError as exc:
        if "409" not in str(exc):
            raise
        return _request_json("POST", f"/users/{uid}", {"name": payload["name"]})


def generate_cometchat_auth_token(uid: str) -> str:
    response = _request_json("POST", f"/users/{uid}/auth_tokens")
    if isinstance(response, dict):
        data = response.get("data") or response
        token = data.get("authToken") if isinstance(data, dict) else None
        if token:
            return token
    raise CometChatError("CometChat auth token missing from response.")


def delete_cometchat_user(uid: str) -> None:
    _request_json("DELETE", f"/users/{uid}")
