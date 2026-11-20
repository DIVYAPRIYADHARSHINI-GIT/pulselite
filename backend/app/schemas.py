import re
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Credentials(StrictModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}', value):
            raise ValueError('Enter a valid email address')
        return value


class SiteInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    origin: str = Field(min_length=8, max_length=255)

    @field_validator('name')
    @classmethod
    def name_valid(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid site name')
        return value

    @field_validator('origin')
    @classmethod
    def origin_valid(cls, value):
        value = value.strip().rstrip('/')
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError('Use an exact http(s) origin without a path')
        if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1'):
            raise ValueError('Public sites require HTTPS')
        if not re.fullmatch(r'[a-zA-Z0-9.-]+', parsed.hostname):
            raise ValueError('Invalid hostname')
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError('Invalid port')
        default = (parsed.scheme == 'http' and port == 80) or (parsed.scheme == 'https' and port == 443)
        return f'{parsed.scheme}://{parsed.hostname.lower()}' + (f':{port}' if port and not default else '')


class SiteSettings(StrictModel):
    respect_dnt: bool


class PageView(StrictModel):
    type: Literal['pageview']
    path: str = Field(min_length=1, max_length=256)
    referrer: str = Field(default='', max_length=253)
    device: Literal['mobile', 'tablet', 'desktop']
    dnt: bool = False

    @field_validator('path')
    @classmethod
    def path_valid(cls, value):
        if not value.startswith('/') or value.startswith('//') or any(ord(c) < 32 for c in value) or '\\' in value:
            raise ValueError('Invalid path')
        return value

    @field_validator('referrer')
    @classmethod
    def referrer_valid(cls, value):
        if value and (any(ord(c) < 33 for c in value) or '@' in value or not re.fullmatch(r'[a-zA-Z0-9.:/\-_%?=&+#]+', value)):
            raise ValueError('Invalid referrer')
        return value