# UIUX 文档：A2 TestOps Console v0.1

> 责任专家：颜好看（设计）  
> 项目：思必驰会议办公本 A2 自动化测试平台  
> 阶段：Phase 1  
> 状态：待确认  
> 日期：2026-06-30

---

## 1. 产品类型识别

本项目不是营销型 SaaS 官网，而是企业内部拥有的“设备实验室 + 自动化测试调度 + 真机远程调试 + 测试报告 + 可观测性平台”。

核心使用者：

- 测试开发
- QA
- Android 工程师
- 音频算法/设备链路工程师
- 研发管理者
- CI 维护者

设计关键词：专业、可靠、可观测、可扩展、数据密集、低噪声、面向排障。

---

## 2. 同类产品信息架构调研结论

### BrowserStack App Automate

- 典型结构：项目/应用构建、设备选择、自动化会话、实时日志、截图、视频、性能指标、CI 集成、调试报告。
- 可借鉴：测试会话是核心对象，围绕 session 聚合 video、logs、screenshots、metrics、capabilities、framework 信息。
- 避免照抄：不做营销感强的首页；内部平台首页应直接进入运行态和设备态。

### Firebase Test Lab

- 典型结构：测试矩阵、设备型号、系统版本、语言区域、屏幕方向、测试历史、结果详情、日志与截图。
- 可借鉴：矩阵思维适合 A2 后续扩展多设备、多系统、多配置。

### AWS Device Farm

- 典型结构：项目、设备池、测试运行、远程访问、私有设备、运行产物、日志、截图、视频、CI/API 集成。
- 可借鉴：设备池、私有设备、排队/并发槽位、运行产物保留策略应成为一等信息。

### OpenSTF / DeviceFarmer

- 典型结构：设备列表、远程屏幕控制、设备占用、ADB shell、logcat、截图、安装 APK、网络/电量等状态。
- 可借鉴：Device Lab 页面应是平台底座。

### Allure Report

- 典型结构：Overview、Categories、Suites、Graphs、Timeline、Behaviors、Packages、附件、步骤、重试、历史趋势。
- 可借鉴：测试报告详情页采用“用例树 + 步骤时间线 + 附件抽屉 + 失败分类”。

### Grafana / Datadog / Sentry

- 典型结构：Dashboard、Panel、变量筛选、时间范围、注释、告警、日志/指标/链路统一检索、错误聚类、发布关联。
- 可借鉴：质量看板应支持按项目、分支、构建、设备组、时间范围过滤，并把失败与设备状态、性能、日志关联。

---

## 3. 对标品牌与设计语言

### 对标品牌组合

- 主对标：Datadog、Sentry、Grafana，用于可观测性、故障聚类、日志/指标/链路统一视图。
- 流程对标：BrowserStack、AWS Device Farm、Firebase Test Lab，用于设备池、测试矩阵、会话产物、CI 集成。
- 视觉打磨对标：Linear、Vercel、Apple HIG，用于信息层级、留白、动效克制、细节质感。

### 设计语言方向

建议命名为 **A2 TestOps Console**。

整体风格：深色工作台 + 高密度数据表 + 清晰状态色 + 真实运行产物。

避免：口号型首页、抽象装饰图形、营销型 SaaS Hero。

设计原则：

- 信息先于装饰：页面视觉中心是设备、运行、报告、告警。
- 状态一眼可辨：设备在线、占用、离线、授权失败、运行中、失败、阻塞都用一致 Badge 和图标。
- 调试路径短：失败详情页必须能在 1 次点击内看到截图、视频、logcat、ADB 命令、性能曲线。
- 真实内容驱动：空状态给具体下一步。

---

## 4. 图标系统与字体系统

### 图标系统

唯一图标库：Lucide。

尺寸规范：

- 16px：表格行内、状态标签、辅助操作。
- 20px：按钮内、导航项、工具栏操作。
- 24px：页面标题、空状态、关键模块入口。

建议图标映射：

- 设备：Smartphone、Tablet、MonitorSmartphone
- 运行：Play、Square、RotateCcw、Clock
- 结果：CheckCircle、XCircle、AlertTriangle、CircleSlash
- 调试：Terminal、FileSearch、Bug、Activity
- 音频：Mic、Volume2、AudioLines
- 性能：Gauge、Cpu、MemoryStick、BatteryCharging
- 看板：LayoutDashboard、ChartNoAxesCombined、Bell
- 管理：Settings、ShieldCheck、KeyRound、Users

禁止 emoji 作为功能图标。

### 字体系统

- Display / Body：Inter + Noto Sans SC + -apple-system + sans-serif
- Mono：JetBrains Mono + Fira Code + monospace

字号层级：

