import { Alert, Button, Descriptions, List, Space, Tag, Timeline, message } from 'antd';
import { Camera, FileCode2, Home, ListTree, PanelTopOpen, RotateCcw, Settings2, TerminalSquare, Zap } from 'lucide-react';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Action, Artifact, Device, DeviceCommandResult } from '../api/types';
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
