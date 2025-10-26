from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.mysql import JSON as MYSQL_JSON
from sqlalchemy import inspect

from app.db import Base, engine


def _json_type():
    # Use native JSON if available, otherwise fallback to Text containing JSON string
    dialect = inspect(engine).dialect.name
    if dialect == "postgresql":
        return PG_JSONB
    if dialect == "sqlite":
        return SQLITE_JSON
    if dialect == "mysql":
        return MYSQL_JSON
    return Text


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(255), index=True, nullable=True, unique=True)
    title = Column(String(512), nullable=True)
    source_hash = Column(String(128), index=True, nullable=True)
    engine = Column(String(64), nullable=False)
    css_version = Column(String(32), nullable=True)
    html_content = Column(Text, nullable=False)
    asset_manifest = Column(_json_type(), nullable=True)