- 32px：页面标题，如“设备实验室”“运行详情”。
- 24px：模块标题，如“设备健康”“失败分类”。
- 20px：卡片标题、抽屉标题。
- 18px：关键指标数值辅助层级。
- 16px：正文与表单主输入。
- 14px：表格、导航、按钮、常规 UI 文本。
- 12px：元信息、时间戳、日志标签、辅助说明。

等宽字体使用边界：ADB 命令、logcat、设备序列号、构建号、用例 ID、JSON/环境变量、错误堆栈。

---

## 5. 信息架构

### 一级导航

1. **Command Center 控制台**：质量概览、活跃运行、队列压力、设备健康、最新失败、质量门禁。
2. **Device Lab 设备实验室**：设备清单、设备组、设备详情、远程控制、ADB 授权、占用/预约、健康检查、基线采集。
3. **Test Assets 测试资产**：App 包、测试套件、测试用例、数据集、脚本/关键字、音频样本、基线截图。
4. **Run Center 运行中心**：创建测试矩阵、运行队列、计划任务、执行历史、重跑、对比、取消/暂停。
5. **Live Debug 实时调试**：设备画面、键鼠/触控操作、ADB Shell、logcat、截图、录屏、音频链路监控。
6. **Reports 报告中心**：Allure 风格报告、失败分类、用例树、步骤时间线、附件、导出、历史趋势。
7. **Observability 可观测性**：质量看板、性能看板、稳定性看板、音频看板、告警中心、事件注释。
8. **CI & Integrations 集成**：Jenkins、GitHub Actions、GitLab CI、Webhook、CLI/API Token、质量门禁、回调日志。
9. **Admin 管理**：用户与角色、权限、审计日志、设备池配额、密钥、数据保留、平台设置。

### 全局结构

- 左侧持久导航：支持折叠，显示模块图标与运行状态微提示。
- 顶部栏：项目切换、全局搜索、时间范围、环境选择、通知、用户菜单。
- 右侧检查器：用于设备详情、运行详情、失败附件、告警上下文，避免频繁跳页。
- 命令面板：支持键盘快速跳转设备、运行、用例、报告、ADB 命令模板。

---

## 6. 页面清单

### 基础平台页

1. 登录页
2. 首次初始化页
3. 项目/工作区选择页

### 设备实验室

4. 设备清单页
5. 设备详情页
6. 设备组管理页

### 测试与运行

7. 测试资产页
8. 创建运行页
9. 运行队列页
10. 运行详情页
11. 失败排障页

### 报告与看板

12. 报告中心页
13. 质量看板页
14. 设备健康看板页
15. 性能与稳定性看板页
16. 音频链路看板页

### 集成与管理

17. CI 集成页
18. 告警中心页
19. 用户权限页

---

## 7. 核心工作流

### 工作流 A：首次接入 A2 真机

1. Windows 本机检测 ADB 环境。
2. 平台发现设备并读取序列号、型号、系统版本、电量、存储、分辨率。
3. 执行 ADB 授权和健康检查。
4. 自动生成设备指纹卡片。
5. 设备进入 Device Lab，并可被运行矩阵选择。

关键 UI：初始化检查页、设备清单、设备详情抽屉、健康检查时间线。

### 工作流 B：跑通基础真机操作

1. 用户选择 A2 设备。
2. 创建“基础真机操作检查”运行。
3. 平台执行唤醒、解锁、下拉通知栏、点击下拉项、截图、录屏、logcat 采集。
4. 运行详情展示每一步结果、截图、耗时、失败点。
5. 成功后生成“设备基础能力已验证”的基线记录。

关键 UI：快速运行按钮、步骤时间线、屏幕截图对比、ADB 命令记录。

### 工作流 C：创建自动化测试矩阵

1. 选择构建或系统测试任务。
2. 选择 UI 自动化、接口/设备命令、音频链路、稳定性、性能采集、兼容性等套件。
3. 选择设备组、并发策略、重试策略、超时策略。
4. 设置质量门禁。
5. 提交后进入运行队列。

### 工作流 D：失败排障

1. 从 Command Center 或报告中心进入失败运行。
2. 先看失败聚类和首个失败步骤。
3. 同屏查看截图、视频、logcat、ADB 命令、性能曲线、设备健康。
4. 支持标记为产品缺陷、脚本缺陷、设备异常、环境问题、flaky。
5. 支持一键重跑失败用例或开启 Live Debug。

### 工作流 E：CI 质量门禁

1. CI 触发平台运行。
2. 平台在设备池排队并执行。
3. 回传通过率、失败详情、报告链接、质量门禁结果。
4. 平台保留历史趋势和构建注释。

---

## 8. 组件规范

### Atoms

