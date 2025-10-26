# Fei2HTML 部署与配置指南

## 1. 环境依赖

- **操作系统**：macOS / Linux（推荐），Windows 需自备 Pandoc 与 MySQL。
- **Python**：3.9+（建议使用 Anaconda/Miniconda）。
- **Pandoc**：用于 `.docx` → HTML 转换。
- **MySQL**：默认数据库；测试阶段可改用 SQLite。

### 1.1 安装 Python 依赖

```
pip install -r requirements.txt
# 或使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

主要依赖：FastAPI/uvicorn、SQLAlchemy/PyMySQL、python-dotenv、bleach、python-multipart、mammoth、pydantic。

### 1.2 安装 Pandoc

```
# macOS (Homebrew)
brew install pandoc

# Conda
conda install -c conda-forge pandoc
```

验证：`pandoc --version`

### 1.3 数据库

示例（MySQL）：

```
CREATE DATABASE ai_db_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

首次启动 FastAPI 会自动建表；如需手动建表：

```
USE ai_db_agent;
CREATE TABLE documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  doc_id VARCHAR(255) UNIQUE,
  title VARCHAR(512) NULL,
  source_hash VARCHAR(128) NULL,
  engine VARCHAR(64) NOT NULL,
  css_version VARCHAR(32) NULL,
  html_content LONGTEXT NOT NULL,
  asset_manifest JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_source_hash (source_hash)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. 环境变量

支持两种方式：
1. 直接 `FEI2HTML_DB_URL`
2. 使用 `DB_*` 离散变量（推荐搭配 `.env`）

示例 `.env`：

```
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3309
DB_NAME=ai_db_agent
DB_USER=root
DB_PASSWORD=123456
DB_MAX_CONNECTIONS=20

# 可选：直接指定 URL
# FEI2HTML_DB_URL=mysql+pymysql://root:123456@127.0.0.1:3309/ai_db_agent?charset=utf8mb4

# Redis 预留（暂未启用）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

加载 `.env`：

```
export $(grep -v '^#' .env | xargs)
```

## 3. 启动流程

### 3.1 后端（FastAPI）

```
uvicorn app.main:app --reload --port 8000
```

- Swagger：`http://localhost:8000/docs`
- 核心接口：`POST /convert`、`POST /documents/upload`、`GET /documents`、`GET /documents/{id}`

### 3.2 静态预览

```
python3 -m http.server 8000
# 访问
http://localhost:8000/out/<doc_id>_preview.html
```

## 4. 接口说明

### 4.1 `POST /convert`
- 仅转换，不写库；返回 `{ html, assets[], engine }`

### 4.2 `POST /documents/upload`
- 转换 + 图片提取 + HTML 清洗 + 写库 + 生成预览
- 表单字段：`file`、`doc_id`、`title`、`css_version`、`overwrite`
- 返回字段含 `preview_path`、`preview_url`、`asset_manifest_path`

### 4.3 `GET /documents`
- 文档列表

### 4.4 `GET /documents/{id}`
- 文档详情（HTML、资源清单、预览路径）

## 5. 产物目录

- `public/assets/<doc_id>/`：图片资源
- `out/<doc_id>_preview.html`：完整预览页面
- `out/<doc_id>.assets.json`：图片清单
- DB：`documents` 表

CLI 转换示例：
```
python scripts/convert_docx.py your.docx --doc-id your-id --out-html out/your.html
```

## 6. 部署建议

1. 容器化：打包 Python、Pandoc、依赖；用 Gunicorn + Uvicorn Workers。
2. 静态资源：映射 `public/assets/`、`out/` 至 Nginx 或对象存储；如需自定义图床，实现自定义 `ImageStore`。
3. 环境变量：使用 `.env`、K8s Secret、Vault 等。
4. 日志监控：接入 APM 或自定义中间件记录耗时。
5. 安全：接口鉴权（Token/OAuth），限制上传大小，使用 HTTPS。

## 7. 常见问题

- 图片不显示：确保通过 HTTP 访问，且 `/assets/<doc_id>/` 可达。
- 颜色未保留：Word 中需显式设置字体颜色。
- 列表未识别：文档需使用 Word 原生“项目符号/编号”。
- 标题层级：建议使用 Word 标题样式；否则系统会把整行粗体段落转为 `h2`。

## 8. 检查清单

- [ ] Pandoc 安装成功（`pandoc --version`）
- [ ] MySQL 可访问
- [ ] `pip install -r requirements.txt` 完成
- [ ] `.env` 配置正确
- [ ] FastAPI 启动无报错
- [ ] `POST /documents/upload` 返回 200 且生成预览/JSON
- [ ] 静态服务可访问 `out/<doc_id>_preview.html`
