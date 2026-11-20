import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime
from urllib.parse import urlsplit
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .models import DailySalt, RateBucket


def insert_for(db, model):
    return (pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert)(model)


def daily_salt(db, day):
    db.execute(insert_for(db, DailySalt).values(day=day, salt=secrets.token_bytes(32)).on_conflict_do_nothing())
    salt = db.scalar(select(DailySalt.salt).where(DailySalt.day == day))
    db.execute(delete(DailySalt).where(DailySalt.day < day))
    return salt


def visitor_hash(ip: str, ua: str, site_key: str, salt: bytes):
    message = json.dumps([ip, ua, site_key], separators=(',', ':')).encode()
    return hmac.new(salt, message, hashlib.sha256).hexdigest()


def rate_allowed(db, key: str, limit: int, now=None):
    window = int((now or datetime.utcnow()).timestamp()) // 60
    key = hashlib.sha256(key.encode()).hexdigest()
    statement = insert_for(db, RateBucket).values(key=key, window=window, count=1)
    statement = statement.on_conflict_do_update(index_elements=['key', 'window'], set_={'count': RateBucket.count + 1}).returning(RateBucket.count)
    count = db.scalar(statement)
    db.execute(delete(RateBucket).where(RateBucket.window < window - 10))
    db.commit()
    return count <= limit


BOT = re.compile(r'bot|crawler|spider|slurp|headless|lighthouse|facebookexternalhit|preview|wget|curl', re.I)


def is_bot(ua):
    return not ua or bool(BOT.search(ua))


def browser_family(ua):
    for marker, family in [('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'), ('FxiOS/', 'Firefox'), ('Chrome/', 'Chrome'), ('CriOS/', 'Chrome'), ('Safari/', 'Safari')]:
        if marker in ua:
            return family
    return 'Other'


def clean_path(value):
    return value.split('?', 1)[0].split('#', 1)[0]


def referrer_host(value):
    if not value:
        return ''
    # Accept the hostname sent by our tracker; strip URLs from other clients.
    host = urlsplit(value if '://' in value else 'https://' + value).hostname or ''
    return host.lower().rstrip('.')[:253]


def traffic_source(host, site_origin):
    if not host:
        return 'Direct'
    if host == urlsplit(site_origin).hostname:
        return 'Internal'
    if any(host == domain or host.endswith('.' + domain) for domain in ('google.com', 'bing.com', 'duckduckgo.com', 'search.yahoo.com', 'baidu.com')):
        return 'Search'
    if any(host == domain or host.endswith('.' + domain) for domain in ('facebook.com', 'instagram.com', 'linkedin.com', 't.co', 'reddit.com', 'x.com')):
        return 'Social'
    return 'Referral'