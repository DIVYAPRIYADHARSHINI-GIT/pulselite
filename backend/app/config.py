import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = 'sqlite:///./pulselite.db'
    dashboard_origin: str = 'http://localhost:5173'
    production: bool = False
    trusted_vercel: bool = False
    event_limit: int = 120
    auth_limit: int = 20
    retention_days: int = 90

    @classmethod
    def from_env(cls):
        url = os.getenv('DATABASE_URL', cls.database_url)
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
        result = cls(
            database_url=url,
            dashboard_origin=os.getenv('DASHBOARD_ORIGIN', cls.dashboard_origin).rstrip('/'),
            production=os.getenv('PULSELITE_ENV') == 'production',
            trusted_vercel=os.getenv('VERCEL') == '1',
            event_limit=int(os.getenv('EVENT_RATE_LIMIT', '120')),
            auth_limit=int(os.getenv('AUTH_RATE_LIMIT', '20')),
            retention_days=int(os.getenv('RETENTION_DAYS', '90')),
        )
        if not 1 <= result.retention_days <= 730 or result.event_limit < 1:
            raise RuntimeError('Invalid retention/rate configuration')
        if result.production and (not url.startswith('postgresql') or not result.dashboard_origin.startswith('https://')):
            raise RuntimeError('Production requires PostgreSQL and an HTTPS dashboard origin')
        return result