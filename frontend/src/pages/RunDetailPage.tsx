import { Button, Descriptions, List } from 'antd';
import { FileArchive, StopCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { RunDetail } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { MetricCard } from '../components/MetricCard';
import { PixelRiskPanel } from '../components/PixelRiskPanel';
import { RiskBadge } from '../components/RiskBadge';
import { RunTimeline } from '../components/RunTimeline';
import { StatusBadge } from '../components/StatusBadge';

export function RunDetailPage() {
  const { id = '' } = useParams();
  const [detail, setDetail] = useState<RunDetail>();

  useEffect(() => {
    void api.getRun(id).then((result) => setDetail(result.data));
  }, [id]);

  const audits = useMemo(() => detail?.results.map((result) => result.pixelAudit).filter(Boolean) ?? [], [detail]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Run Detail</div>
          <h1 className="page-title">运行详情与失败证据链</h1>
          <p className="page-description">展示步骤时间线、截图/logcat/UI XML 附件、定位策略、错误码与像素兜底完整审计字段。</p>
        </div>
        <Button icon={<StopCircle size={16} />}>取消运行</Button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 18 }}>
        <MetricCard label="状态" value={detail?.run.status ? <StatusBadge status={detail.run.status} /> : '-'} helper={detail?.run.id !== undefined ? String(detail.run.id) : undefined} />
        <MetricCard label="通过" value={detail?.run.passedCount ?? 0} helper="passed cases" />
        <MetricCard label="失败" value={detail?.run.failedCount ?? 0} helper="failed cases" />
        <MetricCard label="像素兜底" value={detail?.run.pixelFallbackCount ?? 0} helper="risk points" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 18 }}>
        <div style={{ display: 'grid', gap: 18 }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>步骤时间线</h2>
            {detail ? <RunTimeline results={detail.results} /> : null}
          </div>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>Artifacts</h2>
            <List
              dataSource={detail?.artifacts ?? []}
              renderItem={(artifact) => (
                <List.Item actions={[<Link key="open" to={`/artifacts/${artifact.id}`} state={{ artifact }}>预览</Link>]}>
                  <List.Item.Meta title={<span><FileArchive size={15} /> {artifact.type}</span>} description={<span className="mono">{artifact.path}</span>} />
                </List.Item>
              )}
            />
          </div>
        </div>
        <div style={{ display: 'grid', gap: 16, alignContent: 'start' }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>运行摘要</h2>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Run ID"><span className="mono">{detail?.run.id}</span></Descriptions.Item>
              <Descriptions.Item label="Device"><span className="mono">{detail?.run.deviceSerial}</span></Descriptions.Item>
              <Descriptions.Item label="Started"><span className="mono">{detail?.run.startedAt}</span></Descriptions.Item>
              <Descriptions.Item label="Ended"><span className="mono">{detail?.run.endedAt}</span></Descriptions.Item>
              <Descriptions.Item label="Report"><span className="mono">{detail?.run.reportPath}</span></Descriptions.Item>
            </Descriptions>
          </div>
          {audits.length > 0 ? audits.map((audit, index) => audit ? <PixelRiskPanel key={index} audit={audit} /> : null) : <div className="console-card" style={{ padding: 16 }}>无像素兜底风险</div>}
          {detail?.artifacts[0] ? <ArtifactPreview artifact={detail.artifacts[0]} /> : null}
        </div>
      </div>
    </div>
  );
}
