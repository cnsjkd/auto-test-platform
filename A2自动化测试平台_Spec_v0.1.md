# Spec - A2 Android 真机自动化测试平台 v0.1

> 生成日期：2026-06-30  
> 基于：PRD v0.1 + 架构文档 v0.1 + UIUX 文档 v0.1  
> 状态：已确认  
> 维护人：郝交付（交付总监）

---

## 1. 产品定义

- **一句话描述**：面向思必驰会议办公本 A2 Android 真机的 Local-first 自动化测试平台，从 Windows 本机 + ADB 真机起步，先跑通基础 UI 操作与证据闭环，再扩展为企业设备池、专项测试和质量看板。
- **目标用户**：测试负责人、自动化测试工程师、QA、Android/设备研发工程师、交付负责人，后续覆盖设备池管理员与 CI 维护者。
- **核心问题**：当前没有自动化资产、没有设备池、没有报告系统，需要从 0 建立可重复执行、可留证、可排障、可扩展的真机自动化质量闭环。

---

## 2. MVP 范围（锁定——不在此列表的功能一律不做）

| 优先级 | 功能 | 验收标准摘要 | RICE 评分 |
|---|---|---|---:|
| P0 | Windows 本机 ADB 真机接入与设备体检 | 60 秒内扫描 A2，展示 serial、型号、Android 版本、SDK、分辨率、电量、网络、存储、ADB 状态；未授权/未连接给出明确修复建议 | 9.00 |
| P0 | 基础 UI 操作编排与执行 | 跑通下拉/点击/输入/返回/等待/断言/截图；语义定位优先；像素坐标仅作为显式兜底并在报告中标注 | 4.59 |
| P0 | 测试报告与失败证据闭环 | 任意运行生成报告；失败保留步骤、截图、logcat、UI XML、设备状态、定位策略与失败原因 | 5.10 |

### 明确不做的功能（Won't Have）

- 云端 SaaS 设备农场 — 原因：当前目标是 Windows 本机 + A2 真机本地优先。
- 完整低代码测试平台/AI 自动生成用例 — 原因：MVP 必须先跑通真机第一公里。
- 多租户、组织权限、审计、计费 — 原因：企业化能力后移到 P3。
- 音频端到端质量全自动验收 — 原因：纯 ADB 无法保证会议麦克风/扬声器/降噪/回声消除全链路质量，后续需 companion APK 或外部声学闭环。
- 固件刷写、root、底层驱动诊断 — 原因：风险高且不属于当前自动化测试平台第一阶段。
- 多设备并发与 CI 质量门禁 — 原因：先保证单设备闭环，后续 P2/P3 扩展。

---

## 3. 技术架构（锁定）

- **前端**：React + Ant Design + Lucide 图标。
- **后端**：FastAPI + SQLAlchemy + Alembic。
- **执行引擎**：Python + pytest + uiautomator2 + ADB adapter。
- **报告**：Allure Pytest + 平台自有运行摘要。
- **数据库**：SQLite dev mode 起步，PostgreSQL 企业模式；DB 只存元数据和 artifact 索引。
- **文件存储**：本地 `artifacts/{run_id}/{device_serial}/...` 起步，后续支持 NAS/MinIO。
- **部署**：Windows 本机优先；后续可扩展为 Linux device-agent + 中央调度。
- **认证方案**：MVP 本机默认关闭登录；预留 JWT + RBAC。
- **后续适配器**：Appium 2 + UiAutomator2 作为 Phase 2/3 兼容通道；Prometheus/Grafana 作为趋势看板通道；STF/DeviceFarmer 仅在 Linux 设备实验室阶段评估。

### 3.1 定位策略硬约束

