# A2 自动化测试平台 Phase 3 联调门禁报告 v0.1

> 日期：2026-06-30  
> 阶段：Phase 3 并行开发 + 自检修复  
> 状态：通过，允许进入 Phase 4 QA  
> 维护人：郝交付（交付总监）

---

## 1. 开发交付范围

### 前端

交付目录：`frontend/`

已实现：

- React + TypeScript + Vite + Ant Design + Lucide。
- 全局 Shell：左侧导航、顶部状态栏、深色企业测试工作台。
- 页面：`/setup`、`/`、`/devices`、`/devices/:id`、`/test-cases`、`/runs/new`、`/runs`、`/runs/:id`、`/artifacts/:id`。
- Pixel Fallback 风险展示：原因、x/y、screenWidth/screenHeight、orientation、riskNote、improvementSuggestion。
- API client：统一 envelope，后端不可用时降级 mock；Vite dev server 已配置 `/api` 和 `/ws` 代理到 `127.0.0.1:8000`。

### 后端

交付目录：`backend/`

已实现：

- FastAPI 后端骨架、统一异常处理、requestId middleware。
- SQLAlchemy + SQLite dev mode + Alembic 初始迁移。
- 8 张核心表：devices、test_cases、test_runs、test_results、artifacts、device_commands、locator_fallbacks、platform_events。
- P0 API：health、devices、commands、test-cases、test-runs、artifacts download、WebSocket events。
- ADB adapter 白名单、artifact manager、test run 同步执行器、失败证据采集。
- Pixel Fallback 校验与审计链路：缺字段返回 `52003`；外部字段固定使用 `action`，不暴露 `commandType`。

---

## 2. 门禁发现与修复

| 问题 | 发现方式 | 处理结果 |
|---|---|---|
| 前端开发模式默认同源请求，真实后端在 8000 端口时会误降级 mock | 静态检查 `vite.config.ts` | 已加 `/api`、`/ws` 代理到 `127.0.0.1:8000` |
| 后端设备序列化缺少前端展示字段 `battery/network/storage/adbStatus` | 契约检查前后端类型 | 已在 `device_to_dict` 中补齐默认字段 |
| 后端运行序列化缺少 `deviceSerial/pixelFallbackCount` | 契约检查运行列表/详情 | 已在 `test_run_to_dict` 中补齐 |
| 前端 Artifact 页把二进制下载接口当 JSON 元数据接口 | 静态检查 `ArtifactPage.tsx` 与后端 `FileResponse` | 已通过路由 state 传入 artifact 元数据；下载接口仅用于文件下载 |
| `POST /api/test-runs` 缺 `deviceId` 时会创建失败运行并污染历史 | 真实 HTTP 冒烟 | 已改为运行前直接返回 `42201`，并补回归测试 |

---

## 3. 自检结果

### 前端

命令：

```bash
cd "D:/WorkBuddyData/2026-06-30-11-43-37/frontend" && "C:/Users/PC/.workbuddy/binaries/node/versions/22.22.2/node.exe" "node_modules/typescript/bin/tsc" --noEmit && "C:/Users/PC/.workbuddy/binaries/node/versions/22.22.2/node.exe" "node_modules/vite/bin/vite.js" build
```

结果：通过。

备注：Vite 提示主 chunk 约 1,089 kB，P0 可接受；后续建议路由级 lazy loading/code splitting。

### 后端

命令：

```bash
PYTHONPATH="D:/WorkBuddyData/2026-06-30-11-43-37/backend" "C:/Users/PC/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -m pytest "D:/WorkBuddyData/2026-06-30-11-43-37/backend/tests"
```

结果：`6 passed, 25 warnings`。

命令：

```bash
"C:/Users/PC/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -m compileall "D:/WorkBuddyData/2026-06-30-11-43-37/backend/app" "D:/WorkBuddyData/2026-06-30-11-43-37/backend/tests" "D:/WorkBuddyData/2026-06-30-11-43-37/backend/alembic"
```

结果：通过。

备注：FastAPI `on_event` deprecation warning 暂不影响 P0 功能，后续可迁移 lifespan。

---

## 4. 真实 HTTP 冒烟

启动服务：

```bash
PYTHONPATH="D:/WorkBuddyData/2026-06-30-11-43-37/backend" A2_DB_URL="sqlite:///D:/WorkBuddyData/2026-06-30-11-43-37/backend/smoke_phase3.db" A2_ARTIFACT_ROOT="D:/WorkBuddyData/2026-06-30-11-43-37/backend/artifacts_smoke_phase3" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证项：

| 检查 | 结果 |
|---|---|
| `GET /api/health` 返回 envelope，包含 `adbAvailable` | 通过 |
| 创建缺字段 Pixel Fallback 用例返回 `52003` | 通过 |
| 创建普通 screenshot 用例成功，steps 使用 `action` | 通过 |
| `GET /api/test-cases` 返回 steps | 通过 |
| `POST /api/test-runs` 缺 `deviceId` 返回 `42201` | 通过 |
| 运行前拒绝后不污染 `/api/test-runs` 历史 | 通过 |

真实 HTTP 冒烟结论：通过。

---

## 5. 设计 / 契约红线复查

| 红线 | 结果 |
|---|---|
| 前端源码无 `commandType` 作为契约字段 | 通过 |
| 后端仅保留 `commandType` 拒绝测试，外部契约使用 `action` | 通过 |
| 无 `Welcome to`、`Lorem ipsum`、紫色/粉色渐变令牌 | 通过 |
| Pixel Fallback 字段在前后端均可追踪 | 通过 |
| 未新增未确认的 `/api/test-cases/{id}` | 通过 |

---

## 6. 未完成 / 风险

1. 尚未连接真实 A2 设备执行 ADB / uiautomator2 端到端真机操作。
2. `uiautomator2` 当前未加入 requirements，语义点击/输入真机闭环前需要安装并验证。
3. P0 test run 是同步执行；后续长任务需要后台 worker + device lock。
4. 前端 chunk 偏大，后续可做路由拆包。
5. FastAPI startup 使用 `on_event` 有弃用警告，后续可迁移 lifespan。

---

## 7. Phase 3 结论

Phase 3 自检与联调门禁通过，允许进入 Phase 4 QA。

下一步：严过关进行独立 QA 验收，重点覆盖：

- API 契约与错误码。
- Pixel Fallback 必填审计字段。
- 前端 P0 页面闭环。
- 后端无设备/无 ADB 降级行为。
- Artifact 与报告证据链。
