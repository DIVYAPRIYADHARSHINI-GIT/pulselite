from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from sqlalchemy import Date, cast, distinct, func, select
from .models import Event

DIMENSIONS = ('path', 'device', 'browser', 'country', 'referrer', 'source')


def date_range(start, end):
    if start > end or (end - start).days > 365 or end > datetime.utcnow().date():
        raise HTTPException(422, 'Use a valid UTC range of at most 366 days, not in the future')
    return datetime.combine(start, time()), datetime.combine(end + timedelta(days=1), time())


def aggregate(db, site_id, start, end, filters=None):
    low, high = date_range(start, end)
    filters = filters or {}
    base = [Event.site_id == site_id]
    for name, value in filters.items():
        if name in DIMENSIONS and value is not None:
            if name == 'referrer' and value == 'Direct':
                value = ''
            base.append(getattr(Event, name) == value)
    current = base + [Event.occurred_at >= low, Event.occurred_at < high]
    prior = base + [Event.occurred_at >= low - (high - low), Event.occurred_at < low]

    def counts(where):
        row = db.execute(select(func.count(Event.id), func.count(distinct(Event.visitor_hash))).where(*where)).one()
        return {'pageviews': row[0], 'visitors': row[1]}

    result = counts(current)
    result['previous'] = counts(prior)
    result['live'] = counts(base + [Event.occurred_at >= datetime.utcnow() - timedelta(minutes=5), Event.occurred_at <= datetime.utcnow()])['visitors']
    bucket = cast(Event.occurred_at, Date) if db.bind.dialect.name == 'postgresql' else func.date(Event.occurred_at)
    rows = db.execute(select(bucket, func.count(Event.id), func.count(distinct(Event.visitor_hash))).where(*current).group_by(bucket).order_by(bucket)).all()
    indexed = {str(r[0]): {'date': str(r[0]), 'pageviews': r[1], 'visitors': r[2]} for r in rows}
    result['series'] = [indexed.get(str(start + timedelta(days=i)), {'date': str(start + timedelta(days=i)), 'pageviews': 0, 'visitors': 0}) for i in range((end - start).days + 1)]
    for name in DIMENSIONS:
        col = getattr(Event, name)
        rows = db.execute(select(col, func.count(Event.id).label('n'), func.count(distinct(Event.visitor_hash))).where(*current).group_by(col).order_by(func.count(Event.id).desc(), col).limit(20)).all()
        result[name] = [{'name': r[0] or 'Direct', 'pageviews': r[1], 'visitors': r[2]} for r in rows]
    result['start'] = str(start)
    result['end'] = str(end)
    result['visitor_definition'] = 'Daily uniques, summed across UTC days; not cross-day unique people.'
    return result