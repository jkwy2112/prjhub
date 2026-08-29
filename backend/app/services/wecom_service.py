"""WeCom (企业微信) OAuth2 service.

Flow (扫码/网页授权, scope=snsapi_base):
  1. Frontend redirects to WECOM_AUTHORIZE_URL with corpid + agentid + redirect_uri
  2. WeCom redirects back with ?code=xxx
  3. Backend exchanges code -> userid via /cgi-bin/auth/getuserinfo
  4. userid -> profile via /cgi-bin/user/get (name, email, avatar)
"""
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
GET_USERINFO_URL = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
USER_GET_URL = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
GET_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"

_token_cache: "dict[str, tuple[str, float]]" = {}


def get_authorize_url(redirect_uri: str, state: str = "wecom") -> str:
    from urllib.parse import quote_plus

    return (
        f"{AUTHORIZE_URL}?appid={settings.WECOM_CORP_ID}"
        f"&redirect_uri={quote_plus(redirect_uri)}"
        "&response_type=code&scope=snsapi_base"
        f"&agentid={settings.WECOM_AGENT_ID}&state={state}#wechat_redirect"
    )


def _get_access_token() -> str:
    cached = _token_cache.get("token")
    if cached and cached[1] > time.time():
        return cached[0]
    resp = httpx.get(
        GET_TOKEN_URL,
        params={"corpid": settings.WECOM_CORP_ID, "corpsecret": settings.WECOM_CORP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("errcode") not in (0, None):
        raise RuntimeError(f"wecom gettoken failed: {data}")
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 7200))
    _token_cache["token"] = (token, time.time() + expires_in - 300)
    return token


def login_with_code(code: str) -> Optional[dict]:
    """Exchange oauth code for a user profile dict; None on failure."""
    if not settings.WECOM_ENABLED:
        return None
    try:
        token = _get_access_token()
        resp = httpx.get(GET_USERINFO_URL, params={"access_token": token, "code": code}, timeout=10)
        data = resp.json()
        errcode = data.get("errcode", 0)
        if errcode not in (0, None):
            logger.warning("wecom getuserinfo failed: %s", data)
            return None
        userid = data.get("userid")
        if not userid:
            logger.warning("wecom getuserinfo returned no userid: %s", data)
            return None

        profile = {"userid": userid, "name": userid, "email": "", "avatar": ""}
        try:
            detail = httpx.get(USER_GET_URL, params={"access_token": token, "userid": userid}, timeout=10).json()
            if detail.get("errcode") in (0, None):
                profile.update(
                    name=detail.get("name") or userid,
                    email=detail.get("biz_mail") or detail.get("email") or "",
                    avatar=detail.get("thumb_avatar") or detail.get("avatar") or "",
                )
        except Exception:  # profile is best-effort
            logger.exception("wecom user/get failed")
        return profile
    except Exception:
        logger.exception("wecom login_with_code failed")
        return None
