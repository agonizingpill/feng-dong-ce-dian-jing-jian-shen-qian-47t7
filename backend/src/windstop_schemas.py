from pydantic import BaseModel,Field,field_validator

class WindStopInput(BaseModel):
    reason:str=Field(max_length=2000)
    # Optional client retry token (or Idempotency-Key header). Replaying the
    # same token never creates a second stop event, even if the first response
    # was lost and the stop has since been released or superseded.
    request_id:str|None=Field(default=None,max_length=64)
    @field_validator('reason')
    @classmethod
    def reason_not_blank(cls,v):
        v=v.strip()
        if len(v)<8:raise ValueError('紧急停风须注明至少8字缘由')
        return v
    @field_validator('request_id')
    @classmethod
    def token_not_blank(cls,v):
        if v is None or not v.strip():return None
        v=v.strip()
        if len(v)<8:raise ValueError('重试标识至少8字')
        return v
class WindReleaseInput(BaseModel):
    release_note:str=Field(max_length=2000)
    recheck_confirmed:bool=False
    @field_validator('release_note')
    @classmethod
    def note_not_blank(cls,v):
        v=v.strip()
        if len(v)<8:raise ValueError('解锁须注明至少8字复检确认说明')
        return v
    @field_validator('recheck_confirmed')
    @classmethod
    def must_confirm(cls,v):
        if v is not True:raise ValueError('须由负责人复检确认后才可解锁')
        return v