- Button：primary、secondary、ghost、danger、icon-only。
- Input / Select / Combobox：支持错误、帮助文本、清除、键盘导航。
- Badge：设备状态、运行状态、失败类型、权限级别。
- Icon：Lucide-only，统一尺寸和 stroke。
- Spinner / Skeleton：用于运行中、日志加载、报告生成。
- Tooltip：说明不可操作原因、指标定义、缩写解释。

### Molecules

- DeviceCard：设备名、序列号、状态、电量、占用者、健康分、快捷操作。
- RunStatusPill：queued、running、passed、failed、cancelled、blocked。
- MetricCard：数值、趋势、阈值、时间范围。
- FilterBar：项目、分支、构建、设备组、时间范围、状态。
- LogStream：logcat/平台日志，支持级别、关键字、时间定位。
- ArtifactPreview：截图、视频、音频、文本、JSON、HTML 报告。
- TimelineStep：步骤名称、状态、耗时、附件、错误摘要。

### Organisms

- Sidebar：模块导航、运行态微提示、折叠模式。
- DeviceGrid / DeviceTable：设备库存主视图。
- MatrixBuilder：测试矩阵创建器。
- RunTable：运行列表、队列、批量操作。
- ReportViewer：Allure-like 报告容器。
- LiveDeviceConsole：屏幕、控制、ADB、logcat、性能同屏。
- DashboardPanel：统一看板面板容器，支持刷新、导出、阈值说明。

### Templates

- ConsoleLayout：控制台、设备、运行中心通用布局。
- SplitInspectionLayout：列表 + 右侧详情检查器。
- LiveDebugLayout：左设备屏幕，右日志/命令，下方时间线。
- ReportLayout：顶部摘要，左用例树，中间详情，右附件。
- DashboardLayout：变量筛选 + KPI + 多 Panel 看板。

### 状态矩阵

所有核心交互组件必须覆盖：Default、Hover、Focus、Active、Disabled、Loading、Error、Empty、Success。

重点要求：

- Focus 使用 2px focus-visible ring。
- Disabled 必须说明原因，例如“设备被占用”“ADB 未授权”。
- Loading 对长任务显示队列位置、预计等待、取消入口。
- Empty 给行动建议，不写空洞文案。
- Error 给可恢复动作，例如重试、查看日志、复制诊断信息。

---

## 9. Design Token 体系

说明：UI 实现时不得直接写原始色值，组件只引用语义 Token；原始色值仅允许出现在 Foundation Token 定义中。

### Foundation Token

颜色：

- `--color-ink-950`: `#0D1117`
- `--color-ink-900`: `#111827`
- `--color-slate-800`: `#1F2937`
- `--color-slate-700`: `#374151`
- `--color-slate-500`: `#6B7280`
- `--color-slate-400`: `#9CA3AF`
- `--color-slate-200`: `#E5E7EB`
- `--color-slate-50`: `#F9FAFB`
- `--color-blue-600`: `#2563EB`
- `--color-blue-500`: `#3B82F6`
- `--color-cyan-600`: `#0891B2`
- `--color-green-600`: `#16A34A`
- `--color-amber-600`: `#D97706`
- `--color-red-600`: `#DC2626`
- `--color-white`: `#fff`

间距：4/8/12/16/20/24/32/40/48/64/80。

圆角：

- `--radius-sm`: 4px
- `--radius-md`: 8px
- `--radius-lg`: 12px

动效：

- `--duration-fast`: 150ms
- `--duration-normal`: 250ms
- `--duration-slow`: 400ms
- `--easing-standard`: cubic-bezier(0.4, 0, 0.2, 1)

### Semantic Token

- `--bg-app`: `var(--color-ink-950)`
- `--bg-surface`: `var(--color-ink-900)`
- `--bg-elevated`: `var(--color-slate-800)`
- `--bg-muted`: `var(--color-slate-700)`
- `--text-primary`: `var(--color-slate-50)`
- `--text-secondary`: `var(--color-slate-400)`
- `--text-muted`: `var(--color-slate-500)`
- `--border-default`: `var(--color-slate-700)`
- `--border-subtle`: `var(--color-slate-800)`
- `--border-focus`: `var(--color-blue-600)`
- `--color-primary`: `var(--color-blue-600)`
- `--color-primary-hover`: `var(--color-blue-500)`
- `--color-info`: `var(--color-cyan-600)`
- `--color-success`: `var(--color-green-600)`
- `--color-warning`: `var(--color-amber-600)`
- `--color-error`: `var(--color-red-600)`

---

## 10. 可视化看板设计

### Command Center 控制台

第一屏结构：

