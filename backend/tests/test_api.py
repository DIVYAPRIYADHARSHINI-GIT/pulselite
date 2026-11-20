import hashlib
import secrets
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from app.config import Settings
from app.main import COOKIE, create_app
from app.models import Base, Event, Site, User, LoginSession
from scripts.cleanup import cleanup

ORIGIN = 'http://localhost:5173'
WEB = 'https://test.pulselite.test'
UA = 'Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36'


@pytest.fixture
def env(database_url):
    app = create_app(Settings(database_url=database_url, event_limit=5))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app, headers={'origin': ORIGIN}) as client:
        yield app, client
    app.state.engine.dispose()


def account(client, email='unit-owner@pulselite.test'):
    password = secrets.token_urlsafe(24)
    response = client.post('/api/auth/signup', json={'email': email, 'password': password})
    assert response.status_code == 201
    return password


def site(client):
    account(client)
    response = client.post('/api/sites', json={'name': 'UNIT test site', 'origin': WEB})
    assert response.status_code == 201
    return response.json()


def send(client, s, **changes):
    data = {'type': 'pageview', 'path': '/', 'referrer': 'google.com', 'device': 'desktop', 'dnt': False}
    data.update(changes)
    return client.post('/api/event/' + s['site_key'], json=data, headers={'origin': WEB, 'user-agent': UA})


def test_health_real_query(env):
    app, c = env
    assert c.get('/health').json() == {'status': 'ok', 'database': 'connected'}
    # Instrumentation proves an actual SELECT executes.
    from sqlalchemy import event
    queries = []
    event.listen(app.state.engine, 'before_cursor_execute', lambda a, b, statement, *rest: queries.append(statement))
    assert c.get('/health').status_code == 200
    assert 'SELECT 1' in queries


def test_auth_lifecycle_and_hashes(env):
    app, c = env
    password = account(c)
    assert c.get('/api/auth/me').json()['email'] == 'unit-owner@pulselite.test'
    with app.state.Session() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith('$argon2id$')
        assert password not in user.password_hash
        stored = db.scalar(select(LoginSession.token_hash))
        assert stored == hashlib.sha256(c.cookies.get(COOKIE).encode()).hexdigest()
    assert c.post('/api/auth/signout').status_code == 204
    assert c.get('/api/auth/me').status_code == 401
    assert c.post('/api/auth/signin', json={'email': 'unit-owner@pulselite.test', 'password': password}).status_code == 200


def test_cookie_security_and_csrf(env):
    app, c = env
    app.state.settings.production = True
    r = c.post('/api/auth/signup', json={'email': 'secure-test@pulselite.test', 'password': secrets.token_urlsafe(24)})
    cookie = r.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'secure' in cookie and 'samesite=lax' in cookie and 'path=/api' in cookie
    assert c.post('/api/auth/signout', headers={'origin': 'https://evil.test'}).status_code == 403


def test_credentials_do_not_echo(env):
    _, c = env
    marker = secrets.token_urlsafe(20)
    response = c.post('/api/auth/signup', json={'email': 'invalid', 'password': marker})
    assert response.status_code == 422 and marker not in response.text


def test_wrong_password_and_duplicate(env):
    _, c = env
    account(c)
    payload = {'email': 'unit-owner@pulselite.test', 'password': secrets.token_urlsafe(24)}
    assert c.post('/api/auth/signin', json=payload).status_code == 401
    assert c.post('/api/auth/signup', json=payload).status_code == 409


def test_owner_isolation(env):
    _, c = env
    s = site(c)
    c.post('/api/auth/signout')
    account(c, 'other-unit-owner@pulselite.test')
    assert c.get('/api/sites').json() == []
    for suffix in ('', '/stats', '/export'):
        assert c.get(f'/api/sites/{s["id"]}{suffix}').status_code == 404
    assert c.patch(f'/api/sites/{s["id"]}', json={'respect_dnt': False}).status_code == 404


