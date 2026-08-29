"""Runtime system configuration stored in DB, overlaying .env settings."""
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SystemConfig

LDAP_KEY = "auth_ldap"
WECOM_KEY = "auth_wecom"

LDAP_FIELDS = (
    "enabled", "server", "use_ssl", "bind_dn", "bind_password",
    "search_base", "search_filter", "attr_username", "attr_display_name", "attr_email",
)
WECOM_FIELDS = ("enabled", "corp_id", "corp_secret", "agent_id")

SECRET_FIELDS = ("bind_password", "corp_secret")
MASK = "******"


def _load(db: Session, key: str) -> dict:
    row = db.get(SystemConfig, key)
    return dict(row.value) if row and row.value else {}


def _clean(data: Dict[str, Any], fields) -> dict:
    out = {}
    for f in fields:
        if f in data and data[f] is not None:
            v = data[f]
            if isinstance(v, str) and v.strip() in ("", MASK):
                continue  # keep existing secret when masked value is submitted
            out[f] = v
    return out


def save_ldap_config(db: Session, data: Dict[str, Any]) -> None:
    cfg = _load(db, LDAP_KEY)
    cfg.update(_clean(data, LDAP_FIELDS))
    db.merge(SystemConfig(key=LDAP_KEY, value=cfg))
    db.commit()


def save_wecom_config(db: Session, data: Dict[str, Any]) -> None:
    cfg = _load(db, WECOM_KEY)
    cfg.update(_clean(data, WECOM_FIELDS))
    db.merge(SystemConfig(key=WECOM_KEY, value=cfg))
    db.commit()


def ldap_config(db: Session) -> Dict[str, Any]:
    """DB overrides env; a stored value of any field wins when set."""
    override = _load(db, LDAP_KEY)
    return {
        "enabled": bool(override.get("enabled", settings.LDAP_ENABLED)),
        "server": override.get("server") or settings.LDAP_SERVER,
        "use_ssl": bool(override.get("use_ssl", settings.LDAP_USE_SSL)),
        "bind_dn": override.get("bind_dn") or settings.LDAP_BIND_DN,
        "bind_password": override.get("bind_password") or settings.LDAP_BIND_PASSWORD,
        "search_base": override.get("search_base") or settings.LDAP_SEARCH_BASE,
        "search_filter": override.get("search_filter") or settings.LDAP_SEARCH_FILTER,
        "attr_username": override.get("attr_username") or settings.LDAP_ATTR_USERNAME,
        "attr_display_name": override.get("attr_display_name") or settings.LDAP_ATTR_DISPLAY_NAME,
        "attr_email": override.get("attr_email") or settings.LDAP_ATTR_EMAIL,
    }


def wecom_config(db: Session) -> Dict[str, Any]:
    override = _load(db, WECOM_KEY)
    return {
        "enabled": bool(override.get("enabled", settings.WECOM_ENABLED)),
        "corp_id": override.get("corp_id") or settings.WECOM_CORP_ID,
        "corp_secret": override.get("corp_secret") or settings.WECOM_CORP_SECRET,
        "agent_id": override.get("agent_id") or settings.WECOM_AGENT_ID,
    }


def masked(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    for f in SECRET_FIELDS:
        if out.get(f):
            out[f] = MASK
    return out
