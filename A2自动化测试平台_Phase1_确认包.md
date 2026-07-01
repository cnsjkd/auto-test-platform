# A2 Android 真机自动化测试平台 - Phase 1 三文档确认包

> 项目：思必驰会议办公本 A2 自动化测试平台  
> 阶段：Phase 1 并行调研 + 三文档门禁  
> 状态：待用户确认  
> 汇编人：郝交付（交付总监）  
> 生成时间：2026-06-30

---

## 0. 用户需求锁定

用户目标不是单纯写几个测试脚本，而是为 **思必驰会议办公本 A2 Android 真机** 建立一个公司级、企业内部独立拥有的自动化测试平台。

当前约束与目标：

1. **设备**：A2 是 Android 真机，不是普通 App 项目；支持 ADB；系统版本、分辨率、SDK、设备信息由平台自动读取。
2. **环境**：当前先在这台 Windows 电脑上落地；从 0 开始，没有用例、平台、CI、接口文档、设备池等现有资产。
3. **覆盖方向**：最终覆盖 UI 自动化、设备命令、音频链路、稳定性、性能采集、兼容性、多设备并发、报告看板、CI 集成。
4. **推进原则**：不能一口吃成大胖子；先跑通基础真机操作，例如下拉通知栏、点击、截图、logcat，再逐步扩展。
5. **交付形态**：不是临时脚本，而是“每家公司独立拥有属于自己的自动化测试平台”。
6. **元素定位规则**：自动化用例语义定位优先；若某个控件确实只能靠像素坐标触达，不能放弃自动化测试，但必须显式标注“像素坐标兜底”，说明原因、坐标、设备分辨率/方向、稳定性风险和后续可测试性改造建议。

---

## 1. Phase 1 专家产出清单

| 交付物 | 责任专家 | 状态 | 文件 |
|---|---|---|---|
| PRD 文档 | 许清楚（PM） | 已完成 | `A2自动化测试平台_PRD_v0.1.md` |
| 架构文档 | 高见远（架构） | 已完成 | `A2自动化测试平台_架构文档_v0.1.md` |
| UIUX 文档 | 颜好看（设计） | 已完成 | `A2自动化测试平台_UIUX文档_v0.1.md` |
| 一致性检查 | 郝交付（交付总监） | 已完成 | 本文件 |

---

## 2. 三文档核心结论

### 2.1 PRD 核心结论

MVP 第一阶段只做 3 件最关键的事：

1. **Windows 本机 ADB 真机接入与设备体检**
   - 自动发现 A2 设备。
   - 展示序列号、型号、Android 版本、SDK、分辨率、电量、网络、存储、ADB 授权状态。

2. **测试报告与失败证据闭环**
   - 每次执行保留设备信息、步骤、耗时、截图、日志、失败原因、附件。
   - 失败时自动留证，不依赖人工补截图、补日志。

3. **基础 UI 操作编排与执行**
   - 先跑通点击、滑动/下拉、输入、返回、等待、断言、截图。
   - 第一条标杆用例：A2 真机完成一个“下拉通知栏/下拉面板/设置项”类基础操作并生成报告。

后续再扩展：ADB 命令用例化、性能采集、稳定性长跑、音频链路、多设备并发、趋势看板、CI 质量门禁。

### 2.2 架构核心结论

推荐最终稳定组合：

- **ADB 底座**：设备发现、截图、录屏、logcat、dumpsys、shell、文件传输。
- **Python uiautomator2**：MVP 主 UI 驱动，用于点击、滑动、下拉、元素定位、dump hierarchy。
- **pytest**：测试执行与 fixture 管理。
- **Allure Pytest**：用例级报告和附件归档。
- **FastAPI**：后端平台服务。
- **React + Ant Design**：Web 控制台。
- **PostgreSQL + 文件存储**：元数据与 artifact 存储。
- **Appium 2 + UiAutomator2**：Phase 2/3 作为企业兼容适配器，不阻塞 MVP。
- **Prometheus/Grafana**：后续用于长期性能与稳定性趋势，不替代 Allure 报告。

架构师明确不建议：

- 不建议纯 Appium 起步：依赖重，第一公里慢。
- 不建议纯 ADB 作为唯一 UI 自动化方案：复杂 UI 定位和断言弱。
- 不建议 Windows MVP 直接上 STF/OpenSTF：依赖重、官方对 Windows 不友好。

### 2.3 UIUX 核心结论

平台设计方向命名为 **A2 TestOps Console**。

