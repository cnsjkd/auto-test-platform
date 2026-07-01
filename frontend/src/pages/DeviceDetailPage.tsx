import { Button, Descriptions, List, message } from 'antd';
import { Camera, FileCode2, ListTree, TerminalSquare } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Artifact, Device } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { StatusBadge } from '../components/StatusBadge';

export function DeviceDetailPage() {
  const { id = '' } = useParams();
  const [device, setDevice] = useState<Device>();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loadingAction, setLoadingAction] = useState<string>();

  useEffect(() => {
    void api.getDevice(id).then((result) => setDevice(result.data.device));
  }, [id]);

  const runAction = async (action: 'screenshot' | 'dump' | 'logcat') => {
    if (!device) return;
    setLoadingAction(action);
    const result = action === 'screenshot' ? await api.screenshot(device.id) : action === 'dump' ? await api.dumpHierarchy(device.id) : await api.logcatSnapshot(device.id);
    setArtifacts((items) => [result.data.artifact, ...items]);
    message.success('已生成本地 artifact 预览');
    setLoadingAction(undefined);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Device Inspector</div>
          <h1 className="page-title">设备详情与证据采集</h1>
          <p className="page-description">执行截图、UI XML、logcat 快照等 P0 证据动作；所有 ADB 真实动作由后端保证使用 serial 定向。</p>
        </div>
        {device ? <StatusBadge status={device.status} /> : null}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 18 }}>
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
          <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
            <Button type="primary" loading={loadingAction === 'screenshot'} icon={<Camera size={16} />} onClick={() => runAction('screenshot')}>采集截图</Button>
            <Button loading={loadingAction === 'dump'} icon={<ListTree size={16} />} onClick={() => runAction('dump')}>采集 UI XML</Button>
            <Button loading={loadingAction === 'logcat'} icon={<TerminalSquare size={16} />} onClick={() => runAction('logcat')}>采集 logcat</Button>
          </div>
        </div>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}><FileCode2 size={18} /> Artifact 操作结果</h2>
          {artifacts.length === 0 ? (
            <List dataSource={['点击左侧动作按钮生成截图、UI XML 或 logcat artifact', '后端不可用时会展示本地 mock/degraded 附件', '真实执行失败时应保留错误原因与设备状态']} renderItem={(item) => <List.Item style={{ color: 'var(--text-secondary)' }}>{item}</List.Item>} />
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              {artifacts.map((artifact) => <ArtifactPreview key={artifact.id} artifact={artifact} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
