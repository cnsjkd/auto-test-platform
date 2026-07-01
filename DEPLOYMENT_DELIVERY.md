# A2 Android 真机自动化测试平台交付与本地部署说明

> 项目：思必驰会议办公本 A2 Android 真机自动化测试平台  
> 阶段：Phase 4 后交付准备  
> 适用环境：Windows 本机 + ADB + 单台 A2 真机 + SQLite dev mode  
> 当前结论：本地源码交付可运行；真实 A2 真机专项验收仍需在现场设备上执行。

---

## 1. 交付包内容

核心目录：

```text
.
├── backend/                 # FastAPI + SQLAlchemy + Alembic + ADB adapter
├── frontend/                # React + TypeScript + Vite + Ant Design
├── .env.example             # 环境变量模板，复制为 .env 后使用
├── .gitignore               # 交付包排除规则
├── pytest.ini               # 后端测试收敛到 backend/tests，避免误收集生产代码
├── A2自动化测试平台_Spec_v0.1.md
├── A2自动化测试平台_Phase2_门禁包.md
├── A2自动化测试平台_Phase3_联调门禁报告.md
└── DEPLOYMENT_DELIVERY.md   # 本文档
```

交付包不应包含：

- `.env`、任何真实密钥或本机私有配置。
- `frontend/node_modules/`、`frontend/dist/`。
- `backend/*.db`、`backend/artifacts/`、`backend/artifacts_*/`。
- 日志文件、IDE 配置目录。

---

## 2. 运行前置条件

### 2.1 Windows 本机

建议版本：

- Python 3.11+。
- Node.js 20+ / 22+。
- npm。
- Android Platform Tools，确保 `adb.exe` 已加入 `PATH`。

检查命令：

```powershell
python --version
node --version
npm --version
adb version
```

### 2.2 A2 真机连接

1. A2 打开开发者选项。
2. 启用 USB 调试。
3. 使用数据线连接 Windows 本机。
4. 在 A2 上确认 RSA 授权弹窗。
5. 在 Windows 执行：

```powershell
adb devices -l
```

期望看到类似：

```text
List of devices attached
<serial> device product:... model:...
```

常见异常：

- `unauthorized`：在 A2 上确认 USB 调试授权；必要时执行 `adb kill-server` 后重新插拔。
- `offline`：检查线缆、USB 模式、重新插拔或重启 adb server。
- 无设备：确认 platform-tools 在 PATH，且 A2 USB 调试已开启。

---

## 3. 环境变量

从项目根目录复制模板：

```powershell
Copy-Item .env.example .env
```

默认 `.env.example` 内容适用于本地 SQLite dev mode：

```env
A2_DB_URL=sqlite:///backend/a2_automation.db
A2_ARTIFACT_ROOT=backend/artifacts
VITE_API_BASE_URL=
```

说明：

- 后端会自动读取项目根目录 `.env` 或 `backend/.env`；已存在的系统环境变量优先，不会被 `.env` 覆盖。
- `A2_DB_URL` 默认使用 SQLite，启动时自动建表；也可使用 Alembic 手动迁移。
- `A2_ARTIFACT_ROOT` 保存截图、UI XML、logcat 等证据文件。
- `VITE_API_BASE_URL` 本地开发建议留空，依赖 Vite dev proxy 转发 `/api` 与 `/ws` 到后端。

---

## 4. 后端启动与验证

### 4.1 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

当前 `requirements.txt` 包含 FastAPI、uvicorn、SQLAlchemy、Alembic、pytest、httpx。  
注意：`uiautomator2` 尚未写入依赖文件；语义定位真机闭环前需按现场网络与设备策略补装并验证。

### 4.2 启动后端

从项目根目录执行：

