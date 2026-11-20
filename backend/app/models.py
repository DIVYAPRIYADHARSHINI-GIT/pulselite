from datetime import datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Site(Base):
    __tablename__ = 'sites'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(80))
    origin: Mapped[str] = mapped_column(String(255))
    site_key: Mapped[str] = mapped_column(String(40), unique=True)
    respect_dnt: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id', ondelete='CASCADE'))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    visitor_hash: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(256))
    referrer: Mapped[str] = mapped_column(String(253))
    source: Mapped[str] = mapped_column(String(24))
    device: Mapped[str] = mapped_column(String(10))
    browser: Mapped[str] = mapped_column(String(16))
    country: Mapped[str] = mapped_column(String(2))
    __table_args__ = (
        Index('ix_events_site_time', 'site_id', 'occurred_at'),
        Index('ix_events_site_path_time', 'site_id', 'path', 'occurred_at'),
        Index('ix_events_site_visitor_time', 'site_id', 'visitor_hash', 'occurred_at'),
    )


class DailySalt(Base):
    __tablename__ = 'daily_salts'
    day: Mapped[datetime] = mapped_column(Date, primary_key=True)
    salt: Mapped[bytes] = mapped_column(LargeBinary(32))


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    count: Mapped[int] = mapped_column(Integer)