from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .run_models import TunnelRun
from .windstop_models import TunnelControl,WindStopEvent,WindStopRequest,RunAbort
from .calibration_service import locked
from .services import pack,audit

def now():return datetime.now(timezone.utc).isoformat()

def control(s):
    """Serialize 开车/停风/解锁/采样 against a single control row.

    Every writer that can change the wind-stop gate takes this lock first.
    Holding it while reading the active stop, while aborting running tests and
    while opening/writing sampling makes stop-vs-start and stop-vs-sampling
    outcomes linearizable: once a stop commits, no run is still running and no
    further sample write can succeed.
    """
    row=s.scalar(select(TunnelControl).where(TunnelControl.id==1).with_for_update())
    if row:return row
    try:
        with s.begin_nested():
            s.add(TunnelControl(id=1,updated_at=now()));s.flush()
    except IntegrityError:
        pass
    return locked(s,TunnelControl,1)

def active(s):
    return s.scalar(select(WindStopEvent).where(WindStopEvent.state=='active').order_by(WindStopEvent.id.desc()).limit(1))

def aborts(s,stop_id):
    rows=s.execute(select(RunAbort,TunnelRun).join(TunnelRun,TunnelRun.id==RunAbort.run_id).where(RunAbort.stop_id==stop_id).order_by(RunAbort.id)).all()
    return [pack(a)|{'run_code':r.code,'layout_id':r.layout_id,'speed':r.speed,'target_angle':r.target_angle,'started_at':r.started_at,'has_start_snapshot':bool(r.snapshot)} for a,r in rows]

def view(s,e):
    return pack(e)|{'aborted_runs':aborts(s,e.id)}

def stop(s,d,u):
    control(s)
    token=d.request_id
    # Replaying a stop whose response was lost must not create another event —
    # even if that stop has since been released, or a newer stop is active now.
    if token:
        seen=s.get(WindStopRequest,token)
        if seen:return view(s,locked(s,WindStopEvent,seen.stop_id))
    current=active(s)
    if current:
        # A request that arrived while a stop was already in force simply
        # observes it; the token is remembered so retries after that stop ends
        # still map back instead of creating a new event.
        if token:s.add(WindStopRequest(request_id=token,stop_id=current.id))
        s.flush()
        return view(s,current)
    e=WindStopEvent(reason=d.reason,state='active',stopped_by=u.email,stopped_at=now())
    s.add(e);s.flush()
    if token:s.add(WindStopRequest(request_id=token,stop_id=e.id))
    running=list(s.scalars(select(TunnelRun).where(TunnelRun.state=='running').order_by(TunnelRun.id).with_for_update()))
    for r in running:
        r.state='aborted'
        s.add(RunAbort(run_id=r.id,stop_id=e.id,reason=d.reason,aborted_by=u.email,aborted_at=e.stopped_at,prior_state='running'))
    s.flush()
    audit(s,u,'紧急停风封锁，中止运行试验 '+('、'.join(r.code for r in running)or'无')+'；缘由：'+e.reason)
    return view(s,e)

def release(s,id,d,u):
    control(s)
    e=locked(s,WindStopEvent,id)
    # Replaying an already successful release returns the same outcome without
    # a second audit line, even if a newer stop has since begun.
    if e.state=='released':return view(s,e)
    current=active(s)
    # A late/stale release that was never applied must never clear a newer stop.
    if current and current.id!=e.id:raise HTTPException(409,'该解锁针对的停风已结束，不能解除后一次封锁')
    if not current:raise HTTPException(409,'当前没有待解除的停风封锁')
    e.state='released';e.released_by=u.email;e.released_at=now();e.release_note=d.release_note
    audit(s,u,'负责人复检解锁停风 '+str(e.id)+'，仅放行新试验；中止试验不恢复')
    return view(s,e)