1. **语义定位优先**：点击、输入、断言默认使用 resource-id、text、description、accessibility label、class + hierarchy path、稳定语义锚点。
2. **像素坐标只做最后兜底**：如果控件确实无法语义定位，且用户要求不能放弃自动化测试，可以使用像素坐标触达。
3. **像素兜底必须显性告知**：任何像素坐标操作必须在用例、执行日志、报告中标注 `pixel_fallback=true`，并记录：`fallback_reason`、`x`、`y`、`screen_width`、`screen_height`、`orientation`、前后截图、稳定性风险、后续可测试性改造建议。
4. **禁止静默兜底**：不得在用户、报告、日志不知情的情况下从语义定位降级到像素坐标。
5. **可测试性改造优先级**：所有像素兜底点自动进入“可测试性改造清单”。

---

## 4. API 端点清单（锁定——开发时以此为唯一依据）

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|---|---|---|---|---|---|
| GET | `/api/health` | 平台健康检查 | 否 | 无 | `{ status, adbAvailable, pythonVersion, artifactRoot }` |
| GET | `/api/devices` | 查询设备列表 | 否 | query: `status` | `{ devices: Device[] }` |
| POST | `/api/devices/scan` | 扫描 ADB 设备并体检 | 否 | `{ refresh: boolean }` | `{ devices: Device[] }` |
| GET | `/api/devices/{device_id}` | 获取设备详情 | 否 | 无 | `{ device: Device }` |
| POST | `/api/devices/{device_id}/commands` | 执行设备命令/系统动作/语义操作/像素兜底 | 否 | `DeviceCommandRequest` | `{ command: DeviceCommand, artifacts: Artifact[] }` |
| POST | `/api/devices/{device_id}/screenshot` | 采集截图 | 否 | `{ name?: string }` | `{ artifact: Artifact }` |
| POST | `/api/devices/{device_id}/dump-hierarchy` | 采集 UI XML | 否 | `{ name?: string }` | `{ artifact: Artifact }` |
| POST | `/api/devices/{device_id}/logcat/snapshot` | 采集 logcat 快照 | 否 | `{ durationSec?: number, buffers?: string[] }` | `{ artifact: Artifact }` |
| GET | `/api/test-cases` | 查询测试用例 | 否 | query: `type,tags,enabled` | `{ cases: TestCase[] }` |
| POST | `/api/test-cases` | 创建测试用例 | 否 | `TestCaseCreateRequest` | `{ case: TestCase }` |
| POST | `/api/test-runs` | 创建测试运行 | 否 | `RunCreateRequest` | `{ run: TestRun }` |
| GET | `/api/test-runs` | 查询测试运行 | 否 | query: `status,deviceId,limit` | `{ runs: TestRun[] }` |
| GET | `/api/test-runs/{run_id}` | 获取运行详情 | 否 | 无 | `{ run: TestRun, results: TestResult[], artifacts: Artifact[] }` |
| POST | `/api/test-runs/{run_id}/cancel` | 取消运行 | 否 | `{ reason: string }` | `{ run: TestRun }` |
| GET | `/api/test-runs/{run_id}/artifacts` | 获取运行附件 | 否 | query: `type` | `{ artifacts: Artifact[] }` |
| GET | `/api/artifacts/{artifact_id}/download` | 下载附件 | 否 | 无 | binary stream |
| WS | `/ws/test-runs/{run_id}/events` | 运行事件流 | 否 | 无 | event stream |

### 4.1 DeviceCommandRequest

