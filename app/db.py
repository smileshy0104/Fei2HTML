from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os


def _build_db_url() -> str:
    # Prefer explicit URL env
    url = os.getenv("FEI2HTML_DB_URL")
    if url:
        return url

    # Or compose from discrete DB_* envs
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    if db_type == "mysql":
        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "fei2html")
        user = os.getenv("DB_USER", "root")
        pwd = os.getenv("DB_PASSWORD", "")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"
    # default sqlite
    return "sqlite:///./fei2html.db"


DB_URL = _build_db_url()


class Base(DeclarativeBase):
    pass


pool_size = None
max_conn = os.getenv("DB_MAX_CONNECTIONS")
try:
    if max_conn:
        pool_size = max(1, int(max_conn))
except Exception:
    pool_size = None

engine_kwargs = {}
if DB_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Reasonable MySQL defaults
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # 30 minutes
    })
    if pool_size:
        engine_kwargs.update({
            "pool_size": min(pool_size, 50),
            "max_overflow": 10,
        })

engine = create_engine(DB_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    from app import models  # noqa: F401 ensure models are imported
    Base.metadata.create_all(bind=engine)
