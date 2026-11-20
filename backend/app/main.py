import csv
import hashlib
import io
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from .config import Settings
from .models import Event, LoginSession, Site, User
from .privacy import browser_family, clean_path, daily_salt, is_bot, rate_allowed, referrer_host, traffic_source, visitor_hash
from .schemas import Credentials, PageView, SiteInput, SiteSettings
from .stats import aggregate

PASSWORDS = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
COOKIE = 'pulselite_session'


class BodyLimit:
    """Bound bytes before JSON parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PATCH', 'PUT'):
            return await self.app(scope, receive, send)
        cap = 1024 if scope['path'].startswith('/api/event/') else 4096
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body = message.get('body', b'')
            size += len(body)
            if size > cap:
                response = JSONResponse({'detail': 'Request body too large'}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(body)
            if not message.get('more_body'):
                break
        used = False

        async def bounded_receive():
            nonlocal used
            if not used:
                used = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)


def site_dict(site):
    return {name: getattr(site, name) for name in ('id', 'name', 'origin', 'site_key', 'respect_dnt', 'is_demo')}


def create_app(settings=None):
    settings = settings or Settings.from_env()
    engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout': 20} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True, hide_parameters=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    Session = sessionmaker(engine, expire_on_commit=False)
    @asynccontextmanager
    async def lifespan(_app):
        # Run inside hosting only; credentials never need to leave the platform.
        if settings.production and os.getenv('PULSELITE_BOOTSTRAP') == '1':
            from alembic import command
            from alembic.config import Config
            try:
                with engine.begin() as connection:
                    connection.execute(text('SELECT pg_advisory_xact_lock(78120417)'))
                    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
                    config.set_main_option('script_location', str(Path(__file__).parents[1] / 'migrations'))
                    config.attributes['connection'] = connection
                    command.upgrade(config, 'head')
                if os.getenv('PULSELITE_SEED_DEMO') == '1':
                    with engine.begin() as guard:
                        guard.execute(text('SELECT pg_advisory_xact_lock(78120418)'))
                        if not guard.scalar(select(Site.id).where(Site.is_demo.is_(True)).limit(1)):
                            from scripts.seed import seed
                            seed()
            except Exception:
                raise RuntimeError('Database initialization failed; verify the hosted integration and migration configuration.') from None
        yield

    app = FastAPI(title='PulseLite API', docs_url=None if settings.production else '/docs', redoc_url=None, lifespan=lifespan)
    app.state.engine, app.state.Session, app.state.settings = engine, Session, settings

    def db_session():
        with Session() as db:
            yield db

    def current_user(request: Request, db=Depends(db_session)):
        token = request.cookies.get(COOKIE, '')
        digest = hashlib.sha256(token.encode()).hexdigest()
        session = db.scalar(select(LoginSession).where(LoginSession.token_hash == digest, LoginSession.expires_at > datetime.utcnow()))
        if not session:
            raise HTTPException(401, 'Please sign in to continue')
        return db.get(User, session.user_id)

    def owned_site(site_id, user, db):
        site = db.scalar(select(Site).where(Site.id == site_id, Site.owner_id == user.id))
        if not site:
            raise HTTPException(404, 'Site not found')
        return site

    def new_session(user, response, db):
        token = secrets.token_urlsafe(32)
        db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=datetime.utcnow() + timedelta(days=7)))
        db.commit()
        response.set_cookie(COOKIE, token, max_age=604800, httponly=True, secure=settings.production, samesite='lax', path='/api')
        return {'id': user.id, 'email': user.email}

    def auth_rate(request, email, db):
        # Raw IP/email never enter the limiter table. Do not trust generic X-Forwarded-For.
        address = request.client.host if request.client else ''
        if settings.trusted_vercel:
            address = request.headers.get('x-vercel-forwarded-for', address).split(',')[0].strip()
        salt = daily_salt(db, datetime.utcnow().date())
        bucket = visitor_hash(address, '', 'auth', salt)
        email_bucket = visitor_hash('', email, 'auth-email', salt)
        if not rate_allowed(db, bucket, settings.auth_limit) or not rate_allowed(db, email_bucket, settings.auth_limit):
            raise HTTPException(429, 'Too many attempts. Please try again in a minute.', headers={'Retry-After': '60'})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _exc):
        # Pydantic errors normally echo input, potentially including passwords.
        return JSONResponse({'detail': 'Invalid input. Check the field formats and limits.'}, status_code=422)

    @app.middleware('http')
    async def security(request, call_next):
        origin = request.headers.get('origin', '')
        path = request.url.path
        collector = path.startswith('/api/event/')
        allowed = origin == settings.dashboard_origin
        if collector:
            key = path.rsplit('/', 1)[-1]
            with Session() as db:
                site = db.scalar(select(Site).where(Site.site_key == key)) if re.fullmatch(r'[A-Za-z0-9_-]{20,40}', key) else None
                allowed = bool(site and origin == site.origin)
        if request.method == 'OPTIONS':
            response = Response(status_code=204 if allowed else 403)
        elif (collector or (request.method in ('POST', 'PUT', 'PATCH', 'DELETE'))) and not allowed:
            response = JSONResponse({'detail': 'Origin is not registered for this request'}, status_code=403)
        else:
            response = await call_next(request)
        if allowed and origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Vary'] = 'Origin'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS' if collector else 'GET, POST, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            if not collector:
                response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    app.add_middleware(BodyLimit)

    @app.get('/health')
    @app.get('/api/health')
    def health(db=Depends(db_session)):
        try:
            db.execute(text('SELECT 1')).scalar_one()
            return {'status': 'ok', 'database': 'connected'}
        except Exception:
            return JSONResponse({'status': 'unavailable'}, status_code=503)

    @app.post('/api/auth/signup', status_code=201)
    def signup(body: Credentials, request: Request, response: Response, db=Depends(db_session)):
        auth_rate(request, body.email, db)
        user = User(email=body.email, password_hash=PASSWORDS.hash(body.password))
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Unable to create account. Try signing in instead.')
        return new_session(user, response, db)

    @app.post('/api/auth/signin')
    def signin(body: Credentials, request: Request, response: Response, db=Depends(db_session)):
        auth_rate(request, body.email, db)
        user = db.scalar(select(User).where(User.email == body.email))
        try:
            PASSWORDS.verify(user.password_hash if user else DUMMY_HASH, body.password)
        except VerificationError:
            raise HTTPException(401, 'Email or password is incorrect')
        if not user:
            raise HTTPException(401, 'Email or password is incorrect')
        return new_session(user, response, db)

    @app.post('/api/auth/signout', status_code=204)
    def signout(request: Request, response: Response, _user=Depends(current_user), db=Depends(db_session)):
        digest = hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest()
        db.execute(delete(LoginSession).where(LoginSession.token_hash == digest))
        db.commit()
        response.delete_cookie(COOKIE, path='/api', secure=settings.production, httponly=True, samesite='lax')

    @app.get('/api/auth/me')
    def me(user=Depends(current_user)):
        return {'id': user.id, 'email': user.email}

    @app.get('/api/sites')
    def sites(user=Depends(current_user), db=Depends(db_session)):
        return [site_dict(s) for s in db.scalars(select(Site).where(Site.owner_id == user.id).order_by(Site.id.desc()))]

    @app.post('/api/sites', status_code=201)
    def add_site(body: SiteInput, user=Depends(current_user), db=Depends(db_session)):
        site = Site(owner_id=user.id, name=body.name, origin=body.origin, site_key=secrets.token_urlsafe(24))
        db.add(site)
        db.commit()
        return site_dict(site)

    @app.get('/api/sites/{site_id}')
    def get_site(site_id: int, user=Depends(current_user), db=Depends(db_session)):
        return site_dict(owned_site(site_id, user, db))

    @app.patch('/api/sites/{site_id}')
    def settings_site(site_id: int, body: SiteSettings, user=Depends(current_user), db=Depends(db_session)):
        site = owned_site(site_id, user, db)
        site.respect_dnt = body.respect_dnt
        db.commit()
        return site_dict(site)

    @app.get('/api/tracker.js')
    def tracker():
        path = Path(__file__).parent / 'tracker.js'
        return Response(path.read_text() if path.exists() else '', media_type='text/javascript', headers={'Cache-Control': 'public, max-age=300'})

    @app.post('/api/event/{key}', status_code=202)
    def collect(key: str, body: PageView, request: Request, db=Depends(db_session)):
        site = db.scalar(select(Site).where(Site.site_key == key))
        if not site:
            raise HTTPException(404, 'Site not found')
        if not rate_allowed(db, 'event:' + key, settings.event_limit):
            raise HTTPException(429, 'Site rate limit reached', headers={'Retry-After': '60'})
        ua = request.headers.get('user-agent', '')[:1024]
        if is_bot(ua) or (site.respect_dnt and (body.dnt or request.headers.get('dnt') == '1')):
            return {'accepted': False}
        now = datetime.utcnow()
        ip = request.client.host if request.client else ''
        country = 'ZZ'
        if settings.trusted_vercel:
            ip = request.headers.get('x-vercel-forwarded-for', ip).split(',')[0].strip()
            header_country = request.headers.get('x-vercel-ip-country', '').upper()
            if re.fullmatch('[A-Z]{2}', header_country):
                country = header_country
        digest = visitor_hash(ip, ua, key, daily_salt(db, now.date()))
        browser = browser_family(ua)
        del ip, ua
        referrer = referrer_host(body.referrer)
        db.add(Event(site_id=site.id, occurred_at=now, visitor_hash=digest, path=clean_path(body.path), referrer=referrer, source=traffic_source(referrer, site.origin), device=body.device, browser=browser, country=country))
        db.commit()
        return {'accepted': True}

    def parameters(start: date | None = None, end: date | None = None, page: str | None = Query(None, max_length=256), device: str | None = Query(None, pattern='^(mobile|tablet|desktop)$'), browser: str | None = Query(None, pattern='^(Chrome|Firefox|Safari|Edge|Opera|Other)$'), country: str | None = Query(None, pattern='^[A-Z]{2}$'), referrer: str | None = Query(None, max_length=253), source: str | None = Query(None, pattern='^(Direct|Internal|Search|Social|Referral)$')):
        today = datetime.utcnow().date()
        return start or today - timedelta(days=29), end or today, {'path': page, 'device': device, 'browser': browser, 'country': country, 'referrer': referrer, 'source': source}

    @app.get('/api/sites/{site_id}/stats')
    def stats(site_id: int, params=Depends(parameters), user=Depends(current_user), db=Depends(db_session)):
        site = owned_site(site_id, user, db)
        return {'site': site_dict(site), **aggregate(db, site.id, *params)}

    @app.get('/api/sites/{site_id}/export')
    def export(site_id: int, params=Depends(parameters), user=Depends(current_user), db=Depends(db_session)):
        owned_site(site_id, user, db)
        data = aggregate(db, site_id, *params)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['dimension', 'value', 'pageviews', 'daily_unique_visitors'])
        for row in data['series']:
            writer.writerow(['date', row['date'], row['pageviews'], row['visitors']])
        for dim in ('path', 'device', 'browser', 'country', 'referrer', 'source'):
            for row in data[dim]:
                value = row['name']
                if value.startswith(('=', '+', '-', '@', '\t', '\r')):
                    value = "'" + value
                writer.writerow([dim, value, row['pageviews'], row['visitors']])
        return PlainTextResponse('\ufeff' + output.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="pulselite-aggregates.csv"'})

    @app.get('/api/demo/stats')
    def demo(params=Depends(parameters), db=Depends(db_session)):
        site = db.scalar(select(Site).where(Site.is_demo.is_(True)).order_by(Site.id))
        if not site:
            raise HTTPException(404, 'Demo data is not seeded yet')
        return {'site': site_dict(site), **aggregate(db, site.id, *params)}

    return app


app = create_app()