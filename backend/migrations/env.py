from alembic import context
from sqlalchemy import create_engine
from app.config import Settings
from app.models import Base

config = context.config
target_metadata = Base.metadata
url = Settings.from_env().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    def run(connection):
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    existing = config.attributes.get('connection')
    if existing is not None:
        run(existing)
    else:
        engine = create_engine(url, hide_parameters=True)
        with engine.connect() as connection:
            run(connection)