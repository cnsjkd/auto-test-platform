import { Alert, Button, Descriptions, List } from 'antd';
import { RefreshCw, Terminal } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Device, Health } from '../api/types';
import { CodeBlock } from '../components/CodeBlock';
import { StatusBadge } from '../components/StatusBadge';

export function SetupPage() {
  const [health, setHealth] = useState<Health>();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [degraded, setDegraded] = useState(false);

  const detect = async () => {
    setLoading(true);
    const [healthResult, scanResult] = await Promise.all([api.health(), api.scanDevices()]);
    setHealth(healthResult.data);
    setDevices(scanResult.data.devices);
    setDegraded(Boolean(healthResult.degraded || scanResult.degraded));
    setLoading(false);
  };

  useEffect(() => {
    void detect();
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Setup</div>
          <h1 className="page-title">环境检测与 ADB 诊断</h1>
          <p className="page-description">验证 Python、ADB、artifact 目录与 A2 授权状态。后端不可用时展示降级诊断，不阻断前端 P0 闭环预览。</p>
        </div>
        <Button type="primary" loading={loading} icon={<RefreshCw size={16} />} onClick={detect}>重新检测</Button>
      </div>

      {degraded ? <Alert type="warning" showIcon message="当前为 degraded/mock 状态" description="未连接真实 FastAPI 后端，设备扫描结果来自本地预览数据。" style={{ marginBottom: 18 }} /> : null}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>检测清单</h2>
          <List
            dataSource={health?.checks ?? []}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>{item.label}<StatusBadge status={item.status} /></span>}
                  description={<span style={{ color: 'var(--text-secondary)' }}>{item.detail}{item.suggestion ? ` · ${item.suggestion}` : ''}</span>}
                />
              </List.Item>
            )}
          />
        </div>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>平台状态</h2>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="status">{health?.status ?? 'detecting'}</Descriptions.Item>
            <Descriptions.Item label="adbAvailable">{String(health?.adbAvailable ?? false)}</Descriptions.Item>
            <Descriptions.Item label="pythonVersion"><span className="mono">{health?.pythonVersion ?? '-'}</span></Descriptions.Item>
            <Descriptions.Item label="artifactRoot"><span className="mono">{health?.artifactRoot ?? '-'}</span></Descriptions.Item>
          </Descriptions>
        </div>
      </div>

      <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>设备授权指引</h2>
          <List
            dataSource={[
              '打开 A2 开发者选项并启用 USB 调试',
              '使用数据线连接 Windows 本机，等待 RSA 授权弹窗',
              '选择允许当前电脑调试后重新扫描设备',
              '若状态仍为 unauthorized，执行 adb kill-server 后重新插拔设备',
            ]}
            renderItem={(item) => <List.Item style={{ color: 'var(--text-secondary)' }}>{item}</List.Item>}
          />
        </div>
        <CodeBlock
          title="ADB 诊断命令"
          code={`adb devices -l\nadb -s <serial> shell getprop ro.build.version.release\nadb -s <serial> shell wm size\nadb -s <serial> logcat -d -t 200`}
        />
      </div>

      <div className="console-card" style={{ marginTop: 18, padding: 16 }}>
        <h2 style={{ marginTop: 0 }}><Terminal size={18} /> 扫描结果</h2>
        <List
          dataSource={devices}
          renderItem={(device) => (
            <List.Item>
              <List.Item.Meta title={<span className="mono">{device.serial}</span>} description={`${device.model} · Android ${device.androidVersion} · ${device.screenWidth}x${device.screenHeight} · ${device.storage}`} />
              <StatusBadge status={device.status} />
            </List.Item>
          )}
        />
      </div>
    </div>
  );
}
