"""Unified authentication: local password / LDAP / WeCom, with auto user provisioning."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import AuthType, User
from app.services import ldap_service, wecom_service

logger = logging.getLogger(__name__)


def authenticate_local(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username.strip().lower()).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return None
    return user if user.is_active else None


def authenticate_ldap(db: Session, username: str, password: str) -> Optional[User]:
    result = ldap_service.authenticate(db, username, password)
    if result is None:
        return None
    user = _provision(
        db,
        auth_type=AuthType.ldap,
        username=result.username,
        external_id=result.dn,
        name=result.name,
        email=result.email,
        dept=result.dept,
    )
    return user if user.is_active else None


def authenticate_wecom(db: Session, code: str) -> Optional[User]:
    profile = wecom_service.login_with_code(code)
    if profile is None:
        return None
    user = _provision(
        db,
        auth_type=AuthType.wecom,
        username=f"wecom_{profile['userid']}",
        external_id=profile["userid"],
        name=profile.get("name") or profile["userid"],
        email=profile.get("email") or "",
        avatar=profile.get("avatar") or "",
    )
    return user if user.is_active else None


def _provision(db: Session, auth_type: AuthType, username: str, external_id: str,
               name: str = "", email: str = "", avatar: str = "", dept: str = "") -> User:
    """First login from external IdP creates the account; afterwards syncs profile."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        user = User(
            username=username,
            name=name or username,
            email=email,
            dept=dept,
            avatar=avatar,
            auth_type=auth_type,
            external_id=external_id,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        logger.info("provisioned %s user %s", auth_type.value, username)
    else:
        changed = False
        if not user.external_id:
            user.external_id, changed = external_id, True
        if name and user.name in ("", user.username):
            user.name, changed = name, True
        if email and not user.email:
            user.email, changed = email, True
        if avatar and not user.avatar:
            user.avatar, changed = avatar, True
        if dept and not user.dept:
            user.dept, changed = dept, True
        if changed:
            db.commit()
    db.refresh(user)
    return user