外部 API 字段统一使用 `action`，不得对外暴露 `commandType`。DB 内部可保留 `device_commands.command_type` 作为归类字段，由后端 service 层做 `action <-> command_type` 映射。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| action | enum | 是 | `semantic_click`、`semantic_input`、`semantic_assert`、`swipe`、`keyevent`、`open_notification`、`open_quick_settings`、`shell`、`pixel_tap`、`pixel_swipe`、`screenshot`、`dump_hierarchy`、`logcat_snapshot` |
| selector | object | 条件必填 | 语义定位器；`semantic_click`、`semantic_input`、`semantic_assert` 必填；支持 resource_id、text、description、class_name、xpath、hierarchy_path |
| params | object | 否 | action 参数；`semantic_input` 必须包含 `text`；`keyevent` 必须包含 `key`；`swipe` 使用方向/比例/时长，若使用明确像素起止点必须改用 `pixel_swipe` |
| timeoutSec | integer | 否 | 1-300，默认 30 |
| pixelFallback | boolean | 条件必填 | `pixel_tap`/`pixel_swipe` 必须为 true 且不可静默关闭 |
| fallbackReason | string | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，说明为何无法语义定位 |
| riskNote | string | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，说明像素兜底稳定性风险 |
| improvementSuggestion | string | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，说明后续可测试性改造建议 |
| x | integer | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，要求 `0 <= x < screenWidth` |
| y | integer | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，要求 `0 <= y < screenHeight` |
| screenWidth | integer | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，必须与执行时设备当前分辨率一致 |
| screenHeight | integer | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，必须与执行时设备当前分辨率一致 |
| orientation | enum | 条件必填 | `pixel_tap`/`pixel_swipe` 必填，`portrait` 或 `landscape`；未知方向不得执行像素兜底 |

### 4.2 错误码

| code | 含义 |
|---:|---|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40401 | 资源不存在 |
| 40901 | 设备已被占用/状态冲突 |
| 42201 | 测试计划不可执行 |
| 50001 | 平台内部错误 |
| 51001 | ADB 不可用 |
| 51002 | 设备未连接 |
| 51003 | 设备未授权 |
| 51004 | ADB 命令超时 |
| 52001 | UI 自动化驱动失败或动作执行异常 |
| 52002 | 语义定位失败 |
| 52003 | 像素兜底审计字段缺失 |
| 53001 | 报告生成失败 |

---

## 5. 数据库表清单（锁定）

| 表名 | 核心字段 | 索引 | 关联 |
|---|---|---|---|
| devices | id, serial, status, manufacturer, model, android_version, sdk_int, screen_width, screen_height, density, capabilities, last_seen_at | serial unique, status, model, last_seen_at | test_runs, artifacts, device_commands |
| test_cases | id, name, type, priority, tags, status, steps, has_pixel_fallback, pixel_fallback_count, description, created_at | status, priority, has_pixel_fallback, updated_at | test_results |
| test_runs | id, status, device_id, total_count, passed_count, failed_count, skipped_count, started_at, ended_at, report_path, config | status, device_id, started_at | devices, test_results, artifacts |
| test_results | id, run_id, case_id, device_id, status, duration_ms, error_code, message, locator_strategy, pixel_fallback_used, started_at, ended_at, raw | run_id, case_id, device_id, status | test_runs, test_cases, artifacts |
| artifacts | id, run_id, result_id, device_id, type, path, mime_type, size_bytes, checksum, meta, created_at | run_id, result_id, device_id, type, created_at | test_runs, test_results, devices |
| device_commands | id, device_id, run_id, result_id, case_id, command_type, source, params, response, exit_code, status, locator_mode, selector, pixel_fallback_used, locator_fallback_id, error_code, error_message, started_at, ended_at | device_id, run_id, result_id, command_type, status, locator_fallback_id, started_at | devices, test_runs, test_results, test_cases, locator_fallbacks |
| locator_fallbacks | id, run_id, result_id, device_id, case_id, action, x, y, screen_width, screen_height, orientation, fallback_reason, risk_note, improvement_suggestion, before_artifact_id, after_artifact_id, created_at | run_id, device_id, case_id, created_at | test_runs, test_results, artifacts |
| platform_events | id, run_id, device_id, level, category, message, payload, created_at | run_id, device_id, level, created_at | test_runs, devices |

---

## 6. 页面清单（锁定）

