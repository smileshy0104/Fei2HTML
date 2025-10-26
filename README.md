Fei2HTML — Hybrid Docx to HTML Converter

Overview
- Converts Feishu/Lark exported .docx (or generic Word .docx) to clean HTML.
- Hybrid strategy: Pandoc mainline for higher fidelity; Mammoth as fallback.
- Uploads images via a pluggable ImageStore, rewrites `img` URLs, returns HTML + asset manifest.
- Provides REST APIs to convert-only or upload+persist results into a DB.

Project Layout
- app/main.py — FastAPI service exposing APIs.
- app/db.py — SQLAlchemy engine/session setup.
- app/models.py — Document model for persistence.
- app/schemas.py — Pydantic response/request models.
- app/converters/pandoc_converter.py — Pandoc-based converter.
- app/converters/mammoth_converter.py — Mammoth-based converter (placeholder).
- app/converters/hybrid.py — Try Pandoc, fallback to Mammoth.
- app/services/image_store.py — ImageStore interface + Local implementation.
- app/services/sanitizer.py — HTML sanitizer and CSS injector.
- app/services/html_postprocess.py — Post-processing (headings/tables/images/lists).
- app/templates/article.css — Base CSS for rendering content.
- scripts/convert_docx.py — CLI helper to convert a .docx file.

APIs
- POST `/convert`
  - Form fields: `file` (.docx), `doc_id` (optional)
  - Returns: `{ html, assets[], engine }`
- POST `/documents/upload`
  - Form fields: `file` (.docx), `doc_id` (optional), `title` (optional), `css_version` (default v1)
  - Action: convert + sanitize + persist into DB (SQLite by default) and copy assets.
  - Returns: `{ id, doc_id, title, engine, source_hash, css_version, html_content, asset_manifest[] }`
- GET `/documents`
  - List last converted documents (id, doc_id, title, engine, source_hash)
- GET `/documents/{id}`
  - Returns full document with HTML and asset manifest

Install
1) Python deps
   pip install -r requirements.txt

2) Pandoc availability (recommended)
   - Install Pandoc locally, OR run via Docker (example):
     docker run --rm -v "$PWD":/data pandoc/core:latest --version
   - The service auto-detects pandoc in PATH; if unavailable, it falls back to Mammoth.

Run service
- uvicorn app.main:app --reload --port 8000

CLI usage
- python scripts/convert_docx.py path/to/file.docx --doc-id mydoc

Configuration
- DB (MySQL recommended):
  - Either set a full URL via `FEI2HTML_DB_URL`, e.g. `mysql+pymysql://root:123456@127.0.0.1:3309/ai_db_agent?charset=utf8mb4`
  - Or set discrete envs (see `.env.example`): `DB_TYPE, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_MAX_CONNECTIONS`
  - Default fallback: `sqlite:///./fei2html.db`
- Image storage: LocalImageStore writes to `public/assets/{doc_id}/...` and returns `/assets/...`.
  Replace with your own implementation (OSS/COS/S3) by implementing `ImageStore` interface.

Overwrite semantics and per-doc assets
- On upload with the same `doc_id`, the service overwrites the DB record and replaces the directory `public/assets/{doc_id}` with newly generated assets (when `overwrite=true`, default).
- Each document’s images are stored under its own directory: `public/assets/{doc_id}/<filename>`.

Security
- Sanitizes HTML via Bleach with a conservative allowlist; adjust in `app/services/sanitizer.py`.
- External links gain rel attributes. Images are constrained with max-width:100%.

Feishu API (optional, future)
- Add a new converter under `app/converters/feishu_api.py` to fetch document blocks or exported HTML, then pass through sanitizer and CSS injector.

Notes
- Complex tables and equations: Pandoc handles better; Mammoth may degrade. For equations, consider MathJax on the front-end.
- DB storage: use MEDIUMTEXT/LONGTEXT for `html_content` and store `asset_manifest` JSON alongside.