@pytest.mark.parametrize('origin', ['https://test.pulselite.test.evil.test', 'http://test.pulselite.test', 'null', '', 'https://evil.test'])
def test_origin_rejected(env, origin):
    _, c = env
    s = site(c)
    path = '/api/event/' + s['site_key']
    r = c.post(path, json={'type': 'pageview', 'path': '/', 'device': 'mobile'}, headers={'origin': origin, 'user-agent': UA})
    assert r.status_code == 403
    assert 'access-control-allow-origin' not in r.headers
    assert c.options(path, headers={'origin': origin}).status_code == 403


def test_collector_cors_no_credentials(env):
    _, c = env
    s = site(c)
    r = send(c, s)
    assert r.status_code == 202 and r.json()['accepted']
    assert r.headers['access-control-allow-origin'] == WEB
    assert 'access-control-allow-credentials' not in r.headers
    assert 'set-cookie' not in r.headers
    assert c.options('/api/event/' + s['site_key'], headers={'origin': WEB}).status_code == 204


def test_rate_limit_database_backed(env):
    app, c = env
    s = site(c)
    assert all(send(c, s).status_code == 202 for _ in range(5))
    assert send(c, s).status_code == 429
    # New application/worker must share the existing database limit.
    second = create_app(app.state.settings)
    with TestClient(second) as c2:
        assert send(c2, s).status_code == 429
    second.state.engine.dispose()


def test_auth_rate_limit(env):
    app, c = env
    app.state.settings.auth_limit = 2
    payload = {'email': 'missing-test@pulselite.test', 'password': secrets.token_urlsafe(24)}
    assert c.post('/api/auth/signin', json=payload).status_code == 401
    assert c.post('/api/auth/signin', json=payload).status_code == 401
    assert c.post('/api/auth/signin', json=payload).status_code == 429


def test_dnt_and_owner_override(env):
    _, c = env
    s = site(c)
    assert not send(c, s, dnt=True).json()['accepted']
    assert c.patch(f'/api/sites/{s["id"]}', json={'respect_dnt': False}).status_code == 200
    assert send(c, s, dnt=True).json()['accepted']


@pytest.mark.parametrize('agent', ['Googlebot/2.1', 'Mozilla HeadlessChrome/131', 'bingbot', 'curl/8', 'facebookexternalhit'])
def test_bots_ignored(env, agent):
    _, c = env
    s = site(c)
    r = c.post('/api/event/' + s['site_key'], json={'type': 'pageview', 'path': '/', 'device': 'desktop'}, headers={'origin': WEB, 'user-agent': agent})
    assert r.status_code == 202 and not r.json()['accepted']


@pytest.mark.parametrize('change', [{'device': 'fridge'}, {'type': 'click'}, {'path': 'not/absolute'}, {'path': '//evil.test'}, {'path': '/a\n'}, {'dnt': 'false'}, {'city': 'never'}, {'timestamp': '2000-01-01'}, {'path': '/' * 257}])
def test_impossible_and_extra_values(env, change):
    _, c = env
    s = site(c)
    assert send(c, s, **change).status_code == 422


def test_body_size(env):
    _, c = env
    s = site(c)
    assert c.post('/api/event/' + s['site_key'], content='x' * 1025, headers={'origin': WEB}).status_code == 413
    assert c.post('/api/auth/signup', content='x' * 4097).status_code == 413


def test_no_ip_or_raw_ua_in_any_database_column(env):
    app, c = env
    s = site(c)
    ua = 'PrivacyProbeUnique/927 Mozilla Chrome/130.0'
    address = '198.51.100.77'
    app.state.settings.trusted_vercel = True
    r = c.post('/api/event/' + s['site_key'], json={'type': 'pageview', 'path': '/journal?email=discarded#private', 'referrer': 'https://google.com/private?q=discard', 'device': 'mobile'}, headers={'origin': WEB, 'user-agent': ua, 'x-vercel-forwarded-for': address, 'x-vercel-ip-country': 'IN'})
    assert r.json()['accepted']
    with app.state.engine.connect() as connection:
        for table in inspect(app.state.engine).get_table_names():
            rows = connection.execute(text(f'SELECT * FROM "{table}"')).all()
            serialized = repr(rows)
            assert address not in serialized and ua not in serialized and 'PrivacyProbeUnique' not in serialized
            assert 'discarded' not in serialized
    with app.state.Session() as db:
        e = db.scalar(select(Event))
        assert e.path == '/journal' and e.referrer == 'google.com' and e.country == 'IN'
        assert e.browser == 'Chrome' and len(e.visitor_hash) == 64
    columns = set(Event.__table__.columns.keys())
    assert not columns.intersection({'ip', 'ip_address', 'user_agent', 'city', 'email', 'name'})


