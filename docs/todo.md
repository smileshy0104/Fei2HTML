# TODO 任务清单（混合方案：Pandoc 主线 + Mammoth 回退）

本文将混合方案拆解为可执行任务，按阶段推进。每个任务包含目标、完成标准与产出。优先级：P0（必须）、P1（应有）、P2（可选）。

## 阶段划分（里程碑）
- M0 原型（1 周）：上传 .docx → Pandoc 转换（失败回退 Mammoth）→ 图片本地存储 → HTML 清洗与注入基础 CSS → 返回 html+assets。
- M1 完善（1–2 周）：对象存储接入、标题锚点/TOC、代码高亮、并发与重试、观测与告警、CLI 工具。
- M2 增强（2–4 周）：飞书 API 通道（导出/块结构）、幂等与缓存、复杂表格与公式的优化、后台管理与版本回溯。

---

## M0 原型（P0）

- [ ] 项目初始化与结构
  - 目标：建立最小服务骨架与目录。
  - 完成标准：
    - 存在服务入口 `app/main.py`，可启动；
    - 目录包含 `app/converters/`, `app/services/`, `app/templates/`, `docs/`, `scripts/`。
  - 产出：初始 README、依赖 `requirements.txt`、运行说明。

- [ ] 接口：POST /convert（接收 .docx）
  - 目标：接收 multipart/form-data 文件与可选 `doc_id`。
  - 完成标准：
    - 非 .docx 返回 400；
    - 成功返回 JSON：`{html, assets, engine}`；
    - 错误返回 500 并包含可读错误信息。
  - 产出：`app/main.py` 可运行，`uvicorn` 启动正常。

- [ ] 转换器：Pandoc 主线
  - 目标：`.docx → html5`，提取媒体到临时目录。
  - 完成标准：
    - 探测 PATH 中 `pandoc` 可用；
    - 能输出 HTML 字符串与媒体文件列表；
    - 进程执行设置超时，异常被捕获。
  - 产出：`app/converters/pandoc_converter.py`。

- [ ] 转换器：Mammoth 回退
  - 目标：Pandoc 失败时使用 Mammoth 生成 HTML。
  - 完成标准：
    - 自定义 image handler 将图片落至临时目录；
    - 输出 HTML 与媒体文件列表；
    - 与 Pandoc 接口一致（方便 Hybrid 调用）。
  - 产出：`app/converters/mammoth_converter.py`。

- [ ] 转换器：Hybrid 调度
  - 目标：统一入口，优先 Pandoc，失败回退 Mammoth。
  - 完成标准：
    - 记录 `engine` 为 `pandoc | mammoth`；
    - 向上抛出统一 `ConversionError`；
    - 单元测试覆盖主/回退路径（基础）。
  - 产出：`app/converters/hybrid.py`、基础测试用例。

- [ ] 图片存储：本地实现（可切换）
  - 目标：抽象 `ImageStore` 接口，默认写入 `public/assets/{doc_id}/...` 并返回 `/assets/...` URL。
  - 完成标准：
    - `save(local_path, dest_path)->url`；
    - 自动创建目录、处理命名冲突（覆盖或加指纹）；
    - 返回清单 `assets: [{name, url, hash}]`。
  - 产出：`app/services/image_store.py`（接口+本地实现）。

- [ ] HTML 清洗与样式注入
  - 目标：安全白名单清洗，注入统一容器类与基础 CSS。
  - 完成标准：
    - Bleach 白名单保留 p/h1–h6/ul/ol/li/a/img/table/thead/tbody/tr/th/td/pre/code/blockquote 等；
    - 图片添加 `max-width:100%;height:auto;`；
    - 外链增加 `rel="noopener noreferrer"`；
    - 输出 HTML 片段可直接嵌入前端容器。
  - 产出：`app/services/sanitizer.py`、`app/templates/article.css`。

- [ ] 开发脚本与示例
  - 目标：提供命令行转换示例。
  - 完成标准：
    - `python scripts/convert_docx.py file.docx --doc-id xxx` 输出 html 与 assets；
    - README 更新运行与示例。
  - 产出：`scripts/convert_docx.py`、更新 `README.md`。

---

## M1 完善（P1）

- [ ] 对象存储接入（替换/扩展 ImageStore）
  - 目标：支持 OSS/COS/S3 任一实现，鉴权通过环境变量配置。
  - 完成标准：
    - 新实现：`OssImageStore`（或等价），并发上传与重试；
    - 命名：`{doc_id}/{hash_or_rev}/{seq}.{ext}`；
    - 配置切换无须改业务代码（依赖注入）。
  - 产出：对象存储实现、配置样例与文档。

- [ ] 标题锚点与目录（TOC）
  - 目标：为 h1–h6 生成稳定 `id`，可选生成 TOC。
  - 完成标准：
    - H 标签附带 slug 化 id，重复名自动去重；
    - 可开关生成 TOC（返回字段或单独接口）。
  - 产出：HTML 整形增强代码与文档。

