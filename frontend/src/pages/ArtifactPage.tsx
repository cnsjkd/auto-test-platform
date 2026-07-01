import { Alert, Button, Descriptions, Empty, List, Space, Tag } from 'antd';
import { Download, FileArchive, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Artifact } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { RiskBadge } from '../components/RiskBadge';

export function ArtifactPage() {
  const { id } = useParams();
  const location = useLocation();
  const routedArtifact = (location.state as { artifact?: Artifact } | null)?.artifact;
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [artifact, setArtifact] = useState<Artifact | undefined>(routedArtifact);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  const loadArtifacts = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const result = await api.listArtifacts();
      setArtifacts(result.data.artifacts);
      if (!id && !routedArtifact) {
        setArtifact(result.data.artifacts[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法加载真实 artifact 列表');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadArtifacts();
  }, []);

  useEffect(() => {
    if (routedArtifact) {
      setArtifact(routedArtifact);
      return;
    }
    if (!id) return;
    void api.getArtifact(id).then((result) => setArtifact(result.data.artifact)).catch((err) => setError(err instanceof Error ? err.message : '无法加载 artifact'));
  }, [id, routedArtifact]);

  const screenshots = useMemo(() => artifacts.filter((item) => item.type === 'screenshot' || item.type === 'pixel_audit'), [artifacts]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Artifact Preview</div>
          <h1 className="page-title">真实证据附件</h1>
          <p className="page-description">这里展示后端数据库里的真实 artifact。没有后端或没有真实运行时，不再显示 local preview 模拟图。</p>
        </div>
        <Space>
          {artifact?.meta?.pixelAudit ? <RiskBadge /> : null}
          <Button loading={loading} icon={<RefreshCw size={16} />} onClick={loadArtifacts}>刷新真实附件</Button>
        </Space>
      </div>

      {error ? <Alert type="error" showIcon message="真实 artifact 加载失败" description={error} style={{ marginBottom: 16 }} /> : null}
      {artifacts.length === 0 && !loading ? (
        <Alert
          type="warning"
          showIcon
          message="暂无真实 artifact"
          description="请先到 Device Lab 打开真实设备，执行自动化流程或采集截图；完成后这里会出现真实截图、UI XML、logcat 和报告。"
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 18 }}>
        <div style={{ display: 'grid', gap: 18, alignContent: 'start' }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>真实附件列表</h2>
            <List
              loading={loading}
              dataSource={artifacts}
              locale={{ emptyText: <Empty description="暂无真实附件" /> }}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Link key="preview" to={`/artifacts/${item.id}`} state={{ artifact: item }} onClick={() => setArtifact(item)}>预览</Link>,
                    <Button key="download" size="small" icon={<Download size={14} />} href={`/api/artifacts/${item.id}/download`}>下载</Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileArchive size={18} />}
                    title={<Space wrap><Tag>{item.type}</Tag><span className="mono">#{item.id}</span>{item.runId ? <Tag>run {item.runId}</Tag> : null}</Space>}
                    description={<span className="mono">{item.path}</span>}
                  />
                </List.Item>
              )}
            />
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>截图快速核验</h2>
            {screenshots.length === 0 ? <Empty description="暂无截图类 artifact" /> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                {screenshots.slice(0, 8).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setArtifact(item)}
                    style={{ border: '1px solid var(--border-default)', borderRadius: 'var(--radius-card)', background: 'var(--bg-elevated)', padding: 8, cursor: 'pointer', color: 'var(--text-primary)' }}
                  >
                    <img src={`/api/artifacts/${item.id}/download`} alt={item.path} style={{ width: '100%', height: 120, objectFit: 'contain', display: 'block' }} />
                    <span className="mono" style={{ display: 'block', marginTop: 6, fontSize: 11 }}>#{item.id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gap: 18, alignContent: 'start' }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>附件元数据</h2>
            {artifact ? (
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Artifact ID"><span className="mono">{artifact.id}</span></Descriptions.Item>
                <Descriptions.Item label="Type">{artifact.type}</Descriptions.Item>
                <Descriptions.Item label="Run ID"><span className="mono">{artifact.runId ?? '-'}</span></Descriptions.Item>
                <Descriptions.Item label="Device ID"><span className="mono">{artifact.deviceId ?? '-'}</span></Descriptions.Item>
                <Descriptions.Item label="Path"><span className="mono">{artifact.path}</span></Descriptions.Item>
                <Descriptions.Item label="MIME"><span className="mono">{artifact.mimeType}</span></Descriptions.Item>
                <Descriptions.Item label="Size"><span className="mono">{artifact.sizeBytes}</span></Descriptions.Item>
                <Descriptions.Item label="Checksum"><span className="mono">{artifact.checksum}</span></Descriptions.Item>
              </Descriptions>
            ) : <Empty description="请选择一个真实 artifact" />}
          </div>
          <ArtifactPreview artifact={artifact} />
        </div>
      </div>
    </div>
  );
}
