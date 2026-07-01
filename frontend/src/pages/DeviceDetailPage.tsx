import { Alert, Button, Descriptions, List, Space, Tag, Timeline, message } from 'antd';
import { Camera, FileCode2, Home, ListTree, PanelTopOpen, RotateCcw, Settings2, TerminalSquare, Zap } from 'lucide-react';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Action, Artifact, Device, DeviceCommandResult, FlowRunResponse, FlowStepResult } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { StatusBadge } from '../components/StatusBadge';

type EvidenceAction = 'screenshot' | 'dump' | 'logcat';
type VisibleAction = 'home' | 'notification' | 'quick_settings' | 'back' | 'visible_demo';

interface ActionHistoryItem {
  id: string;
  label: string;
  status: 'success' | 'failed';
  time: string;
  command?: DeviceCommandResult;
  artifactCount: number;
}

const safeFlowSteps = [
  { id: 'home', name: '回到主页', action: 'keyevent' as const, params: { key: 'HOME' }, description: '发送 HOME 键，确保从稳定起点开始。' },
  { id: 'notification', name: '展开通知栏', action: 'open_notification' as const, description: '打开系统通知栏，验证 ADB 可见动作链路。' },
  { id: 'quick-settings', name: '展开快捷设置', action: 'open_quick_settings' as const, description: '展开快捷设置面板，验证连续系统动作。' },
  { id: 'back-quick-settings', name: '返回关闭快捷设置', action: 'keyevent' as const, params: { key: 'BACK' }, description: '发送 BACK 键关闭当前面板。' },
  { id: 'back-notification', name: '返回关闭通知栏', action: 'keyevent' as const, params: { key: 'BACK' }, description: '再次发送 BACK 键回到初始状态。' },
];

const statusColor = (status?: string) => {
  if (status === 'success' || status === 'passed') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'running') return 'processing';
  return 'default';
};

const visibleActions: Array<{
  key: VisibleAction;
  label: string;
  description: string;
  commandLabel: string;
  icon: ReactNode;
}> = [
  {
    key: 'home',
    label: '回到主页',
    description: '发送 HOME 键，肉眼应看到设备返回桌面或主界面。',
    commandLabel: 'keyevent HOME',
    icon: <Home size={16} />,
  },
  {
    key: 'notification',
    label: '展开通知栏',
    description: '执行系统通知栏下拉，屏幕上应出现通知面板。',
    commandLabel: 'open_notification',
    icon: <PanelTopOpen size={16} />,
  },
  {
    key: 'quick_settings',
    label: '展开快捷设置',
    description: '执行快捷设置展开，屏幕上应出现快捷设置面板。',
    commandLabel: 'open_quick_settings',
    icon: <Settings2 size={16} />,
  },
  {
    key: 'back',
    label: '返回',
    description: '发送 BACK 键，关闭当前面板或返回上一层。',
    commandLabel: 'keyevent BACK',
    icon: <RotateCcw size={16} />,
  },
  {
    key: 'visible_demo',
    label: '可见演示：通知栏→快捷设置→返回',
    description: '连续执行一组安全动作，并在动作后自动采集截图证据。',
    commandLabel: 'open_notification + open_quick_settings + BACK',
    icon: <Zap size={16} />,
  },
];

