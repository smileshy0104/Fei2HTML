# 飞书/Word → HTML 转换混合方案（Pandoc 主线 + Mammoth 回退）

## 1. 背景与目标
- 背景：当前从飞书/Word 拷贝到 CMS 富文本编辑器存在样式错乱、图片适配差、操作耗时高的问题。
- 目标：上传 `.docx` 后自动生成高保真 HTML 片段（含图片/表格/链接等），统一样式并存库，前端稳定渲染；在高保真与实现成本之间取得平衡。
- 关键指标：
  - 上传耗时 ≤ 10 分钟/篇；
  - 样式还原度 ≥ 80–90%；
  - 失败率 ≤ 1%；
  - 支持批量与并发转换（常见 10–50MB 文档）。

## 2. 策略与技术选型
- 混合策略：
  - 主线：Pandoc 将 `.docx` 转为 HTML5（可包含 MathML/支持脚注/表格更稳）。
  - 回退：Mammoth 轻量转换，Pandoc 不可用或失败时兜底。
  - 可选增强：后续接入飞书 API（导出 HTML/块结构），进一步提升还原与增量更新能力。
- 依赖/组件：
  - 转换：Pandoc CLI（容器化或本地安装）、Mammoth（Python 库）。
  - 图片：抽象 ImageStore，接入 OSS/COS/S3/本地静态目录；支持重试与幂等。
  - 清洗：Bleach（后端）或 DOMPurify（前端）白名单清洗，避免 XSS。
  - 样式：统一 CSS 模板，保证版心与基础排版一致（图片自适应、表格横向滚动）。

## 3. 整体架构
- 形态：服务化微服务 `POST /convert`，返回 `html + assets + engine`。
- 关键模块：
  1) Upload 接收器：接收 `.docx`，写入临时目录。
  2) Converter（Hybrid）：优先 Pandoc，失败则 Mammoth。
  3) Media 提取与上传：解析文档中的图片/媒体，上传到图床，返回稳定 URL。
  4) HTML 整形：重写图片引用、补充语义属性、标题锚点、外链属性。
  5) 清洗与注入样式：白名单清洗，包裹统一容器类并注入/关联 CSS。
  6) 存储与返回：可落库（可选），或直接返回前端预览与保存。

## 4. 数据流与时序（文字版）
1) 前端上传 `.docx` → 后端保存临时文件。
2) Converter 调用 Pandoc：
   - `--extract-media`/容器卷导出媒体到临时目录；
   - 解析出 HTML5（可选 `--mathjax`）。
3) 若 Pandoc 失败，调用 Mammoth：
   - 自定义 image handler 输出临时图片文件。
4) Media 模块并发上传图片 → 返回新 URL；在 HTML 中替换引用。
5) HTML 整形与清洗：添加标题锚点、外链 rel 属性、代码块类名等；Bleach 白名单清洗。
6) 注入统一 CSS 类前缀与基础样式 → 输出 HTML 片段。
7) 返回 JSON（`html, assets, engine`），或持久化存库并返回记录 ID。

## 5. 模块设计
- Converter 接口：
  - 输入：`docx_path`, `doc_id`（用于命名）、可选配置。
  - 输出：`html`、`assets`（[{name, url, hash}]）、`engine`。
  - 错误：抛出 `ConversionError`，由 Hybrid 捕获并回退。
- PandocConverter：
  - 探测 pandoc 是否可用；构造参数（`--from docx --to html5`）。
  - 提取媒体目录，收集图片路径映射。
  - 支持 `--mathjax`（前端用 MathJax 渲染公式）。
- MammothConverter：
  - 使用 style map 提高语义化（heading/list/blockquote/code）。
  - 自定义 image handler 将图片保存至临时目录并记录信息。
- ImageStore：
  - 接口：`save(local_path, dest_path)` → `url`。
  - 默认：本地 `public/assets/{doc_id}/...` 返回 `/assets/...`；可替换为 S3/OSS/COS 实现。
  - 命名：`{doc_id}/{revision_or_hash}/{seq}.{ext}`，避免冲突并支持幂等。
- Sanitizer & CSS：
  - Bleach 白名单：保留 p/h1–h6/ul/ol/li/a/img/table/thead/tbody/tr/th/td/pre/code/blockquote 等。
  - 外链安全：`rel="noopener noreferrer"`，可选 `target="_blank"`。
  - CSS：统一容器类（如 `.lark-article`），图片 `max-width:100%`，表格外层容器横向滚动，代码块基础高亮类名。

