from fastapi import APIRouter,Depends
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .calibration_models import CalibrationCertificate
from .run_models import TunnelRun
from .windstop_models import WindStopEvent
from .readiness_schemas import CertificateInput,RunInput,FinishInput
from .windstop_schemas import WindStopInput,WindReleaseInput
from .services import pack
from . import calibration_service as calibration,runs_service as runs,windstop_service as windstop
router=APIRouter()
@router.get('/calibration-certificates')
def certificates(s=Depends(db_session),u=Depends(current)):return [calibration.view(s,x) for x in s.scalars(select(CalibrationCertificate).order_by(CalibrationCertificate.id.desc()))]
@router.post('/calibration-certificates')
def create_certificate(d:CertificateInput,s=Depends(db_session),u=Depends(writers)):
    x=calibration.create(s,d,u);s.commit();return x
@router.put('/calibration-certificates/{id}')
def revise_certificate(id:int,d:CertificateInput,s=Depends(db_session),u=Depends(writers)):
    x=calibration.revise(s,id,d,u);s.commit();return x
@router.post('/calibration-certificates/{id}/issue')
def issue(id:int,s=Depends(db_session),u=Depends(admin)):
    x=calibration.issue(s,id,u);s.commit();return x
@router.get('/tunnel-runs')
def list_runs(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(TunnelRun).order_by(TunnelRun.id.desc()))]
@router.get('/wind-stops')
def list_stops(s=Depends(db_session),u=Depends(current)):return [windstop.view(s,x) for x in s.scalars(select(WindStopEvent).order_by(WindStopEvent.id.desc()))]
@router.get('/wind-stops/active')
def active_stop(s=Depends(db_session),u=Depends(current)):
    e=windstop.active(s)
    return windstop.view(s,e) if e else None
@router.post('/wind-stops')
def emergency_stop(d:WindStopInput,s=Depends(db_session),u=Depends(writers)):
    # 停风 is a safety action: any engineer or the responsible lead may trip it.
    # A client retry token (optional) deduplicates replays after a lost response;
    # without one, each call is a fresh request.
    x=windstop.stop(s,d,u);s.commit();return x
@router.post('/wind-stops/{id}/release')
def release_stop(id:int,d:WindReleaseInput,s=Depends(db_session),u=Depends(admin)):
    x=windstop.release(s,id,d,u);s.commit();return x
@router.post('/tunnel-runs')
def create_run(d:RunInput,s=Depends(db_session),u=Depends(writers)):
    x=runs.create(s,d,u);s.commit();return x
@router.put('/tunnel-runs/{id}')
def revise_run(id:int,d:RunInput,s=Depends(db_session),u=Depends(writers)):
    x=runs.revise(s,id,d,u);s.commit();return x
@router.post('/tunnel-runs/{id}/start')
def start(id:int,s=Depends(db_session),u=Depends(admin)):
    x=runs.start(s,id,u);s.commit();return x
@router.post('/tunnel-runs/{id}/complete')
def complete(id:int,d:FinishInput,s=Depends(db_session),u=Depends(writers)):
    x=runs.finish(s,id,d,u);s.commit();return x
