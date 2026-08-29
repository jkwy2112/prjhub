from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut, UserUpdate, WeComAuthRequest
from app.services import auth_service, config_service, wecom_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.username), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse, summary="账号密码登录(本地, 失败后自动尝试 LDAP)")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_local(db, body.username, body.password)
    if user is None and config_service.ldap_config(db).get("enabled"):
        user = auth_service.authenticate_ldap(db, body.username, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    return _token_response(user)


@router.post("/wecom", response_model=TokenResponse, summary="企业微信授权码登录")
def wecom_login(body: WeComAuthRequest, db: Session = Depends(get_db)):
    if not config_service.wecom_config(db).get("enabled"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未启用企业微信登录")
    user = auth_service.authenticate_wecom(db, body.code)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "企业微信授权失败")
    return _token_response(user)


@router.get("/wecom/url", summary="获取企业微信授权跳转地址")
def wecom_auth_url(redirect_uri: str, db: Session = Depends(get_db)):
    if not config_service.wecom_config(db).get("enabled"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未启用企业微信登录")
    return {"url": wecom_service.get_authorize_url(db, redirect_uri)}


@router.get("/me", response_model=UserOut, summary="当前登录用户")
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut, summary="更新个人信息")
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