- 顶部 KPI：设备在线率、活跃运行、今日通过率、失败聚类数、队列 P95 等待、CI 门禁失败数。
- 中部左侧：活跃运行列表，显示套件、设备、进度、预计剩余、失败首因。
- 中部右侧：设备健康热力图，按设备组和状态聚合。
- 底部：最新失败、最新报告、告警、CI 回调异常。

### 设备健康看板

- 设备 x 健康指标热力图：在线、授权、电量、温度、存储、网络、占用率。
- 异常设备排行：离线次数、ADB 断连、授权失败、执行失败率。
- 点击热力格打开设备详情抽屉。

### 运行质量看板

- 通过率趋势、失败率趋势、flaky 率、平均耗时、P95 耗时。
- 失败分类：脚本问题、产品缺陷、设备异常、环境问题、未知。
- 用例稳定性排行：连续失败、偶发失败、最长耗时、最高重试。

### 音频链路看板

- 录音链路可用性、输入电平、播放/录制延迟、音频样本比对、异常片段数量。
- 将音频异常与测试步骤、logcat、设备状态对齐到同一时间线。
- 音频附件支持波形预览和片段定位。

### 报告详情页

- 顶部：运行状态、通过率、总耗时、设备矩阵、质量门禁。
- 左侧：Suite / Case 树。
- 中间：步骤时间线、错误摘要、历史对比。
- 右侧：附件抽屉，支持截图、视频、音频、logcat、性能片段、ADB 命令。
- 底部：重试记录、关联运行、CI 回调记录。

---

## 11. 交互边界与可访问性

### 可访问性

- 所有按钮、菜单、Tabs、表格行操作必须键盘可达。
- 所有交互控件提供可见 focus-visible 状态。
- 图标按钮必须有文本标签或 aria-label。
- 正文对比度目标不低于 4.5:1。
- 日志颜色不能只靠颜色区分，需同时显示级别文本。

### 动效

- 常规过渡 150ms 到 250ms。
- 页面/抽屉进入不超过 400ms。
- 支持 prefers-reduced-motion。
- 禁止弹跳/弹性缓动。

### 错误与边界状态

- 设备离线：显示最后在线时间、最近失败命令、重新检测入口。
- ADB 未授权：显示原因、检测步骤、重新握手入口。
- 设备被占用：显示占用者、预计释放、申请接管入口。
- 运行排队：显示队列位置、并发槽位、预计开始。
- 日志过大：默认截断并提供下载完整日志。
- 报告生成中：显示进度、已完成产物、失败可重试。
- 权限不足：说明缺失权限，不只显示禁用按钮。

### 空状态文案方向

- 设备空状态：未检测到 A2 设备。连接设备并完成 ADB 授权后，平台会自动执行健康检查。
- 运行空状态：还没有运行记录。先创建“基础真机操作检查”，验证下拉框、截图和日志采集链路。
- 报告空状态：暂无报告。完成一次运行后，截图、视频、logcat 和性能数据会在这里归档。
- 看板空状态：当前筛选条件没有数据。调整时间范围或选择包含运行记录的设备组。

---

## 12. 提交前红线自查

- 无紫色渐变，不使用 `#7C3AED`、`#A855F7`、`#9333EA`、`#EC4899`。
- 无 emoji 功能图标，统一 Lucide。
- 无 Lorem ipsum、无 “Welcome to”、无空洞占位。
- 字体已冻结：Inter + Noto Sans SC + JetBrains Mono。
- 颜色使用三层 Design Token，组件不直接引用原始色值。
- 间距使用 4px 基准网格。
- 按钮与核心组件覆盖 Default、Hover、Focus、Active、Disabled、Loading、Error、Empty、Success。
- Hero 模式已规避，首页为真实运行控制台。
- 可访问性交互已覆盖 focus-visible、键盘可达、prefers-reduced-motion。
- 可视化围绕设备、运行、报告、性能、音频链路，适配企业内部测试平台。

---

## 13. 共享内存池写入

### 设计方向

A2 TestOps Console，定位为企业内部“ADB-first 真机自动化测试 + 设备实验室 + 可观测性 + 报告中心”平台；采用深色专业工作台、数据密集布局、真实运行产物驱动，不做营销型 SaaS Hero。

### 对标品牌

Datadog、Sentry、Grafana 作为可观测性与故障排查参考；BrowserStack、AWS Device Farm、Firebase Test Lab 作为设备云/测试矩阵/运行产物参考；Linear、Vercel、Apple HIG 作为视觉精致度与交互克制参考。

### 配色基调

Navy / Graphite 深色底，Cobalt Blue 作为主操作色，Green / Amber / Red 作为状态色，Cyan 作为信息辅助色；通过 Design Token 使用，禁止紫色渐变和硬编码组件色值。
