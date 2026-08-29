"""LDAP authentication service (ldap3, search-then-bind)."""
import logging
from typing import Optional

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class LDAPAuthResult:
    def __init__(self, username: str, name: str, email: str, dn: str):
        self.username = username
        self.name = name
        self.email = email
        self.dn = dn


def _server() -> Server:
    use_ssl = settings.LDAP_USE_SSL
    tls = Tls() if use_ssl else None
    return Server(
        settings.LDAP_SERVER,
        port=636 if use_ssl else 389,
        use_ssl=use_ssl,
        get_info=ALL,
        tls=tls,
        connect_timeout=5,
    )


def authenticate(username: str, password: str) -> Optional[LDAPAuthResult]:
    """Search the user with admin bind, then verify credentials by binding as the user."""
    if not settings.LDAP_ENABLED:
        return None
    if not password:
        return None

    search_filter = settings.LDAP_SEARCH_FILTER.format(login=_escape(username))
    try:
        with Connection(_server(), user=settings.LDAP_BIND_DN, password=settings.LDAP_BIND_PASSWORD,
                        auto_bind=True, receive_timeout=5) as conn:
            conn.search(settings.LDAP_SEARCH_BASE, search_filter, attributes=[
                settings.LDAP_ATTR_USERNAME,
                settings.LDAP_ATTR_DISPLAY_NAME,
                settings.LDAP_ATTR_EMAIL,
            ])
            if not conn.entries:
                logger.info("LDAP search found no entry for %s", username)
                return None
            entry = conn.entries[0]

        # verify password by binding as the located DN
        with Connection(_server(), user=entry.entry_dn, password=password, auto_bind=True):
            pass

        return LDAPAuthResult(
            username=_norm(entry[settings.LDAP_ATTR_USERNAME].value or username),
            name=str(entry[settings.LDAP_ATTR_DISPLAY_NAME].value or ""),
            email=str(entry[settings.LDAP_ATTR_EMAIL].value or ""),
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
