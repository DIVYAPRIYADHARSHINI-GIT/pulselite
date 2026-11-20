"""Initial PulseLite schema, frozen independently of application models."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users', sa.Column('id', sa.Integer, primary_key=True), sa.Column('email', sa.String(254), nullable=False, unique=True), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('created_at', sa.DateTime, nullable=False))
    op.create_table('sessions', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('expires_at', sa.DateTime, nullable=False))
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])
    op.create_table('sites', sa.Column('id', sa.Integer, primary_key=True), sa.Column('owner_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('name', sa.String(80), nullable=False), sa.Column('origin', sa.String(255), nullable=False), sa.Column('site_key', sa.String(40), nullable=False, unique=True), sa.Column('respect_dnt', sa.Boolean, nullable=False), sa.Column('is_demo', sa.Boolean, nullable=False), sa.Column('created_at', sa.DateTime, nullable=False))
    op.create_index('ix_sites_owner_id', 'sites', ['owner_id'])
    op.create_table('events', sa.Column('id', sa.Integer, primary_key=True), sa.Column('site_id', sa.Integer, sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False), sa.Column('occurred_at', sa.DateTime, nullable=False), sa.Column('visitor_hash', sa.String(64), nullable=False), sa.Column('path', sa.String(256), nullable=False), sa.Column('referrer', sa.String(253), nullable=False), sa.Column('source', sa.String(24), nullable=False), sa.Column('device', sa.String(10), nullable=False), sa.Column('browser', sa.String(16), nullable=False), sa.Column('country', sa.String(2), nullable=False))
    for name, columns in [('ix_events_occurred_at', ['occurred_at']), ('ix_events_site_time', ['site_id', 'occurred_at']), ('ix_events_site_path_time', ['site_id', 'path', 'occurred_at']), ('ix_events_site_visitor_time', ['site_id', 'visitor_hash', 'occurred_at'])]:
        op.create_index(name, 'events', columns)
    op.create_table('daily_salts', sa.Column('day', sa.Date, primary_key=True), sa.Column('salt', sa.LargeBinary(32), nullable=False))
    op.create_table('rate_buckets', sa.Column('key', sa.String(64), primary_key=True), sa.Column('window', sa.Integer, primary_key=True), sa.Column('count', sa.Integer, nullable=False))
    op.create_index('ix_rate_buckets_window', 'rate_buckets', ['window'])


def downgrade():
    for name in ['rate_buckets', 'daily_salts', 'events', 'sites', 'sessions', 'users']:
        op.drop_table(name)