export function DeviceDetailPage() {
  const { id = '' } = useParams();
  const [device, setDevice] = useState<Device>();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [history, setHistory] = useState<ActionHistoryItem[]>([]);
  const [loadingAction, setLoadingAction] = useState<string>();
  const [flowRun, setFlowRun] = useState<FlowRunResponse>();
  const [runningFlow, setRunningFlow] = useState(false);
  const [flowError, setFlowError] = useState<string>();
  const [flowDegraded, setFlowDegraded] = useState(false);

  useEffect(() => {
    void api.getDevice(id).then((result) => setDevice(result.data.device));
  }, [id]);

  const latestScreenshot = useMemo(() => artifacts.find((artifact) => artifact.type === 'screenshot'), [artifacts]);

  const appendHistory = (item: Omit<ActionHistoryItem, 'id' | 'time'>) => {
    setHistory((items) => [
      {
        ...item,
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        time: new Date().toLocaleTimeString(),
      },
      ...items,
    ]);
  };

  const appendArtifacts = (nextArtifacts: Artifact[]) => {
    if (nextArtifacts.length > 0) {
      setArtifacts((items) => [...nextArtifacts, ...items]);
    }
  };

  const runAction = async (action: EvidenceAction) => {
    if (!device) return;
    setLoadingAction(action);
    try {
      const result = action === 'screenshot' ? await api.screenshot(device.id) : action === 'dump' ? await api.dumpHierarchy(device.id) : await api.logcatSnapshot(device.id);
      setArtifacts((items) => [result.data.artifact, ...items]);
      appendHistory({ label: action === 'screenshot' ? '采集截图' : action === 'dump' ? '采集 UI XML' : '采集 logcat', status: 'success', artifactCount: 1 });
      message.success('已生成真实 artifact 证据');
    } catch (error) {
      appendHistory({ label: '证据采集失败', status: 'failed', artifactCount: 0 });
      message.error(error instanceof Error ? error.message : '证据采集失败');
    } finally {
      setLoadingAction(undefined);
    }
  };

  const sendCommand = async (action: Action, params?: Record<string, string | number | boolean | string[]>) => {
    if (!device) return undefined;
    const result = await api.deviceCommand(device.id, { action, params });
    appendArtifacts(result.data.artifacts ?? []);
    return result.data;
  };

  const captureAfterAction = async () => {
    if (!device) return undefined;
    const result = await api.screenshot(device.id);
    appendArtifacts([result.data.artifact]);
    return result.data.artifact;
  };

  const runFlow = async () => {
    if (!device) return;
    setRunningFlow(true);
    setFlowError(undefined);
    setFlowDegraded(false);
    try {
      const result = await api.runFlow({
        deviceId: device.id,
        flowId: 'a2-safe-system-panel-flow',
        name: 'A2 安全系统面板流程',
        steps: safeFlowSteps,
        captureArtifacts: true,
      });
      setFlowRun(result.data);
      appendArtifacts(result.data.artifacts);
      setFlowDegraded(Boolean(result.degraded));
      appendHistory({
        label: 'message' in result.data.run && result.data.run.message ? result.data.run.message : 'A2 安全系统面板流程',
        status: result.data.run.status === 'failed' ? 'failed' : 'success',
        artifactCount: result.data.artifacts.length,
      });
      message.success(result.degraded ? '后端不可用，已展示本地流程预览' : '流程已执行完成');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '流程执行失败';
      setFlowError(errorMessage);
      appendHistory({ label: '流程编排运行失败', status: 'failed', artifactCount: 0 });
      message.error(errorMessage);
    } finally {
      setRunningFlow(false);
    }
  };

  const flowStepById = useMemo(() => {
    const map = new Map<string, FlowStepResult>();
    flowRun?.steps.forEach((step) => map.set(step.id, step));
    return map;
  }, [flowRun]);

  const runVisibleAction = async (action: VisibleAction) => {
    if (!device) return;
    setLoadingAction(action);
    try {
      const commands: DeviceCommandResult[] = [];
      if (action === 'home') {
        const result = await sendCommand('keyevent', { key: 'HOME' });
        if (result?.command) commands.push(result.command);
      }
      if (action === 'notification') {
        const result = await sendCommand('open_notification');
        if (result?.command) commands.push(result.command);
      }
      if (action === 'quick_settings') {
        const result = await sendCommand('open_quick_settings');
        if (result?.command) commands.push(result.command);
      }
      if (action === 'back') {
        const result = await sendCommand('keyevent', { key: 'BACK' });
        if (result?.command) commands.push(result.command);
      }
      if (action === 'visible_demo') {
        for (const command of [
          { action: 'keyevent' as Action, params: { key: 'HOME' } },
          { action: 'open_notification' as Action },
          { action: 'open_quick_settings' as Action },
          { action: 'keyevent' as Action, params: { key: 'BACK' } },
          { action: 'keyevent' as Action, params: { key: 'BACK' } },
        ]) {
          const result = await sendCommand(command.action, command.params);
          if (result?.command) commands.push(result.command);
        }
      }

      const screenshot = await captureAfterAction();
      const visibleAction = visibleActions.find((item) => item.key === action);
      appendHistory({
        label: visibleAction?.label ?? action,
        status: 'success',
        command: commands.length > 0 ? commands[commands.length - 1] : undefined,
        artifactCount: screenshot ? 1 : 0,
      });
      message.success('真机动作已执行，并已采集动作后截图');
    } catch (error) {
      const visibleAction = visibleActions.find((item) => item.key === action);
      appendHistory({ label: `${visibleAction?.label ?? action}失败`, status: 'failed', artifactCount: 0 });
      message.error(error instanceof Error ? error.message : '真机动作执行失败');
    } finally {
      setLoadingAction(undefined);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Device Inspector</div>
          <h1 className="page-title">设备详情与真机操作台</h1>
          <p className="page-description">直接对 A2 执行肉眼可见的安全动作，并自动采集截图、UI XML、logcat 等证据。所有动作由后端使用 serial 定向到真实设备。</p>
        </div>
        {device ? <StatusBadge status={device.status} /> : null}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 18 }}>
        <div style={{ display: 'grid', gap: 18 }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>设备指纹</h2>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Serial"><span className="mono">{device?.serial}</span></Descriptions.Item>
              <Descriptions.Item label="Model">{device?.model}</Descriptions.Item>
              <Descriptions.Item label="Android">{device?.androidVersion} / SDK {device?.sdkInt}</Descriptions.Item>
              <Descriptions.Item label="Resolution"><span className="mono">{device?.screenWidth}x{device?.screenHeight}</span></Descriptions.Item>
              <Descriptions.Item label="Density"><span className="mono">{device?.density}</span></Descriptions.Item>
              <Descriptions.Item label="Battery">{device?.battery}%</Descriptions.Item>
              <Descriptions.Item label="Network">{device?.network}</Descriptions.Item>
              <Descriptions.Item label="Storage">{device?.storage}</Descriptions.Item>
              <Descriptions.Item label="Last Seen"><span className="mono">{device?.lastSeenAt}</span></Descriptions.Item>
            </Descriptions>
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>可见真机操作</h2>
            <Alert
              type="info"
              showIcon
              message="这些按钮会直接控制已连接 A2"
              description="建议你看着真机屏幕点击：通知栏、快捷设置、返回等动作应能肉眼看到变化；每个动作完成后会自动采一张截图作为证据。"
              style={{ marginBottom: 14 }}
            />
            <div style={{ display: 'grid', gap: 10 }}>
              {visibleActions.map((item) => (
                <Button
                  key={item.key}
                  loading={loadingAction === item.key}
                  icon={item.icon}
                  onClick={() => runVisibleAction(item.key)}
                  disabled={!device || device.status !== 'online'}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>证据采集</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              <Button type="primary" loading={loadingAction === 'screenshot'} icon={<Camera size={16} />} onClick={() => runAction('screenshot')}>采集截图</Button>
              <Button loading={loadingAction === 'dump'} icon={<ListTree size={16} />} onClick={() => runAction('dump')}>采集 UI XML</Button>
              <Button loading={loadingAction === 'logcat'} icon={<TerminalSquare size={16} />} onClick={() => runAction('logcat')}>采集 logcat</Button>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gap: 18 }}>
          <div className="console-card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div>
                <h2 style={{ marginTop: 0 }}>流程编排运行</h2>
                <p style={{ color: 'var(--text-secondary)', margin: '0 0 12px' }}>内置安全流程：HOME -&gt; 通知栏 -&gt; 快捷设置 -&gt; BACK -&gt; BACK。后端不可用时展示本地预览，参数校验错误会直接显示。</p>
              </div>
              <Button type="primary" loading={runningFlow} disabled={!device || device.status !== 'online'} icon={<Zap size={16} />} onClick={runFlow}>
                执行流程
              </Button>
            </div>
            <Space wrap style={{ marginBottom: 12 }}>
              <Tag color={statusColor(flowRun?.run.status)}>{flowRun?.run.status ?? 'idle'}</Tag>
              <Tag>artifact：{flowRun?.artifacts.length ?? 0} 个</Tag>
              {flowRun?.run.id ? <Tag className="mono">{flowRun.run.id}</Tag> : null}
            </Space>
            {flowDegraded ? <Alert type="warning" showIcon message="后端流程 API 不可用，当前为本地 mock 预览" style={{ marginBottom: 12 }} /> : null}
            {flowError ? <Alert type="error" showIcon message="流程执行失败" description={flowError} style={{ marginBottom: 12 }} /> : null}
            <List
              dataSource={safeFlowSteps}
              renderItem={(step, index) => {
                const result = flowStepById.get(step.id);
                const screenshot = result?.artifacts.find((artifact) => artifact.type === 'screenshot');
                return (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Tag className="mono">{index + 1}</Tag>}
                      title={(
                        <Space wrap>
                          <span>{step.name}</span>
                          <Tag>{step.action === 'keyevent' ? `keyevent ${step.params?.key}` : step.action}</Tag>
                          <Tag color={statusColor(result?.status)}>{result?.status ?? 'pending'}</Tag>
                        </Space>
                      )}
                      description={(
                        <div style={{ display: 'grid', gap: 8 }}>
                          <span>{result?.message ?? step.description}</span>
                          <span className="mono" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                            artifact：{result?.artifacts.length ?? 0} 个{result?.durationMs ? ` · ${result.durationMs}ms` : ''}
                          </span>
                          {screenshot ? (
                            <div style={{ width: 180, border: '1px solid var(--border-default)', borderRadius: 'var(--radius-card)', background: 'var(--bg-elevated)', color: 'var(--text-secondary)', padding: 10 }}>
                              <img
                                src={`/api/artifacts/${screenshot.id}/download`}
                                alt={screenshot.meta?.title ?? screenshot.path}
                                style={{ display: 'block', width: '100%', height: 96, objectFit: 'contain', borderRadius: 'var(--radius-button)' }}
                              />
                              <span style={{ display: 'block', marginTop: 6, textAlign: 'center' }}>{screenshot.meta?.title ?? screenshot.path}</span>
                            </div>
                          ) : null}
                        </div>
                      )}
                    />
                  </List.Item>
                );
              }}
            />
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>动作说明</h2>
            <List
              dataSource={visibleActions}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={item.icon}
                    title={<Space><span>{item.label}</span><Tag>{item.commandLabel}</Tag></Space>}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>最近动作</h2>
            {history.length === 0 ? (
              <List dataSource={['点击左侧“可见真机操作”按钮后，这里会记录命令、结果和证据数量。']} renderItem={(item) => <List.Item style={{ color: 'var(--text-secondary)' }}>{item}</List.Item>} />
            ) : (
              <Timeline
                items={history.map((item) => ({
                  color: item.status === 'success' ? 'green' : 'red',
                  children: (
                    <div>
                      <Space wrap>
                        <strong>{item.label}</strong>
                        <Tag color={item.status === 'success' ? 'success' : 'error'}>{item.status}</Tag>
                        <span className="mono">{item.time}</span>
                      </Space>
                      <div style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                        artifact：{item.artifactCount} 个{item.command?.message ? `；${item.command.message}` : ''}
                      </div>
                    </div>
                  ),
                }))}
              />
            )}
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}><FileCode2 size={18} /> Artifact 操作结果</h2>
            {latestScreenshot ? (
              <Alert type="success" showIcon message="最新截图已采集" description="请打开下方 screenshot artifact 对照真机屏幕，确认动作后的设备状态。" style={{ marginBottom: 14 }} />
            ) : null}
            {artifacts.length === 0 ? (
              <List dataSource={['点击左侧动作按钮生成截图、UI XML 或 logcat artifact', '真实执行失败时应保留错误原因与设备状态', '可见演示会自动追加动作后截图']} renderItem={(item) => <List.Item style={{ color: 'var(--text-secondary)' }}>{item}</List.Item>} />
            ) : (
              <div style={{ display: 'grid', gap: 14 }}>
                {artifacts.map((artifact) => <ArtifactPreview key={artifact.id} artifact={artifact} />)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
