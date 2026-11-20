"""Run from backend: python -m scripts.cleanup. Schedule daily in production."""
from datetime import datetime, timedelta
from sqlalchemy import delete
from app.main import app
from app.models import DailySalt, Event, LoginSession, RateBucket


def cleanup(db, retention_days):
    now = datetime.utcnow()
    events = db.execute(delete(Event).where(Event.occurred_at < now - timedelta(days=retention_days))).rowcount
    db.execute(delete(LoginSession).where(LoginSession.expires_at < now))
    db.execute(delete(DailySalt).where(DailySalt.day < now.date()))
    db.execute(delete(RateBucket).where(RateBucket.window < int(now.timestamp()) // 60 - 10))
    db.commit()
    return events


if __name__ == '__main__':
    with app.state.Session() as db:
        count = cleanup(db, app.state.settings.retention_days)
        print(f'Removed {count} expired events; expired operational rows also removed.')