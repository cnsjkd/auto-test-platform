import { Descriptions } from 'antd';
import { useEffect, useState } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Artifact } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { RiskBadge } from '../components/RiskBadge';

export function ArtifactPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const routedArtifact = (location.state as { artifact?: Artifact } | null)?.artifact;
  const [artifact, setArtifact] = useState<Artifact | undefined>(routedArtifact);

  useEffect(() => {
    if (routedArtifact) {
      setArtifact(routedArtifact);
      return;
    }
    void api.getArtifact(id).then((result) => setArtifact(result.data.artifact));
  }, [id, routedArtifact]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Artifact Preview</div>
          <h1 className="page-title">证据附件预览</h1>
          <p className="page-description">预览截图、日志、UI XML 与报告摘要；若包含像素兜底元数据，展示坐标标注和风险栏。</p>
        </div>
        {artifact?.meta?.pixelAudit ? <RiskBadge /> : null}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>附件元数据</h2>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Artifact ID"><span className="mono">{artifact?.id}</span></Descriptions.Item>
            <Descriptions.Item label="Type">{artifact?.type}</Descriptions.Item>
            <Descriptions.Item label="Path"><span className="mono">{artifact?.path}</span></Descriptions.Item>
            <Descriptions.Item label="MIME"><span className="mono">{artifact?.mimeType}</span></Descriptions.Item>
            <Descriptions.Item label="Size"><span className="mono">{artifact?.sizeBytes}</span></Descriptions.Item>
            <Descriptions.Item label="Checksum"><span className="mono">{artifact?.checksum}</span></Descriptions.Item>
          </Descriptions>
        </div>
        <ArtifactPreview artifact={artifact} />
      </div>
    </div>
  );
}