## 6. 接口设计（初版）
- `POST /convert`
  - 请求：`multipart/form-data`
    - `file`: `.docx`
    - `doc_id`（可选）：逻辑文档 ID（用于图片命名）。
  - 响应：`200`
    - `html`: 清洗后的 HTML 片段
    - `assets`: 图片等资源清单（原名/最终 URL/哈希）
    - `engine`: `pandoc | mammoth`
  - 错误：`400`（非 docx）、`500`（解析失败）。

## 7. 存储设计建议
- 文章表（示例）：
  - `id`（PK）
  - `title`、`doc_id`、`source_hash`（`docx` 的内容哈希，幂等）
  - `html_content`（`MEDIUMTEXT/LONGTEXT`）
  - `asset_manifest`（JSON）
  - `css_version`、`engine`、`created_at/updated_at`
- 资源存储：
  - 不内联 base64 大图；图片统一走外链 URL。
  - 记录指纹（内容哈希）以避免重复上传。

## 8. 安全与合规
- HTML 白名单清洗，禁止 `script/style/on*` 事件属性。
- 外链安全属性；可配置域名白名单。
- 上传鉴权与最小权限（仅写指定前缀）。
- 日志脱敏（不记录用户上传内容）。

## 9. 性能与可靠性
- 并发与超时：Pandoc 进程加超时；图片上传并发控制与指数退避重试。
- 大文件：分块上传（对象存储实现支持）；限制最大 `.docx` 大小（如 50–100MB）。
- 监控：请求量、耗时、失败率、引擎占比（Pandoc vs Mammoth）。
- 缓存与幂等：`doc_id + source_hash` 命中直接返回上次结果；图片按 hash 去重。

## 10. 部署与运维
- 形态 1：本地 Pandoc 二进制 + Python 服务（简单，需安装依赖）。
- 形态 2：容器化（推荐）：
  - 基础镜像包含 Pandoc；暴露 FastAPI；挂载卷用于临时文件与 public 资源。
  - CI/CD：构建镜像 → 推送 → 环境变量配置（存储凭证、基 URL）。
- 静态资源：`public/assets` 通过 Nginx/静态域名统一服务；或直接走对象存储域名。

## 11. 验收指标（示例）
- 功能验收：
  - 段落/标题/列表/图片/表格/链接/代码块正确渲染；图片自适应；表格横向滚动正常。
  - 10 篇真实文档抽样，视觉接近飞书（主观评分≥4/5）。
- 可靠性：
  - 100 次转换，失败 ≤ 1 次；平均耗时 ≤ 60s/篇（不含超大图上传）。
- 安全：
  - OWASP XSS 基线测试通过；白名单外标签/属性被剔除。

## 12. 风险与对策
- 复杂表格/合并单元格：Pandoc 效果较好；必要时补充 CSS；极端情况保留可读性优先。
- 公式（OMML）：启用 `--mathjax` 输出；前端引入 MathJax；或降级为图片。
- 字体与字号差异：统一 CSS 变量与排版尺度，避免逐字面还原。
- Pandoc 环境不可用：自动回退 Mammoth；并报警记录。
- 外网/对象存储受限：提供本地存储实现或延迟上传策略。

## 13. 迭代路线
Phase 0（原型，1 周）
- 完成 `/convert` 接口、Pandoc 主线、Mammoth 回退、本地 ImageStore、CSS 模板与清洗。

Phase 1（完善，1–2 周）
- 资源上传接入对象存储；锚点/TOC；代码高亮；更丰富白名单与样式。

Phase 2（增强，2–4 周）
- 飞书 API 通道：导出 HTML 或块结构；增量更新；更高还原度与回溯能力。

## 14. 与代码骨架的对应关系
- 服务入口：`app/main.py`（FastAPI `/convert`）。
- 转换器：`app/converters/` 下的 `pandoc_converter.py`、`mammoth_converter.py`、`hybrid.py`。
- 存储与清洗：`app/services/image_store.py`、`app/services/sanitizer.py`。
- 样式：`app/templates/article.css`（统一容器样式）。
- 说明文档：`README.md` 与本方案文档。

（注：若尚未补全上述代码文件，可按该方案逐步实现，接口与模块边界已在文档中明确。）

