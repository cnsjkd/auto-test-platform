# A2 自动化测试平台 Phase 2 门禁包 v0.1

> 日期：2026-06-30  
> 阶段：Phase 2 设计细化  
> 状态：通过，允许进入 Phase 3 开发  
> 维护人：郝交付（交付总监）

---

## 1. Phase 2 输入

- `A2自动化测试平台_Spec_v0.1.md`
- 高见远：API / DB / 执行器细化与契约修订补丁
- 颜好看：P0 页面级设计细化与像素兜底 UI 规范

---

## 2. 门禁结论

| 检查项 | 结论 | 说明 |
|---|---|---|
| 是否超出 Spec P0 范围 | 通过 | 仅覆盖设备体检、基础 UI 操作、报告证据闭环 |
| API 是否覆盖页面需求 | 通过 | Setup、Devices、Test Cases、Runs、Artifacts 均有对应 API 或 artifact 下载链路 |
| DB 是否支撑审计闭环 | 通过 | `locator_fallbacks`、`device_commands`、`artifacts`、`platform_events` 支撑像素兜底与证据链 |
| 像素兜底是否显式告知 | 通过 | 用例、运行、WebSocket、报告、Artifact 预览均要求展示原因、坐标、屏幕信息、风险、改造建议 |
| 设计反模式检查 | 通过 | 无紫色渐变、无 emoji 图标、无 SaaS Hero、无空洞欢迎页、未超出 P0 |
| 契约一致性 | 修正后通过 | 已修正 `commandType`、错误码、未锁定详情端点等偏差 |

---

## 3. 最终锁定契约

### 3.1 外部 API 字段

- 设备命令外部 API 统一使用 `action`。
- 禁止对外暴露或要求前端提交 `commandType`。
- DB 内部可保留 `device_commands.command_type`，但必须由后端 service 层映射：
  - `request.action -> device_commands.command_type`
  - `device_commands.command_type -> response.action`

### 3.2 action 枚举

`action` 只允许以下枚举：

- `semantic_click`
- `semantic_input`
- `semantic_assert`
- `swipe`
- `keyevent`
- `open_notification`
- `open_quick_settings`
- `shell`
- `pixel_tap`
- `pixel_swipe`
- `screenshot`
- `dump_hierarchy`
- `logcat_snapshot`

### 3.3 错误码

| code | 最终含义 | 使用规则 |
|---:|---|---|
| 52001 | UI 自动化驱动失败或动作执行异常 | uiautomator2/ADB UI 执行异常、驱动不可用、点击/输入/滑动执行异常 |
| 52002 | 语义定位失败 | `semantic_click`、`semantic_input`、`semantic_assert` 的 selector 无法匹配目标控件 |
| 52003 | 像素兜底审计字段缺失 | `pixel_tap`、`pixel_swipe` 缺少必填审计字段 |

### 3.4 P0 API 范围控制

- Phase 3 不新增 `GET /api/test-cases/{id}`。
- `GET /api/test-cases` 可返回 `steps`，支持前端列表抽屉展示步骤详情。
- 未锁定端点不得作为 P0 必做；如后续确需新增，必须进入 Spec 变更记录。

### 3.5 像素兜底字段命名

外部 API 使用驼峰字段：

```json
{
  "pixelFallback": true,
  "fallbackReason": "目标控件未暴露稳定语义属性",
  "riskNote": "坐标依赖当前分辨率和方向，布局变化可能漂移",
  "improvementSuggestion": "建议补充 resource-id 或 content-desc",
  "x": 702,
  "y": 1660,
  "screenWidth": 1404,
  "screenHeight": 1872,
  "orientation": "portrait"
}
```

DB 使用蛇形字段：

- `pixel_fallback`
- `fallback_reason`
- `risk_note`
- `improvement_suggestion`
- `screen_width`
- `screen_height`

---

## 4. API / DB 细化摘要

### 4.1 API

- `/api/health`：平台、DB、ADB、artifact 目录健康检查。
- `/api/devices`、`/api/devices/scan`、`/api/devices/{device_id}`：设备列表、扫描、详情。
- `/api/devices/{device_id}/commands`：语义操作、系统动作、像素兜底、证据动作统一入口。
- `/api/devices/{device_id}/screenshot`：截图 artifact。
- `/api/devices/{device_id}/dump-hierarchy`：UI XML artifact。
- `/api/devices/{device_id}/logcat/snapshot`：logcat artifact。
- `/api/test-cases`：用例列表与创建；列表可返回 steps。
- `/api/test-runs`：运行创建与列表。
- `/api/test-runs/{run_id}`、`/api/test-runs/{run_id}/cancel`、`/api/test-runs/{run_id}/artifacts`：运行详情、取消、附件。
- `/api/artifacts/{artifact_id}/download`：artifact 下载。
- `/ws/test-runs/{run_id}/events`：运行事件流。

