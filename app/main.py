from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import tempfile
import shutil
import hashlib

from app.db import SessionLocal, init_db
from app.models import Document
from app.schemas import ConvertResponse, DocumentCreateResponse, DocumentItem, DocumentDetail, AssetItem
from app.converters.hybrid import HybridConverter, ConversionError
from app.services.image_store import LocalImageStore
from app.services.sanitizer import sanitize_and_inject_css
from app.services.preview import generate_preview_html
from app.services.artifacts import write_asset_manifest


app = FastAPI(title="Fei2HTML Hybrid Converter")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/convert", response_model=ConvertResponse)
async def convert(file: UploadFile = File(...), doc_id: Optional[str] = Form(None)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        image_store = LocalImageStore(base_dir=Path("public/assets"), base_url="/assets")
        converter = HybridConverter(image_store=image_store)

        try:
            result = converter.convert_docx(tmp_path, doc_id=doc_id)
        except ConversionError as e:
            raise HTTPException(status_code=500, detail=str(e))

        html_clean = sanitize_and_inject_css(result.html)
        return ConvertResponse(html=html_clean, assets=[AssetItem(**a) for a in result.assets], engine=result.engine)


@app.post("/documents/upload", response_model=DocumentCreateResponse)
async def upload_and_save(
    file: UploadFile = File(...),
    doc_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    css_version: Optional[str] = Form("v1"),
    overwrite: Optional[bool] = Form(True),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        with tmp_path.open("wb") as f:
            data = await file.read()
            f.write(data)
        # Compute source hash
        source_hash = hashlib.sha256(data).hexdigest()

        image_store = LocalImageStore(base_dir=Path("public/assets"), base_url="/assets")

        # Overwrite handling: if same doc_id exists, clear its asset directory and update the row
        logical_id = doc_id or Path(file.filename).stem
        if overwrite and logical_id:
            existing = db.query(Document).filter(Document.doc_id == logical_id).first()
            if existing:
                # Clear assets directory for this doc
                assets_dir = Path("public/assets") / logical_id
                try:
                    if assets_dir.exists():
                        import shutil as _shutil
                        _shutil.rmtree(assets_dir)
                except Exception:
                    pass

        converter = HybridConverter(image_store=image_store)

        try:
            result = converter.convert_docx(tmp_path, doc_id=doc_id)
        except ConversionError as e:
            raise HTTPException(status_code=500, detail=str(e))

        html_clean = sanitize_and_inject_css(result.html)
        preview_info = generate_preview_html(logical_id, title or logical_id, html_clean)
        manifest_path = write_asset_manifest(logical_id, result.engine, result.assets)

        # Upsert by doc_id if provided or derived
        doc = db.query(Document).filter(Document.doc_id == logical_id).first() if logical_id else None
        if doc:
            doc.title = title
            doc.source_hash = source_hash
            doc.engine = result.engine
            doc.css_version = css_version
            doc.html_content = html_clean
            doc.asset_manifest = result.assets
            db.add(doc)
            db.commit()
            db.refresh(doc)
        else:
            doc = Document(
                doc_id=logical_id,
                title=title,
                source_hash=source_hash,
                engine=result.engine,
                css_version=css_version,
                html_content=html_clean,
                asset_manifest=result.assets,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

        return DocumentCreateResponse.model_validate({
            "id": doc.id,
            "doc_id": doc.doc_id,
            "title": doc.title,
            "engine": doc.engine,
            "source_hash": doc.source_hash,
            "css_version": doc.css_version,
            "html_content": doc.html_content,
            "asset_manifest": doc.asset_manifest or [],
            "preview_path": preview_info.path if preview_info else None,
            "preview_url": preview_info.url if preview_info else None,
            "asset_manifest_path": manifest_path,
        })


@app.get("/documents", response_model=list[DocumentItem])
def list_documents(db: Session = Depends(get_db)):
    items = db.query(Document.id, Document.doc_id, Document.title, Document.engine, Document.source_hash).order_by(Document.id.desc()).all()
    return [DocumentItem(id=i[0], doc_id=i[1], title=i[2], engine=i[3], source_hash=i[4]) for i in items]


@app.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    preview_file = None
    preview_url = None
    asset_manifest_path = None
    if doc.doc_id:
        preview_candidate = Path("out") / f"{doc.doc_id}_preview.html"
        if preview_candidate.exists():
            preview_file = str(preview_candidate)
            preview_url = f"/out/{doc.doc_id}_preview.html"
        manifest_candidate = Path("out") / f"{doc.doc_id}.assets.json"
        if manifest_candidate.exists():
            asset_manifest_path = str(manifest_candidate)
    return DocumentDetail.model_validate({
        "id": doc.id,
        "doc_id": doc.doc_id,
        "title": doc.title,
        "engine": doc.engine,
        "source_hash": doc.source_hash,
        "html_content": doc.html_content,
        "asset_manifest": doc.asset_manifest or [],
        "preview_path": preview_file,
        "preview_url": preview_url,
        "asset_manifest_path": asset_manifest_path,
    })
