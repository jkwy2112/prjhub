from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "PrjHub"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "change-me-in-production-9f2c1b7a"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    DATABASE_URL: str = "sqlite:///./data/prjhub.db"

    # bootstrap admin (seeded on first startup)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # ---- LDAP ----
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str = ""            # e.g. ldap://ldap.example.com:389
    LDAP_USE_SSL: bool = False
    LDAP_BIND_DN: str = ""           # admin/search DN, e.g. cn=admin,dc=example,dc=com
    LDAP_BIND_PASSWORD: str = ""
    LDAP_SEARCH_BASE: str = ""       # e.g. ou=people,dc=example,dc=com
    LDAP_SEARCH_FILTER: str = "(uid={login})"   # or (sAMAccountName={login})
    LDAP_ATTR_USERNAME: str = "uid"
    LDAP_ATTR_DISPLAY_NAME: str = "cn"
    LDAP_ATTR_EMAIL: str = "mail"

    # ---- WeCom (企业微信) ----
    WECOM_ENABLED: bool = False
    WECOM_CORP_ID: str = ""
    WECOM_CORP_SECRET: str = ""
    WECOM_AGENT_ID: str = ""

    # ---- reminders ----
    REMINDER_ENABLED: bool = True
    REMINDER_INTERVAL_MINUTES: int = 10

    # ---- Git repos ----
    REPOS_DIR: str = "./repos"
    GIT_INITIAL_BRANCH: str = "main"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> "list[str]":
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
