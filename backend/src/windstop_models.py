from sqlalchemy import String,Text,ForeignKey,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base

class TunnelControl(Base):
    """Singleton row used to serialize start/stop/release decisions.

    Locking this row before reading the active wind-stop makes 开车 and
    停风 mutually exclusive even under concurrent requests.
    """
    __tablename__='tunnel_controls'
    id:Mapped[int]=mapped_column(primary_key=True)
    updated_at:Mapped[str|None]=mapped_column(String(40),nullable=True)

class WindStopEvent(Base):
    __tablename__='wind_stop_events'
    __table_args__=(CheckConstraint("state in ('active','released')"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    reason:Mapped[str]=mapped_column(Text)
    state:Mapped[str]=mapped_column(String(20),default='active')
    stopped_by:Mapped[str]=mapped_column(String(100))
    stopped_at:Mapped[str]=mapped_column(String(40))
    released_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
    released_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    release_note:Mapped[str]=mapped_column(Text,default='')

class WindStopRequest(Base):
    """Idempotency key for a 停风 request.

    A retried request (same client token) maps back to the event it produced,
    and a request that arrived while a stop was already active maps to that
    stop, so a later retry after the stop was released still cannot create a
    second event.
    """
    __tablename__='wind_stop_requests'
    request_id:Mapped[str]=mapped_column(String(64),primary_key=True)
    stop_id:Mapped[int]=mapped_column(ForeignKey('wind_stop_events.id'))

class RunAbort(Base):
    __tablename__='run_aborts'
    id:Mapped[int]=mapped_column(primary_key=True)
    run_id:Mapped[int]=mapped_column(ForeignKey('tunnel_runs.id'),unique=True)
    stop_id:Mapped[int]=mapped_column(ForeignKey('wind_stop_events.id'))
    reason:Mapped[str]=mapped_column(Text)
    aborted_by:Mapped[str]=mapped_column(String(100))
    aborted_at:Mapped[str]=mapped_column(String(40))
    prior_state:Mapped[str]=mapped_column(String(20),default='running')
