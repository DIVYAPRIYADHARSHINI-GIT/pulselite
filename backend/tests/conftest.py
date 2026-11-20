"""SQLite by default; hosted PostgreSQL tests use disposable isolated schemas.

PULSELITE_TEST_POSTGRES=1 is for the approved Vercel build only. DATABASE_URL
stays in hosting memory. Never print it or place it in any local file.
"""
import os
import secrets
import socket
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import Settings


@pytest.fixture
def database_url(tmp_path):
    if os.getenv('PULSELITE_TEST_POSTGRES') != '1':
        yield f'sqlite:///{tmp_path}/test.db'
        return
    base = os.getenv('DATABASE_URL_UNPOOLED') or Settings.from_env().database_url
    if not base.startswith('postgresql'):
        raise RuntimeError('PostgreSQL test mode requires the approved hosted database')
    # Search-path startup options require a direct connection, not PgBouncer.
    direct = make_url(base).set(drivername='postgresql+psycopg')
    if direct.host and direct.host.endswith('.neon.tech'):
        direct = direct.set(host=direct.host.replace('-pooler.', '.'))
    address = socket.getaddrinfo(direct.host, direct.port or 5432, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    direct = direct.update_query_dict({'hostaddr': address})
    base = direct.render_as_string(hide_password=False)
    schema = 'pulselite_test_' + secrets.token_hex(8)
    admin = create_engine(base, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(base).update_query_dict({'options': f'-csearch_path={schema}'})
    try:
        yield url.render_as_string(hide_password=False)
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()