from datetime import datetime, timedelta
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.config import Settings
from app.main import create_app
from app.models import Base, Event, LoginSession
from test_api import ORIGIN, site, send


def test_direct_referrer_filter_and_midnight_boundaries(database_url):
    app = create_app(Settings(database_url=database_url))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app, headers={'origin': ORIGIN}) as c:
        s = site(c)
        midnight = datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
        with app.state.Session() as db:
            for when, visitor, ref in [(midnight, 'today', ''), (midnight-timedelta(microseconds=1), 'prior', ''), (midnight, 'search', 'google.com')]:
                db.add(Event(site_id=s['id'], occurred_at=when, visitor_hash=visitor, path='/', referrer=ref, source='Direct' if not ref else 'Search',device='desktop',browser='Chrome',country='ZZ'))
            db.commit()
        today=str(midnight.date())
        data=c.get(f'/api/sites/{s["id"]}/stats?start={today}&end={today}&referrer=Direct').json()
        assert data['pageviews']==1
        assert data['previous']['pageviews']==1
        assert data['referrer'][0]['name']=='Direct'
    app.state.engine.dispose()


def test_expired_session_is_not_authenticated(database_url):
    app = create_app(Settings(database_url=database_url))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app, headers={'origin': ORIGIN}) as c:
        site(c)
        with app.state.Session() as db:
            session=db.scalar(select(LoginSession))
            session.expires_at=datetime.utcnow()-timedelta(seconds=1)
            db.commit()
        assert c.get('/api/sites').status_code==401
    app.state.engine.dispose()


def test_config_rejects_production_sqlite(monkeypatch):
    monkeypatch.setenv('PULSELITE_ENV','production')
    monkeypatch.setenv('DATABASE_URL','sqlite:///unsafe.db')
    import pytest
    with pytest.raises(RuntimeError, match='Production requires'):
        Settings.from_env()


def test_chunked_body_cannot_bypass_limit(database_url):
    app=create_app(Settings(database_url=database_url))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app, headers={'origin':ORIGIN}) as c:
        r=c.post('/api/auth/signup',content=iter([b'x'*2000,b'x'*2000,b'x'*1000]))
        assert r.status_code==413
    app.state.engine.dispose()