| 页面 | 路由 | 核心组件 | 对应 API | 设计 Token 主题 |
|---|---|---|---|---|
| 首次初始化页 | `/setup` | 环境检查卡、ADB 状态、设备授权指引、重新检测按钮 | `/api/health`, `/api/devices/scan` | dark-console |
| Command Center 控制台 | `/` | KPI 卡、设备在线状态、最新运行、最新失败、快速操作 | `/api/devices`, `/api/test-runs` | dark-console |
| Device Lab 设备实验室 | `/devices` | DeviceTable、DeviceCard、扫描按钮、状态 Badge | `/api/devices`, `/api/devices/scan` | dark-console |
| 设备详情页 | `/devices/:id` | 设备指纹、截图、UI XML、logcat 快照、命令面板 | `/api/devices/:id`, `/api/devices/:id/*` | dark-inspector |
| 测试用例页 | `/test-cases` | CaseTable、定位策略 Badge、像素兜底警示 Badge | `/api/test-cases` | dark-console |
| 创建运行页 | `/runs/new` | 设备选择、用例选择、运行配置、执行按钮 | `/api/devices`, `/api/test-cases`, `/api/test-runs` | dark-console |
| 运行列表页 | `/runs` | RunTable、状态筛选、报告入口 | `/api/test-runs` | dark-console |
| 运行详情页 | `/runs/:id` | 步骤时间线、截图/logcat/UI XML 附件、像素兜底风险区、Allure 链接 | `/api/test-runs/:id`, `/api/test-runs/:id/artifacts` | dark-report |
| Artifact 预览页 | `/artifacts/:id` | 图片/文本/XML/日志预览、下载按钮 | `/api/artifacts/:id/download` | dark-inspector |

---

## 7. 设计 Token（锁定）

- **主色**：`#2563EB`（Cobalt Blue）
- **字体**：Inter + Noto Sans SC
- **等宽字体**：JetBrains Mono + Fira Code
- **图标库**：Lucide
- **主题**：深色工作台
- **对标品牌**：Datadog / Sentry / Grafana + BrowserStack / AWS Device Farm / Firebase Test Lab + Linear / Vercel / Apple HIG

### 7.1 Foundation Token

| Token | 值 |
|---|---|
| `--color-ink-950` | `#0D1117` |
| `--color-ink-900` | `#111827` |
| `--color-slate-800` | `#1F2937` |
| `--color-slate-700` | `#374151` |
| `--color-slate-500` | `#6B7280` |
| `--color-slate-400` | `#9CA3AF` |
| `--color-slate-50` | `#F9FAFB` |
| `--color-blue-600` | `#2563EB` |
| `--color-blue-500` | `#3B82F6` |
| `--color-cyan-600` | `#0891B2` |
| `--color-green-600` | `#16A34A` |
| `--color-amber-600` | `#D97706` |
| `--color-red-600` | `#DC2626` |

### 7.2 Semantic Token

| Token | 值 |
|---|---|
| `--bg-app` | `var(--color-ink-950)` |
| `--bg-surface` | `var(--color-ink-900)` |
| `--bg-elevated` | `var(--color-slate-800)` |
| `--text-primary` | `var(--color-slate-50)` |
| `--text-secondary` | `var(--color-slate-400)` |
| `--border-default` | `var(--color-slate-700)` |
| `--border-focus` | `var(--color-blue-600)` |
| `--color-primary` | `var(--color-blue-600)` |
| `--color-success` | `var(--color-green-600)` |
| `--color-warning` | `var(--color-amber-600)` |
| `--color-error` | `var(--color-red-600)` |

---

## 8. 验收标准（锁定——QA 测试时以此为唯一依据）

