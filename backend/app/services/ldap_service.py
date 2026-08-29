"""LDAP authentication service (ldap3, search-then-bind), config from DB overlaying env."""
import logging
from typing import Any, Dict, Optional

from ldap3 import ALL, Connection, Server
from ldap3.core.exceptions import LDAPException

logger = logging.getLogger(__name__)


class LDAPAuthResult:
    def __init__(self, username: str, name: str, email: str, dn: str):
        self.username = username
        self.name = name
        self.email = email
        self.dn = dn


def _server(cfg: Dict[str, Any]) -> Server:
    return Server(
        cfg["server"],
        port=636 if cfg.get("use_ssl") else 389,
        use_ssl=bool(cfg.get("use_ssl")),
        get_info=ALL,
        connect_timeout=5,
    )


def test_connection(cfg: Dict[str, Any]) -> "tuple[bool, str]":
    """Validate admin bind + search base. Returns (ok, message)."""
    if not cfg.get("server"):
        return False, "未配置 LDAP 服务器地址"
    try:
        with Connection(_server(cfg), user=cfg.get("bind_dn") or None,
                        password=cfg.get("bind_password") or None, auto_bind=True, receive_timeout=5):
            pass
        return True, "连接并绑定成功"
    except LDAPException as exc:
        return False, f"连接失败: {exc}"
    except Exception as exc:  # network / dns errors
        return False, f"连接失败: {exc}"


def authenticate(db, username: str, password: str) -> Optional[LDAPAuthResult]:
    """Search the user with admin bind, then verify credentials by binding as the user."""
    from app.services import config_service

    cfg = config_service.ldap_config(db)
    if not cfg.get("enabled"):
        return None
    if not password or not cfg.get("server"):
        return None

    search_filter = (cfg.get("search_filter") or "(uid={login})").format(login=_escape(username))
    try:
        with Connection(_server(cfg), user=cfg.get("bind_dn") or None,
                        password=cfg.get("bind_password") or None, auto_bind=True, receive_timeout=5) as conn:
            conn.search(cfg.get("search_base") or "", search_filter, attributes=[
                cfg.get("attr_username") or "uid",
                cfg.get("attr_display_name") or "cn",
                cfg.get("attr_email") or "mail",
            ])
            if not conn.entries:
                logger.info("LDAP search found no entry for %s", username)
                return None
            entry = conn.entries[0]

        with Connection(_server(cfg), user=entry.entry_dn, password=password, auto_bind=True):
            pass

        def val(attr: str) -> str:
            try:
                return str(entry[attr].value or "")
            except Exception:
                return ""

        return LDAPAuthResult(
            username=_norm(entry[cfg.get("attr_username") or "uid"].value or username),
            name=val(cfg.get("attr_display_name") or "cn"),
            email=val(cfg.get("attr_email") or "mail"),
            dn=entry.entry_dn,
        )
    except LDAPException as exc:
        logger.warning("LDAP authenticate failed for %s: %s", username, exc)
        return None


def _escape(value: str) -> str:
    for ch, rep in (("\\", r"\5c"), ("*", r"\2a"), ("(", r"\28"), (")", r"\29"), ("\x00", r"\00")):
        value = value.replace(ch, rep)
    return value


def _norm(value) -> str:
    return str(value or "").strip().lower()
