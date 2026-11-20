"""Idempotent synthetic demo; no usable owner password is saved or printed."""
import hashlib
import random
import secrets
from datetime import datetime, timedelta
from sqlalchemy import delete, select
from app.main import app, PASSWORDS
from app.models import Event, Site, User


def seed():
    rng = random.Random(407)
    with app.state.Session() as db:
        owner = db.scalar(select(User).where(User.email == 'demo-owner@pulselite.test'))
        if not owner:
            owner = User(email='demo-owner@pulselite.test', password_hash=PASSWORDS.hash(secrets.token_urlsafe(48)))
            db.add(owner)
            db.flush()
        site = db.scalar(select(Site).where(Site.owner_id == owner.id, Site.is_demo.is_(True)))
        if not site:
            site = Site(owner_id=owner.id, name='Form & Field — synthetic demo', origin='https://demo.pulselite.test', site_key=secrets.token_urlsafe(24), is_demo=True)
            db.add(site)
            db.flush()
        db.execute(delete(Event).where(Event.site_id == site.id))
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        total = 0
        for i in range(30):
            day = today - timedelta(days=29-i)
            for j in range(rng.randint(85, 145) + i * 5):
                visitor = j // rng.choice([1, 2, 3])
                ref, source = rng.choices([('', 'Direct'), ('google.com', 'Search'), ('instagram.com', 'Social'), ('designweekly.test', 'Referral')], [42, 34, 15, 9])[0]
                when = day + timedelta(seconds=rng.randint(0, 86399))
                if when > datetime.utcnow():
                    when = datetime.utcnow() - timedelta(seconds=rng.randint(1, 3600))
                db.add(Event(site_id=site.id, occurred_at=when, visitor_hash=hashlib.sha256(f'synthetic:{day}:{visitor}'.encode()).hexdigest(), path=rng.choices(['/', '/journal', '/work', '/about', '/contact'], [40, 26, 20, 10, 4])[0], referrer=ref, source=source, device=rng.choices(['desktop', 'mobile', 'tablet'], [53, 41, 6])[0], browser=rng.choices(['Chrome', 'Safari', 'Firefox', 'Edge'], [58, 25, 11, 6])[0], country=rng.choices(['US', 'IN', 'GB', 'DE', 'CA', 'AU', 'ZZ'], [29, 24, 17, 11, 8, 6, 5])[0]))
                total += 1
        db.commit()
        print(f'Seeded {total} synthetic events across 30 UTC days. Demo is explicitly labeled.')


if __name__ == '__main__':
    seed()