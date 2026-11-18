import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
_url=os.environ['DATABASE_URL']
# MySQL must run READ COMMITTED so lock-waiting reads see the latest committed
# samples; SQLite (local tests only) does not accept that isolation name.
_engine_kw={'pool_pre_ping':True}
if _url.startswith('mysql'):_engine_kw['isolation_level']='READ COMMITTED'
engine = create_engine(_url, **_engine_kw)
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
def db_session():
    with Session() as s:
        yield s