| 编号 | 功能 | Given | When | Then |
|---|---|---|---|---|
| AC-001 | 平台健康检查 | Windows 本机启动平台 | 打开 `/setup` | 展示 Python、ADB、artifact 目录状态；ADB 不可用时给出修复建议 |
| AC-002 | 设备扫描 | A2 已连接并授权 USB 调试 | 点击“扫描设备” | 60 秒内展示 serial、型号、Android 版本、SDK、分辨率、电量、网络、存储、ADB 状态 |
| AC-003 | 未授权设备提示 | A2 处于 unauthorized | 点击“扫描设备” | 展示“设备未授权”，给出开启 USB 调试和 RSA 授权步骤 |
| AC-004 | 截图采集 | A2 online | 点击“采集截图” | 生成 PNG artifact，可在设备详情与运行报告查看 |
| AC-005 | UI XML 采集 | A2 online | 点击“采集 UI XML” | 生成 XML artifact；失败时保存错误原因 |
| AC-006 | logcat 快照 | A2 online | 点击“采集 logcat” | 生成 logcat artifact，包含采集时间、buffer、设备 serial |
| AC-007 | 语义定位点击 | 页面存在可语义定位控件 | 执行 `semantic_click` | 操作成功，报告记录 selector、耗时、前后截图 |
| AC-008 | 语义定位失败证据 | selector 超时未找到 | 执行用例 | 用例失败，保存截图、UI XML、logcat、失败 selector 与错误码 `52002` |
| AC-009 | 像素坐标兜底 | 控件无法语义定位但必须自动化 | 执行 `pixel_tap` 且填写兜底说明 | 用例继续自动化；报告标红“像素坐标兜底”，展示原因、坐标、分辨率/方向、风险和改造建议 |
| AC-010 | 像素兜底参数校验 | 执行 `pixel_tap` 但未填写 fallbackReason/riskNote | 提交命令 | 拒绝执行，返回错误码 `52003` |
| AC-011 | 标杆用例运行 | A2 online 且处于起始页面 | 运行“基础真机操作检查” | 完成下拉/点击/返回/截图/logcat，生成运行报告 |
| AC-012 | 报告证据闭环 | 任意运行完成 | 打开运行详情 | 可见设备信息、用例状态、步骤、截图、logcat、UI XML、定位策略、像素兜底风险区 |
| AC-013 | 运行取消 | 用例运行中 | 点击取消 | 运行状态变为 canceled，释放设备锁，保留已生成 artifact |
| AC-014 | artifact 下载 | 已生成附件 | 点击下载 | 下载文件名包含 run_id、device_serial、artifact_type |

---

## 9. 边界与约束

- 不支持 IE 浏览器。
- 响应式断点：桌面优先；最小支持宽度 1280px，后续适配平板。
- 性能目标：设备扫描 60 秒内返回；单次命令默认超时 30 秒；截图采集目标 10 秒内完成；运行详情首屏 3 秒内可见。
- Windows 本机必须可运行；不得依赖外部云服务完成 P0 核心流程。
- 所有 ADB 命令必须使用 `adb -s <serial>`，禁止假设单设备。
- ADB 未授权、offline、未连接必须区分展示。
- Allure 结果目录必须按 run 隔离，禁止复用目录污染历史结果。
- 大文件不入 DB，DB 只存路径、元数据、checksum。
- 像素坐标兜底必须显性告知，不得静默降级。
- 音频链路、性能趋势、多设备并发、CI 门禁不进入 P0，但数据模型允许后续扩展。

---

## 10. 变更记录

| 日期 | 变更内容 | 原因 | 影响范围 |
|---|---|---|---|
| 2026-06-30 | 生成 Spec v0.1 | 用户确认三文档并要求进入下一阶段 | 锁定 P0 范围、API、DB、页面、Token、验收标准 |
| 2026-06-30 | 定位策略调整为“语义定位优先 + 像素坐标显式兜底” | 用户明确要求若控件只能坐标触达，不能放弃自动化测试，但必须告知说明 | 影响 PRD、架构、Spec、执行日志、报告、QA 验收 |
| 2026-06-30 | Phase 2 门禁修订 API 契约 | 架构细化中出现 `commandType`、错误码与未锁定详情端点等契约偏差 | 外部 API 统一使用 `action`；错误码固定为 `52001/52002/52003`；`test_cases.steps` 派生像素兜底字段；未锁定端点不进入 P0 |