### 4.2 DB

- `devices`：ADB 设备与体检状态。
- `test_cases`：用例定义，`steps` 存 JSON/TEXT，`has_pixel_fallback` 与 `pixel_fallback_count` 由 steps 派生。
- `test_runs`：运行主表。
- `test_results`：用例结果。
- `artifacts`：证据文件元数据。
- `device_commands`：设备命令执行历史，内部字段 `command_type` 映射外部 `action`。
- `locator_fallbacks`：像素坐标兜底审计主表。
- `platform_events`：运行事件、WebSocket 推送与报告串联。

---

## 5. 像素坐标兜底审计链路

1. 用例创建或命令执行识别 `action=pixel_tap/pixel_swipe`。
2. 强制校验 `pixelFallback=true` 与全部审计字段。
3. 缺字段返回 `52003`，不得执行。
4. 校验坐标范围与当前设备分辨率/方向。
5. 执行前保存 `pixel_audit` 截图；可行时保存 UI hierarchy。
6. 写入 `locator_fallbacks`。
7. 写入 `device_commands`，标记 `locator_mode=pixel_fallback`。
8. WebSocket 推送 `pixel_fallback_used`。
9. 运行详情、报告、Artifact 预览全部展示原因、坐标、分辨率/方向、风险与改造建议。

---

## 6. 页面设计门禁

### 6.1 页面范围

- `/setup`
- `/`
- `/devices`
- `/devices/:id`
- `/test-cases`
- `/runs/new`
- `/runs`
- `/runs/:id`
- `/artifacts/:id`

### 6.2 UI 规则

- 深色企业测试工作台，不做营销页。
- Lucide-only，不使用 emoji 图标。
- Inter + Noto Sans SC；日志、ADB、坐标使用 JetBrains Mono / Fira Code。
- 颜色使用 Token，不在组件中硬编码色值。
- Pixel Fallback 使用 risk/error token、徽标、左边框、摘要卡标出风险。
- 空态必须提供具体下一步，不写空洞欢迎语。

---

## 7. Phase 3 开发准入

### 7.1 后端 / 执行器优先级

1. FastAPI 骨架、统一响应、错误码、requestId。
2. SQLAlchemy models 与 Alembic migrations。
3. `/api/health`、ADB 与 artifact 目录检查。
4. 设备扫描、体检、详情。
5. Artifact Manager 与下载。
6. Test Case 创建/列表与像素兜底校验。
7. Device Commands 与 Device Lock。
8. Test Runs 状态机与 WebSocket 事件。
9. 失败证据采集与报告生成。

### 7.2 前端优先级

1. 设计 Token、全局 Shell、左侧导航、顶部 ADB 状态栏。
2. 基础组件：Button、Input、Select、Badge、Table、Tabs、Drawer、Skeleton、InlineAlert、CodeBlock、Timeline。
3. `/setup`。
4. `/devices` 与 `/devices/:id`。
5. `/test-cases`。
6. `/runs/new`。
7. `/runs/:id`。
8. `/artifacts/:id`。
9. `/runs`。

### 7.3 首个验收切片

完成一条本地闭环：

`/setup -> /devices -> /test-cases -> /runs/new -> /runs/:id -> /artifacts/:id`

必须证明：设备体检、执行、失败证据、像素坐标兜底风险在 UI 和报告中全链路可见。

---

## 8. 决策日志

```text
[11:55] Phase 2 - 接受像素坐标作为最后兜底 - 用户要求不能因控件不可语义定位而放弃自动化 - 影响：用例、日志、报告必须显式展示像素兜底风险
[12:20] Phase 2 - 退回架构契约不一致 - 架构细化中出现 commandType、错误码、未锁定端点偏差 - 影响：要求架构师输出修订补丁
[12:35] Phase 2 - 外部 API 统一 action 字段 - Spec 是开发唯一契约，避免前后端字段漂移 - 影响：Phase 3 Pydantic、前端表单、WebSocket、报告全部使用 action
[12:36] Phase 2 - 未锁定详情端点不进入 P0 - 防止 API 范围膨胀 - 影响：GET /api/test-cases/{id} 暂不实现，后续需要走 Spec 变更
[12:38] Phase 2 - 门禁通过进入 Phase 3 - 设计无反模式，架构契约已修正 - 影响：启动前后端并行开发与自检
```