定位：企业内部“ADB-first 真机自动化测试 + 设备实验室 + 可观测性 + 报告中心”平台。

设计原则：

- 深色专业工作台，不做营销型 SaaS Hero。
- 第一屏直接展示设备在线率、运行状态、失败趋势、队列压力和最新产物。
- 失败排障路径短：一次点击内看到截图、视频、logcat、ADB 命令、性能曲线。
- 图标统一使用 Lucide。
- 字体使用 Inter + Noto Sans SC；日志和命令使用 JetBrains Mono / Fira Code。
- 配色为 Navy / Graphite 深色底 + Cobalt Blue 主操作色 + Green/Amber/Red 状态色。

---

## 3. Phase 1 一致性检查

### 3.1 PRD 功能是否有对应架构/API？

| PRD 功能 | 架构/API 对应 | 检查结果 |
|---|---|---|
| ADB 设备发现与体检 | `POST /api/devices/scan`、`GET /api/devices`、`devices` 表、`device-discovery` 模块 | 通过 |
| 设备信息读取 | ADB `getprop`、`wm size`、`dumpsys battery`、Device Service、`devices.capabilities` | 通过 |
| 截图/录屏/logcat | `POST /api/devices/:id/screenshot`、`POST /api/devices/:id/screenrecord`、`GET /api/devices/:id/logcat`、Artifact Service | 通过 |
| 基础 UI 操作 | `POST /api/devices/:id/commands`，uiautomator2 语义定位优先；ADB 可用于 Home/Back/通知栏展开等系统级动作，也可在控件无法语义定位时显式启用像素坐标兜底；报告必须说明原因与风险 | 通过 |
| 测试执行 | `POST /api/test-runs`、pytest runner、device allocator、run 状态机 | 通过 |
| 报告与失败证据 | Allure Pytest、`artifacts` 表、`GET /api/test-runs/:id/artifacts`、Report Service | 通过 |
| 后续性能采集 | `GET /api/metrics`、metrics 表、dumpsys/top 采集器 | 通过，P1/P2 实现 |
| 后续音频链路 | `POST /api/audio-checks`、audio_checks 表、companion APK/外部闭环预留 | 通过，标记高成本专项 |
| 后续多设备并发 | `test_run_devices`、device_sessions、设备锁、`adb -s <serial>` 强制约束 | 通过，P2/P3 实现 |

结论：PRD 的 P0/P1/P2 能力在架构文档中均有对应模块、API 或数据模型，没有发现功能悬空。

### 3.2 架构技术约束是否有对应设计表达？

| 技术约束 | UIUX 对应设计 | 检查结果 |
|---|---|---|
| ADB-first、设备授权是前置条件 | 首次初始化页、设备清单、设备详情、ADB 未授权错误态 | 通过 |
| Windows 本机从 0 接入 | 初始化检查页展示 Java/Python/ADB/设备/端口/权限状态 | 通过 |
| 所有命令必须指定 serial | 设备详情、ADB 命令记录、设备指纹卡片、命令面板 | 通过 |
| 失败必须保留截图/logcat/UI XML | 报告详情页“步骤时间线 + 附件抽屉” | 通过 |
| logcat/命令输出需等宽字体 | JetBrains Mono / Fira Code token | 通过 |
| 多状态：online/offline/unauthorized/busy | Badge、状态色、设备健康热力图 | 通过 |
| 音频链路高成本且需专项 | 音频链路看板作为后续页面，未强塞 MVP | 通过 |
| Allure 每次 run 目录隔离 | 运行详情、报告中心按 run 展示，artifact 归档 | 通过 |

结论：架构约束在 UIUX 中都有对应页面、状态、组件或 Token 表达。

### 3.3 竞品定位与设计方向是否冲突？

| 来源 | 竞品/参考 | 方向 |
|---|---|---|
| PM | BrowserStack、Sauce Labs、AWS Device Farm、Firebase Test Lab、Perfecto、HeadSpin | 设备云、真机测试、报告、CI |
| 设计 | Datadog、Sentry、Grafana、BrowserStack、AWS Device Farm、Firebase Test Lab、Linear、Vercel、Apple HIG | 可观测性、排障、设备矩阵、克制精致 |
| 架构 | ADB/uiautomator2/pytest/Allure/FastAPI/React/PostgreSQL | 本地可控、渐进企业化 |

结论：不冲突。PM 侧重产品定位和竞品空白；设计侧重信息架构和可观测风格；架构侧重落地技术组合。三者共同指向“本地优先、设备实验室、测试执行、证据闭环、后续企业化”。

