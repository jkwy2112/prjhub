"""WeCom (企业微信) OAuth2 service, config from DB overlaying env.

Flow (网页授权, scope=snsapi_base):
  1. Frontend redirects to authorize URL with corpid + agentid + redirect_uri
  2. WeCom redirects back with ?code=xxx
  3. Backend exchanges code -> userid via /cgi-bin/auth/getuserinfo
  4. userid -> profile via /cgi-bin/user/get (name, email, avatar)
"""
import logging
import time
from typing import Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
GET_USERINFO_URL = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
USER_GET_URL = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
GET_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"

_token_cache: "dict[str, tuple[str, float]]" = {}


def _cache_key(cfg: dict) -> str:
    return f"{cfg.get('corp_id')}:{cfg.get('corp_secret')}"


def get_authorize_url(db, redirect_uri: str, state: str = "wecom") -> str:
    from app.services import config_service

    cfg = config_service.wecom_config(db)
    return (
        f"{AUTHORIZE_URL}?appid={cfg['corp_id']}"
        f"&redirect_uri={quote_plus(redirect_uri)}"
        "&response_type=code&scope=snsapi_base"
        f"&agentid={cfg.get('agent_id', '')}&state={state}#wechat_redirect"
    )


def test_connection(cfg: dict) -> "tuple[bool, str]":
    if not cfg.get("corp_id") or not cfg.get("corp_secret"):
        return False, "未配置 CorpID / Secret"
    try:
        resp = httpx.get(GET_TOKEN_URL, params={"corpid": cfg["corp_id"], "corpsecret": cfg["corp_secret"]}, timeout=10)
        data = resp.json()
        if data.get("errcode") in (0, None):
            return True, "获取 access_token 成功"
        return False, f"企业微信返回错误: errcode={data.get('errcode')} {data.get('errmsg')}"
    except Exception as exc:
        return False, f"请求失败: {exc}"


def _get_access_token(cfg: dict) -> str:
    key = _cache_key(cfg)
    cached = _token_cache.get(key)
    if cached and cached[1] > time.time():
        return cached[0]
    resp = httpx.get(
        GET_TOKEN_URL,
        params={"corpid": cfg["corp_id"], "corpsecret": cfg["corp_secret"]},
        timeout=10,
    )
    data = resp.json()
    if data.get("errcode") not in (0, None):
        raise RuntimeError(f"wecom gettoken failed: {data}")
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 7200))
    _token_cache[key] = (token, time.time() + expires_in - 300)
    return token


def login_with_code(db, code: str) -> Optional[dict]:
    """Exchange oauth code for a user profile dict; None on failure."""
    from app.services import config_service

    cfg = config_service.wecom_config(db)
    if not cfg.get("enabled"):
        return None
    try:
        token = _get_access_token(cfg)
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
