from sqlalchemy import text
from .db import Base,engine
# Import every model module so create_all sees all tables, including the new
# wind-stop tables, when the app starts on an existing database.
from . import models,run_models,calibration_models,mount_models,acquisition_models,delivery_models,windstop_models  # noqa: F401

EXPECTED="state in ('planned','running','completed','aborted')"

def upgrade():
    """Create new tables and widen the historical run-state constraint.

    Historical runs, their start snapshots and sampled data are untouched; the
    only schema change is that the allowed state set gains the terminal value
    'aborted'. Existing rows are never rewritten.
    """
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Singleton gate row; start/stop/release take FOR UPDATE on it.
        conn.execute(text(
            "INSERT INTO tunnel_controls (id, updated_at) SELECT 1, NULL "
            "WHERE NOT EXISTS (SELECT 1 FROM tunnel_controls WHERE id=1)"
        ))
    if engine.dialect.name!='mysql':return
    with engine.begin() as conn:
        found=conn.execute(text(
            "SELECT c.CONSTRAINT_NAME,cc.CHECK_CLAUSE FROM information_schema.TABLE_CONSTRAINTS c "
            "JOIN information_schema.CHECK_CONSTRAINTS cc "
            "ON cc.CONSTRAINT_SCHEMA=c.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=c.CONSTRAINT_NAME "
            "WHERE c.TABLE_SCHEMA=DATABASE() AND c.TABLE_NAME='tunnel_runs' AND c.CONSTRAINT_TYPE='CHECK'"
        )).all()
        if any('aborted' in (clause or '').lower() for _,clause in found):return
        for name,clause in found:
            if 'state' in (clause or '').lower():
                conn.execute(text(f'ALTER TABLE tunnel_runs DROP CHECK `{name}`'))
        conn.execute(text('ALTER TABLE tunnel_runs ADD CONSTRAINT ck_tunnel_runs_state CHECK ('+EXPECTED+')'))