def test_untrusted_geo_header_ignored(env):
    _, c = env
    s = site(c)
    c.post('/api/event/' + s['site_key'], json={'type': 'pageview', 'path': '/', 'device': 'desktop'}, headers={'origin': WEB, 'user-agent': UA, 'x-vercel-ip-country': 'US', 'x-forwarded-for': '198.51.100.1'})
    assert c.get(f'/api/sites/{s["id"]}/stats').json()['country'][0]['name'] == 'ZZ'


def test_aggregation_filters_prior_dates_and_csv(env):
    app, c = env
    s = site(c)
    now = datetime.utcnow()
    with app.state.Session() as db:
        for days, path, visitor, device in [(0, '/', 'a', 'mobile'), (0, '/', 'a', 'mobile'), (0, '/work', 'b', 'desktop'), (1, '/', 'yesterday-a', 'mobile'), (3, '/', 'old-a', 'mobile')]:
            db.add(Event(site_id=s['id'], occurred_at=now - timedelta(days=days), visitor_hash=visitor, path=path, referrer='google.com', source='Search', device=device, browser='Chrome', country='IN'))
        db.commit()
    today = str(now.date())
    url = f'/api/sites/{s["id"]}/stats?start={today}&end={today}'
    data = c.get(url).json()
    assert (data['pageviews'], data['visitors'], data['previous']['pageviews'], data['previous']['visitors'], data['live']) == (3, 2, 1, 1, 2)
    assert len(data['series']) == 1 and data['series'][0]['pageviews'] == 3
    for filter_ in ['page=/', 'device=mobile']:
        assert c.get(url + '&' + filter_).json()['pageviews'] == 2
    for filter_ in ['browser=Chrome', 'country=IN', 'referrer=google.com', 'source=Search']:
        assert c.get(url + '&' + filter_).json()['pageviews'] == 3
    assert c.get(url + '&page=/missing').json()['pageviews'] == 0
    assert len(c.get(f'/api/sites/{s["id"]}/stats').json()['series']) == 30
    export = c.get(f'/api/sites/{s["id"]}/export?start={today}&end={today}')
    assert 'daily_unique_visitors' in export.text and 'visitor_hash' not in export.text
    assert 'attachment;' in export.headers['content-disposition']


@pytest.mark.parametrize('query', ['start=2025-02-30', 'start=2024-01-01&end=2026-01-01', 'start=2026-01-02&end=2026-01-01', 'end=2999-01-01', 'device=unknown', 'country=India'])
def test_invalid_ranges(env, query):
    _, c = env
    s = site(c)
    assert c.get(f'/api/sites/{s["id"]}/stats?{query}').status_code == 422


def test_cleanup(env):
    app, c = env
    s = site(c)
    send(c, s)
    with app.state.Session() as db:
        e = db.scalar(select(Event))
        e.occurred_at = datetime.utcnow() - timedelta(days=100)
        db.commit()
        assert cleanup(db, 90) == 1
        assert db.scalar(select(Event)) is None


@pytest.mark.parametrize('origin', ['https://example.test/path', 'javascript:alert(1)', 'http://public.test', 'https://user:pass@example.test', 'https://example.test:99999'])
def test_invalid_site_origin(env, origin):
    _, c = env
    account(c)
    assert c.post('/api/sites', json={'name': 'Bad origin test', 'origin': origin}).status_code == 422