```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动时会自动：

- 读取 `.env`。
- 创建 SQLite DB 文件。
- 创建 artifact 目录。
- 建立 P0 表结构。

### 4.3 可选：手动执行迁移

如需使用 Alembic 迁移链路：

```powershell
Push-Location backend
alembic upgrade head
Pop-Location
```

### 4.4 后端健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

期望：HTTP 200，响应 envelope `code=0`，`data.status` 为 `ok` 或 `degraded`。

说明：

- DB 正常时 `data.db.ok=true`。
- ADB 未安装时接口仍返回 HTTP 200，但 `data.adbAvailable=false`，用于提示修复，不阻断前端预览。

---

## 5. 前端启动、构建与页面验证

### 5.1 安装依赖

```powershell
Push-Location frontend
npm install
Pop-Location
```

如交付包包含 `package-lock.json`，也可使用：

```powershell
Push-Location frontend
npm ci
Pop-Location
```

### 5.2 本地开发启动

确保后端已在 `127.0.0.1:8000` 启动，然后执行：

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

访问：

```text
http://127.0.0.1:5173
```

Vite 已配置：

- `/api` -> `http://127.0.0.1:8000`
- `/ws` -> `ws://127.0.0.1:8000`

### 5.3 生产构建验证

```powershell
npm --prefix frontend run build
```

成功后会生成 `frontend/dist/`。交付包默认不提交 `dist`，需要部署时现场构建。

### 5.4 前端页面可达性验证

构建后可临时验证静态页面：

```powershell
python -m http.server 5174 --bind 127.0.0.1 --directory frontend/dist
```

访问：

```text
http://127.0.0.1:5174/
```

期望 HTTP 200。

生产静态托管注意：如果不使用 Vite dev server，需要在同源网关/Nginx/反向代理中转发 `/api` 与 `/ws` 到 FastAPI 后端，否则浏览器会遇到跨域或 WebSocket 连接问题。

---

## 6. 核心流程验收

### 6.1 后端 API 冒烟