### 3.4 MVP 是否失焦？

UIUX 文档给出了完整企业平台 IA，但 PRD 和架构均明确 MVP 只落地：

1. 设备发现与体检。
2. 基础 UI 操作。
3. 截图/logcat/报告证据闭环。

设计中的 Observability、CI、Admin、多设备并发、音频看板等作为后续扩展，不进入首轮开发范围。

结论：MVP 未失焦。完整 IA 可作为长期蓝图，但开发 Spec 必须锁定 P0 范围。

---

## 4. 冲突与修正

本轮未发现需要退回专家重做的硬冲突。

需要在 Spec 阶段显式锁定的约束：

1. **MVP 只实现 P0**：设备扫描、体检、基础 UI 标杆用例、截图/logcat、报告。
2. **音频链路不进入 MVP P0**：仅保留数据模型/API 预留或后续专项说明，不能承诺第一版完成端到端音频质量验证。
3. **Appium 不作为第一驱动**：MVP 用 ADB + uiautomator2，Appium 作为后续企业兼容 adapter。
4. **STF/OpenSTF 不进入 Windows MVP**：后续 Linux 设备实验室再评估。
5. **所有真机命令必须 `adb -s <serial>`**：避免未来多设备时重构.
6. **像素坐标兜底必须明示**：默认语义定位优先；如果控件无法稳定语义定位但必须自动化，允许像素坐标兜底，必须在用例、日志和报告中标注原因、坐标、分辨率/方向、稳定性风险与后续可测试性改造建议。

---

## 5. 决策日志

```text
[12:06] Phase 1 - MVP 锁定三件事：ADB 设备体检、基础 UI 操作、报告证据闭环 - 用户要求先跑通简单真机操作再迭代 - 影响：音频/性能/多设备/CI 后移到 P1/P2/P3
[12:07] Phase 1 - 选择 ADB + uiautomator2 + pytest + Allure 作为 MVP 执行链路 - 架构师判断该组合最适合 Windows 本机从 0 快速跑通 - 影响：Appium 作为后续 adapter，不阻塞首轮落地
[12:08] Phase 1 - 选择 FastAPI + React/Ant Design + PostgreSQL 作为平台化组合 - 同语言后端与测试执行更易集成，企业扩展路径清晰 - 影响：MVP 可先做本地轻量版，后续接 DB/队列/设备池
[12:09] Phase 1 - 采用 A2 TestOps Console 设计方向 - 产品是内部测试与可观测平台，不是营销 SaaS - 影响：首页采用作战控制台而非 Hero Landing
[12:10] Phase 1 - 明确音频链路为高成本专项 - ADB 无法单独保证会议音频端到端质量 - 影响：P0 不承诺音频全链路，只预留后续 companion APK/外部声学闭环
[13:38] Phase 1 - 锁定语义定位优先 - 用户明确指出坐标定位非常不稳定 - 影响：Spec 与开发阶段点击/输入/断言默认采用稳定语义定位
[13:46] Phase 1 - 调整像素坐标为最后兜底而非禁用 - 用户要求不能因控件只能坐标触达而放弃自动化 - 影响：像素坐标兜底必须在用例、日志和报告中显式说明原因、坐标、分辨率/方向与风险
```

---

## 6. Phase 1 门禁结论

| 门禁项 | 结果 |
|---|---|
| 三位专家是否独立产出 | 通过 |
| PRD 是否明确 MVP 范围 | 通过 |
| 架构是否覆盖 PRD P0 功能 | 通过 |
| UIUX 是否覆盖技术约束与产品定位 | 通过 |
| 竞品/设计/技术方向是否一致 | 通过 |
| 是否存在必须退回重做的问题 | 无 |

**Phase 1 门禁结论：通过，等待用户确认三文档。**

---

## 7. 用户确认方式

如果你认可这三份文档，请回复：

```text
确认三文档
```

或直接回复：

```text
OK
```

收到确认后，我会自动进入 Phase 1.5，生成 Spec 规格契约，并继续推进：

1. Spec 锁定功能/API/DB/页面/Token/验收标准。
2. Phase 2 设计细化与 API/DB 细化。
3. Phase 3 先落地最小可运行代码，跑通 Windows + ADB + A2 真机基础闭环。
4. Phase 4 QA 测试与交付。

如果需要修改，请直接列出修改点；大改会回到 Phase 0，小改会更新三文档后再继续。
