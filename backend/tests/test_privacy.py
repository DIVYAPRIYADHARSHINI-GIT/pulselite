from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, DailySalt
from app.privacy import browser_family, daily_salt, is_bot, rate_allowed, traffic_source, visitor_hash


def test_hash_site_separation_and_unambiguous_encoding():
    salt = b'x' * 32
    a = visitor_hash('address', 'agent', 'site-a', salt)
    assert a == visitor_hash('address', 'agent', 'site-a', salt)
    assert a != visitor_hash('address', 'agent', 'site-b', salt)
    assert a != visitor_hash('address', 'agent', 'site-a', b'y' * 32)
    assert visitor_hash('ab', 'c', 'd', salt) != visitor_hash('a', 'bc', 'd', salt)


def test_salt_rotates_and_old_salt_removed():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yesterday = date(2026, 1, 1)
        salt1 = daily_salt(db, yesterday)
        assert salt1 == daily_salt(db, yesterday)
        salt2 = daily_salt(db, yesterday + timedelta(days=1))
        assert salt1 != salt2
        assert db.scalars(select(DailySalt.day)).all() == [yesterday + timedelta(days=1)]
        assert visitor_hash('a', 'b', 'c', salt1) != visitor_hash('a', 'b', 'c', salt2)


def test_rate_window_resets():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        now = datetime(2026, 1, 1)
        assert rate_allowed(db, 'public-key', 1, now)
        assert not rate_allowed(db, 'public-key', 1, now)
        assert rate_allowed(db, 'public-key', 1, now + timedelta(minutes=1))


def test_bot_browser_and_sources():
    assert is_bot('GoogleBot') and not is_bot('Mozilla/5.0 Chrome/130.0')
    assert browser_family('Chrome/130 Edg/130') == 'Edge'
    assert browser_family('unknown') == 'Other'
    assert traffic_source('google.com.evil.test', 'https://site.test') == 'Referral'
    assert traffic_source('www.google.com', 'https://site.test') == 'Search'
    assert traffic_source('site.test', 'https://site.test') == 'Internal'