后端启动后执行：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/devices
Invoke-RestMethod http://127.0.0.1:8000/api/test-cases
Invoke-RestMethod http://127.0.0.1:8000/api/test-runs
```

创建普通截图用例：

```powershell
$body = @{
  name = "local smoke screenshot case"
  type = "ui"
  priority = "P0"
  tags = @("smoke")
  steps = @(@{ action = "screenshot" })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod http://127.0.0.1:8000/api/test-cases `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

缺设备运行守卫验证：

```powershell
$body = @{
  deviceId = $null
  caseIds = @(1)
  config = @{}
} | ConvertTo-Json -Depth 5

try {
  Invoke-RestMethod http://127.0.0.1:8000/api/test-runs `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

期望返回 HTTP 422，业务码 `42201`，且不会污染运行历史。

### 6.2 前端核心路径

浏览器访问 `http://127.0.0.1:5173` 后检查：

1. `/setup`：展示健康检查、ADB 状态、artifactRoot、设备授权指引。
2. `/devices`：点击扫描设备；A2 online 时应展示 serial、型号、Android 版本、分辨率等。
3. `/test-cases`：创建/查看用例；像素兜底字段应显式展示风险。
4. `/runs/new`：选择 online 设备与用例后创建运行。
5. `/runs/:id`：查看运行详情、结果、artifact 与像素兜底风险区。
6. `/artifacts/:id`：预览/下载截图、logcat、UI XML 等证据。

### 6.3 真机专项建议

在真实 A2 上至少补做：

- `adb devices -l` 授权状态验证。
- `/api/devices/scan` 60 秒内扫描并展示设备指纹。
- 截图：`POST /api/devices/{id}/screenshot` 生成 PNG artifact。
- UI XML：`POST /api/devices/{id}/dump-hierarchy` 生成 XML artifact。
- logcat：`POST /api/devices/{id}/logcat/snapshot` 生成日志 artifact。
- `semantic_click` / `semantic_input`：安装并验证 `uiautomator2` 后执行语义定位动作。
- `pixel_tap`：填写全部审计字段后执行；报告中必须展示原因、坐标、分辨率/方向、风险和改造建议。

---

## 7. 回滚方案

### 7.1 源码交付包回滚

每次交付前保留上一版源码压缩包，例如：

```text
delivery-a2-automation-20260630-previous.zip
delivery-a2-automation-20260630-current.zip
```

回滚步骤：

1. 停止前端 dev server 与后端 uvicorn。
2. 备份当前 `.env`、SQLite DB 与 artifact 目录。
3. 解压上一版交付包。
4. 复制 `.env` 到上一版根目录。
5. 执行 `pip install -r backend\requirements.txt` 与 `npm ci`/`npm install`。
6. 启动后端与前端。
7. 重新验证 `/api/health`、前端首页与核心 API。

### 7.2 SQLite 数据回滚

SQLite DB 默认位于：

```text
backend/a2_automation.db
```

建议每次升级前备份：

```powershell
Copy-Item backend\a2_automation.db backend\a2_automation.db.bak-YYYYMMDD-HHMM
```

如需回滚 DB：

1. 停止后端。
2. 将当前 DB 改名保留。
3. 将备份 DB 复制回 `backend/a2_automation.db`。
4. 启动后端并验证 `/api/health`。

### 7.3 前端构建回滚

若现场采用静态托管：

1. 每次发布保留上一版 `dist` 压缩包。
2. 发现问题时停止静态服务或切换软链接/目录。
3. 恢复上一版 `dist`。
4. 验证首页 HTTP 200。

---

## 8. 已知限制与 Backlog

1. **QA-P2-001 Backlog**：Artifact type hierarchy / ui_xml 命名不一致。当前非阻断，建议后续统一后端 artifact type 与前端展示枚举，避免报告筛选/下载命名歧义。
2. 尚未在本轮运维验证中连接真实 A2 真机执行端到端设备动作；已通过无设备/ADB 降级与核心 API 冒烟。
3. `uiautomator2` 未列入 `backend/requirements.txt`，语义定位真机闭环前需要补依赖并确认 Windows + A2 环境兼容。
4. FastAPI `on_event` 有弃用 warning，不影响 P0；后续可迁移 lifespan。
5. Vite 构建提示主 chunk 约 1,089 kB，P0 可接受；后续可做路由级 lazy loading/code splitting。
6. MVP 默认关闭认证，仅适合本机/受信网络。生产暴露前需补认证、TLS、访问控制和反向代理。
7. 当前 test run 同步执行，单设备闭环优先；后续多设备并发需要后台 worker 与 device lock 完整化。

---

## 9. 运维部署验证记录

本轮已执行：

| 项目 | 命令/方式 | 结果 |
|---|---|---|
| 后端默认测试 | `python -m pytest` | 通过，`6 passed, 25 warnings` |
| 前端构建 | `npm --prefix frontend run build` | 通过，生成 `frontend/dist`；Vite chunk size warning 非阻断 |
| 后端服务启动 | `PYTHONPATH=backend ... python -m uvicorn app.main:app --host 127.0.0.1 --port 8765` | 通过，验证后已停止 |
| 后端 health | `GET /api/health` | HTTP 200，`code=0` |
| 核心 API 列表 | `/api/devices`、`/api/test-cases`、`/api/test-runs` | HTTP 200，`code=0` |
| 用例创建 | `POST /api/test-cases`，steps 使用 `action=screenshot` | HTTP 201，`code=0` |
| 运行守卫 | `POST /api/test-runs`，`deviceId=null` | HTTP 422，业务码 `42201` |
| 前端静态页面 | `python -m http.server 5174 --directory frontend/dist` 后访问 `/` | HTTP 200，验证后已停止 |

本轮验证使用的临时端口：

- 后端冒烟：`127.0.0.1:8765`，已停止。
- 前端静态冒烟：`127.0.0.1:5174`，已停止。

本轮验证产生的 `frontend/dist`、`backend/devops_smoke.db`、`backend/artifacts_devops_smoke` 已清理，保持交付包符合“不含 dist/运行产物”的要求。

---

## 10. 最终交付结论

允许最终交付本地 MVP 源码包。

交付后用户只需：

1. 复制 `.env.example` 为 `.env` 并按需调整。
2. 安装后端与前端依赖。
3. 启动后端：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
4. 启动前端：`npm --prefix frontend run dev`。
5. 打开 `/setup` 连接 ADB 真机并执行核心流程。

生产/现场正式验收前必须补做真实 A2 真机专项验收，尤其是 ADB 授权、截图、UI XML、logcat、语义定位与像素兜底证据链。