- [ ] 代码块与高亮
  - 目标：为 `pre>code` 添加语言类名；前端可接入高亮库（Prism/Highlight.js）。
  - 完成标准：
    - 支持从样式/提示符推断语言（尽力而为）；
    - 文档说明如何前端加载高亮。
  - 产出：整形逻辑与文档。

- [ ] 表格移动端适配与样式
  - 目标：表格外围容器支持横向滚动；基础边框/间距统一。
  - 完成标准：
    - CSS 更新，示例文档渲染正常；
    - 大宽表不破版，滚动可达。
  - 产出：CSS 更新与预览截图。

- [ ] 并发与重试、超时治理
  - 目标：Pandoc 进程与上传并发控制，统一重试与超时配置。
  - 完成标准：
    - Pandoc 执行超时可配置，失败降级；
    - 上传 429/5xx 指数退避重试；
    - 日志包含 requestId/docId/engine/耗时。
  - 产出：配置项、日志与示例指标。

- [ ] 观测与告警
  - 目标：基础指标与错误告警。
  - 完成标准：
    - 指标：转换次数/成功率/引擎占比/平均耗时/图片数；
    - 告警：连续失败、引擎长时间回退、上传失败率升高。
  - 产出：日志/指标埋点与告警规则示例。

- [ ] CLI 工具与批量处理
  - 目标：支持目录批量转换与资产汇总。
  - 完成标准：
    - `scripts/convert_docx.py` 支持目录输入、并发度参数、错误报告。
  - 产出：增强版 CLI 与 README 更新。

---

## M2 增强（P2）

- [ ] 飞书 API 通道（导出 HTML）
  - 目标：基于飞书开放接口导出 HTML 或文档块。
  - 完成标准：
    - 新增 `FeishuConverter`，支持凭证配置；
    - 获取图片/附件临时链接并外发至对象存储；
    - 与 Hybrid 并列或作为独立入口使用。
  - 产出：`app/converters/feishu_api.py`、配置与使用文档。

- [ ] 幂等与缓存
  - 目标：避免重复转换与重复上传。
  - 完成标准：
    - 使用 `doc_id + source_hash` 命中缓存直接返回；
    - 图片按内容哈希去重；
    - 返回记录包含 `engine/css_version/source_hash`。
  - 产出：缓存层/记录表结构设计与实现。

- [ ] 复杂表格与公式优化
  - 目标：提升合并单元格表格与数学公式的观感。
  - 完成标准：
    - 表格样式优化与边界示例；
    - 公式：Pandoc `--mathjax` + 前端 MathJax；无法识别时降级位图。
  - 产出：CSS/前端指引与回退策略文档。

- [ ] 后台管理与版本回溯（可选）
  - 目标：管理历史版本、重跑转换、对比差异。
  - 完成标准：
    - 存库 `html_content`、`asset_manifest`、`engine`、`source_hash`；
    - 简易列表/详情/重跑接口或页面。
  - 产出：表结构/接口与简易页面（或仅接口）。

---

## 横切任务

- [ ] 配置与秘密管理
  - 目标：通过环境变量或配置文件注入对象存储凭证、Pandoc 超时等。
  - 完成标准：示例 `.env.example`、配置读取模块、敏感信息不入库/日志。

- [ ] 安全清单
  - 目标：XSS 白名单、外链属性、上传权限最小化。
  - 完成标准：安全测试过基线用例，外链统一 `rel` 属性，上传凭证最小权限。

- [ ] 文档与示例
  - 目标：完善 README、接口文档、示例输入输出与截图。
  - 完成标准：`docs/hybrid_plan.md` 与 `README.md` 对齐，新增示例样本与渲染截图。

- [ ] 基础测试
  - 目标：为关键路径添加单元与集成测试（可选）。
  - 完成标准：Hybrid 主/回退路径、HTML 清洗器、ImageStore 保存成功/异常路径。

---

## 验收清单（DoD）
- 10 篇真实文档抽样转换成功（段落/标题/列表/表格/图片/链接/代码块渲染正确）。
- 样式观感接近飞书：主观评分≥4/5；表格可横向滚动；图片不溢出版心。
- 失败率 ≤ 1%；平均接口耗时 ≤ 60s/篇（不含超大上传）。
- HTML 通过白名单清洗，无 XSS 漏洞；外链具备安全属性。
- 产出可存库（MEDIUMTEXT/LONGTEXT）并在前端容器直接渲染。

---

## 交付物清单
- 服务端：`app/` 目录下的可运行 FastAPI 服务与转换器实现。
- CSS 模板：`app/templates/article.css`。
- CLI：`scripts/convert_docx.py`。
- 文档：`README.md`、`docs/hybrid_plan.md`、`docs/todo.md`。
- 示例：示例 .docx、转换输出示例、渲染截图（后续补充）。

