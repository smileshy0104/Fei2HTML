from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class AssetItem(BaseModel):
    name: str
    url: str


class ConvertResponse(BaseModel):
    html: str
    assets: List[AssetItem]
    engine: str


class DocumentCreateResponse(BaseModel):
    id: int
    doc_id: Optional[str] = None
    title: Optional[str] = None
    engine: str
    source_hash: Optional[str] = None
    css_version: Optional[str] = None
    html: str = Field(alias="html_content")
    assets: List[AssetItem] = Field(default_factory=list, alias="asset_manifest")


class DocumentItem(BaseModel):
    id: int
    doc_id: Optional[str] = None
    title: Optional[str] = None
    engine: str
    source_hash: Optional[str] = None


class DocumentDetail(DocumentItem):
    html: str = Field(alias="html_content")
    assets: List[AssetItem] = Field(default_factory=list, alias="asset_manifest")

