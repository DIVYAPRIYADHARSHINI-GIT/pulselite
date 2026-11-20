"""Delete only labelled local Chrome-test rows, never a hosted database."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.main import create_app
from app.config import Settings
from app.models import Event, LoginSession, Site, User
from sqlalchemy import delete, select, func

root=Path(__file__).resolve().parents[1]
app=create_app(Settings(database_url='sqlite:///'+str(root/'backend/pulselite.db')))
with app.state.Session() as db:
    users=db.scalars(select(User).where(User.email.like('chrome-test-%@pulselite.test'))).all()
    ids=[u.id for u in users]
    sites=db.scalars(select(Site).where(Site.owner_id.in_(ids))).all()
    if any(not s.name.startswith('CHROME TEST') for s in sites):
        raise RuntimeError('Refusing cleanup: unexpected site owned by a test account')
    site_ids=[s.id for s in sites]
    event_count=db.scalar(select(func.count()).select_from(Event).where(Event.site_id.in_(site_ids)))
    record={'database':'local SQLite only','accounts':[u.email for u in users],'site_ids':site_ids,'events_deleted':event_count,'accounts_deleted':len(users),'sites_deleted':len(sites),'hosted_database_touched':False}
    db.execute(delete(Event).where(Event.site_id.in_(site_ids)))
    db.execute(delete(Site).where(Site.id.in_(site_ids)))
    db.execute(delete(LoginSession).where(LoginSession.user_id.in_(ids)))
    db.execute(delete(User).where(User.id.in_(ids)))
    db.commit()
    (root/'reports/local-test-cleanup.json').write_text(json.dumps(record,indent=2))
    print(f'Deleted {len(users)} labelled local test accounts, {len(sites)} test sites and {event_count} events. Synthetic demo retained. No hosted database touched.')