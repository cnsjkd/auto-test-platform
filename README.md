# A2 Android 真机自动化测试平台

面向思必驰会议办公本 A2 的本地化自动化测试平台。项目目标不是零散脚本，而是形成一个 Windows 本机可运行、ADB 真机驱动、具备证据采集和报告闭环的企业级测试工作台。

当前版本已在真实 A2 上完成 MVP 验收与 P0 冒烟套件验证：可扫描设备、执行基础安全动作、采集截图/UI XML/logcat、生成运行报告，并强制记录 Pixel Fallback 审计信息。

---

## 当前状态

- 版本阶段：`v0.1+` 可交付基线。
- 目标设备：思必驰会议办公本 A2 / Android 13 / ADB 真机。
- 已验证设备：`A2PBVT1CFADBC000784`，`AINOTE-A2`，`1200x1920`。
- P0 冒烟套件：真实 A2 独立 QA 验证通过，`7/7` 用例 passed。
- 后端门禁：`20 passed`。
- 前端门禁：`typecheck` 与 `build` 通过。

关键质量报告：

- `qa_p0_smoke_suite/QUALITY_REPORT.md`：P0 冒烟套件真实 A2 QA 报告，本地证据目录不提交 Git。
- `DEPLOYMENT_DELIVERY.md`：Windows 本机部署与运行说明。
- `A2自动化测试平台_Spec_v0.1.md`：规格契约。

---

## 技术栈

### 后端

- FastAPI
- SQLAlchemy
- SQLite dev mode
- Alembic
- ADB adapter
- pytest

### 前端

- React
- TypeScript
- Vite
- Ant Design
- Lucide React

---

## 目录结构

```text
.
├── backend/                         # FastAPI 后端、ADB 适配、测试运行与报告服务
├── frontend/                        # React/Vite 前端控制台
├── .github/workflows/ci.yml         # GitHub Actions CI
├── .env.example                     # 本地环境变量模板
├── pytest.ini                       # pytest 收敛配置
├── DEPLOYMENT_DELIVERY.md           # 本地部署交付说明
├── A2自动化测试平台_Spec_v0.1.md     # 已锁定规格契约
└── overview.md                      # 当前交付总览
```

以下内容不应提交 Git：

- `.env`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend/*.db`
- `backend/artifacts*/`
- QA 证据目录
- 临时真机回归脚本

---

## 前置条件

Windows 本机建议安装：

- Python 3.11+
- Node.js 20+ / 22+
- npm
- Android Platform Tools，并确保 `adb` 在 `PATH` 中

检查：

```powershell
python --version
node --version
npm --version
adb version
adb devices -l
```

A2 真机要求：

1. 开启开发者选项。
2. 开启 USB 调试。
3. USB 连接 Windows 本机。
4. 在设备上确认 RSA 授权。
5. `adb devices -l` 显示 `device`，不能是 `unauthorized` 或 `offline`。

---

## 环境变量

复制模板：

```powershell
Copy-Item .env.example .env
```

默认模板：

```env
A2_DB_URL=sqlite:///backend/a2_automation.db
A2_ARTIFACT_ROOT=backend/artifacts
VITE_API_BASE_URL=
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```

说明：

- `A2_DB_URL`：后端 SQLite dev mode 数据库。
- `A2_ARTIFACT_ROOT`：截图、UI XML、logcat、报告等证据文件根目录。
- `VITE_API_BASE_URL`：生产静态托管时可配置 API base；本地 Vite proxy 时保持空。
- `VITE_DEV_PROXY_TARGET`：前端 dev proxy 目标后端地址，默认 `http://127.0.0.1:8000`。

---

## 后端启动

建议先创建虚拟环境：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

从项目根目录启动：

```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

扫描设备：

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/devices/scan `
  -ContentType "application/json" `
  -Body '{"refresh":true}'
```

---

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

如果后端不是 8000 端口，修改根目录 `.env`：

```env
VITE_DEV_PROXY_TARGET=http://127.0.0.1:18766
```

然后重启 Vite。

---

## P0 冒烟套件

平台内置固定套件：

- suite id：`p0_smoke`
- name：`A2 P0 冒烟套件`
- caseCount：7
- pixelFallbackCount：1
- requiresRiskAcceptance：true

覆盖能力：

1. ADB/设备前置留证。
2. screenshot：截图 PNG artifact。
3. dump_hierarchy：UI XML artifact。
4. logcat_snapshot：logcat artifact。
5. open_notification + BACK：通知栏安全动作。
6. open_quick_settings + BACK：快捷设置安全动作。
7. pixel_tap 审计样例：验证 Pixel Fallback 审计链路。

### 查询套件

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smoke-suite/p0
```

### 一键运行

先从 `/api/devices/scan` 获取 `deviceId`，然后：

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/smoke-suite/p0/run `
  -ContentType "application/json" `
  -Body '{"deviceId":1,"riskAccepted":true,"config":{"trigger":"manual"}}'
```

风险门禁：

- 若 `riskAccepted` 不是 `true`，后端返回 HTTP `422` / code `42201`。
- 未确认风险时不会创建 test run。

---

## Pixel Fallback 红线

元素定位默认语义优先：

- resource-id
- text
- description
- accessibility label
- class + hierarchy path
- 稳定语义锚点

如果某个控件只能靠像素坐标触达，允许使用像素兜底，但必须在用例、运行详情和报告中完整审计：

- `pixelFallback`
- `fallbackReason`
- `x`
- `y`
- `screenWidth`
- `screenHeight`
- `orientation`
- `riskNote`
- `improvementSuggestion`

缺字段会返回业务错误 `52003`。

---

## 测试与质量门禁

### 后端

```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -q
python -m compileall backend/app backend/tests backend/alembic
```

### 前端

```powershell
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

### CI

GitHub Actions 已配置：

- 后端 pytest
- 后端 compileall
- 前端 typecheck
- 前端 build

CI 不依赖真实 A2；真实 A2 验收仍需在 Windows + ADB 现场执行。

---

## 已知 Backlog

| ID | 优先级 | 内容 | 状态 |
|----|--------|------|------|
| P2-001 | P2 | 接入 `pytest-cov`，补覆盖率门禁 | 待处理 |
| P2-002 | P2 | 统一前后端 artifact type 枚举与展示文案 | 待处理 |
| P2-003 | P2 | 生产部署前补认证、TLS、反向代理和权限模型 | 待处理 |
| P2-004 | P2 | 浏览器 E2E 基线：Playwright/Cypress | 待处理 |
| P2-005 | P2 | 将更多 A2 业务场景沉淀为自动化用例库 | 待处理 |

---

## 当前交付结论

当前代码可作为 `v0.1+` 基线交付：

- 平台 MVP 已在真实 A2 上完成最终回归。
- P0 冒烟套件已在真实 A2 上通过独立 QA。
- P0=0，P1=0。
- 剩余 P2 不阻断交付。
