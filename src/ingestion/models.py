from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator


class TicketProvider(str, Enum):
    ZENDESK = "zendesk"
    JIRA = "jira"


class TicketMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class ZendeskOnlineConfig(BaseModel):
    subdomain: str
    email: str
    api_token: str
    limit: int = 500


class JiraOnlineConfig(BaseModel):
    server_url: str
    """Full URL, e.g. https://company.atlassian.net or http://192.168.1.10:8080"""
    username: str
    api_token: str
    project_key: Optional[str] = None
    jql: Optional[str] = None
    limit: int = 500

    @field_validator("server_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class TicketSource(BaseModel):
    provider: TicketProvider
    mode: TicketMode
    zendesk_config: Optional[ZendeskOnlineConfig] = None
    jira_config: Optional[JiraOnlineConfig] = None
