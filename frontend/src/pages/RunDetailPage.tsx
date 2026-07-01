import { Alert, Button, Descriptions, Empty, List, Progress, Space, Statistic, Tag, message } from 'antd';
import { Camera, FileArchive, RefreshCw, StopCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { Artifact, RunDetail } from '../api/types';
import { ArtifactPreview } from '../components/ArtifactPreview';
import { MetricCard } from '../components/MetricCard';
import { PixelRiskPanel } from '../components/PixelRiskPanel';
import { RiskBadge } from '../components/RiskBadge';
import { RunTimeline } from '../components/RunTimeline';
import { StatusBadge } from '../components/StatusBadge';

const FINAL_STATUSES = new Set(['passed', 'failed', 'canceled']);

const formatTime = (value?: string) => (value ? new Date(value).toLocaleString() : '-');

export function RunDetailPage() {
  const { id = '' } = useParams();
  const [detail, setDetail] = useState<RunDetail>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>();

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(undefined);
    try {
      const result = await api.getRun(id);
      setDetail(result.data);
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法加载运行详情');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const isRunning = detail ? !FINAL_STATUSES.has(detail.run.status) : true;

  useEffect(() => {
    if (!id || !isRunning) return undefined;
    const timer = window.setInterval(() => {
      void loadDetail();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [id, isRunning, loadDetail]);

  const audits = useMemo(() => detail?.results.map((result) => result.pixelAudit).filter(Boolean) ?? [], [detail]);
  const finishedCount = detail ? detail.run.passedCount + detail.run.failedCount + detail.run.skippedCount : 0;
  const totalCount = detail?.run.totalCount ?? 0;
  const progress = totalCount > 0 ? Math.round((finishedCount / totalCount) * 100) : 0;
  const screenshots = useMemo(() => detail?.artifacts.filter((item) => item.type === 'screenshot' || item.type === 'pixel_audit') ?? [], [detail]);
  const artifactCountByResult = useMemo(() => {
    const map = new Map<string, Artifact[]>();
    detail?.artifacts.forEach((artifact) => {
      if (artifact.resultId === undefined || artifact.resultId === null) return;
      const key = String(artifact.resultId);
      map.set(key, [...(map.get(key) ?? []), artifact]);
    });
    return map;
  }, [detail]);

  const latestScreenshot = screenshots[0];

  const cancelRun = async () => {
    if (!id) return;
    try {
      const result = await api.cancelRun(id);
      setDetail((current) => current ? { ...current, run: result.data.run } : current);
      message.success('已提交取消运行请求');
      void loadDetail();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '取消运行失败');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Run Monitor</div>
          <h1 className="page-title">运行监控与结果证据</h1>
          <p className="page-description">启动后本页会自动刷新真实后端结果。你可以在这里看每条脚本状态、执行耗时、artifact 数量、截图/UI XML/logcat 和 Pixel Fallback 审计。</p>
        </div>
        <Space>
          <Button loading={loading} icon={<RefreshCw size={16} />} onClick={loadDetail}>刷新监控</Button>
          <Button icon={<StopCircle size={16} />} disabled={!detail || !isRunning} onClick={cancelRun}>取消运行</Button>
        </Space>
      </div>

      {error ? <Alert type="error" showIcon message="监控数据加载失败" description={error} style={{ marginBottom: 16 }} /> : null}
      {isRunning ? (
        <Alert
          type="info"
          showIcon
          message="正在监控真实 A2 自动化运行"
          description="页面每 2 秒刷新一次。若脚本包含截图、UI XML 或 logcat，完成对应步骤后会出现在下方证据区。"
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 18 }}>
        <MetricCard label="状态" value={detail?.run.status ? <StatusBadge status={detail.run.status} /> : '-'} helper={detail?.run.id !== undefined ? `Run #${detail.run.id}` : undefined} />
        <MetricCard label="进度" value={`${finishedCount}/${totalCount || '-'}`} helper={`${progress}% completed`} />
        <MetricCard label="通过/失败" value={`${detail?.run.passedCount ?? 0}/${detail?.run.failedCount ?? 0}`} helper="passed / failed" />
        <MetricCard label="证据附件" value={detail?.artifacts.length ?? 0} helper="screenshots / xml / logcat / reports" />
      </div>

      <div className="console-card" style={{ padding: 16, marginBottom: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px 260px', gap: 18, alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: '0 0 10px' }}>脚本执行进度</h2>
            <Progress percent={progress} status={detail?.run.status === 'failed' ? 'exception' : detail?.run.status === 'passed' ? 'success' : 'active'} />
          </div>
          <Statistic title="最近刷新" value={lastRefreshedAt ? lastRefreshedAt.toLocaleTimeString() : '-'} />
          <Statistic title="当前设备" value={detail?.run.deviceSerial ?? detail?.run.deviceId ?? '-'} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 18 }}>
        <div style={{ display: 'grid', gap: 18 }}>
          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>每条脚本/用例状态</h2>
            {detail ? <RunTimeline results={detail.results} artifactCountByResult={artifactCountByResult} /> : <Empty description="等待运行详情" />}
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>本次运行 Artifacts</h2>
            <List
              dataSource={detail?.artifacts ?? []}
              locale={{ emptyText: <Empty description={isRunning ? '正在等待脚本生成证据' : '暂无证据附件'} /> }}
              renderItem={(artifact) => (
                <List.Item actions={[<Link key="open" to={`/artifacts/${artifact.id}`} state={{ artifact }}>预览</Link>]}> 
                  <List.Item.Meta
                    avatar={<FileArchive size={15} />}
                    title={<Space wrap><Tag>{artifact.type}</Tag><span className="mono">#{artifact.id}</span>{artifact.resultId ? <Tag>result {artifact.resultId}</Tag> : null}</Space>}
                    description={<span className="mono">{artifact.path}</span>}
                  />
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
              <Descriptions.Item label="Device"><span className="mono">{detail?.run.deviceSerial ?? detail?.run.deviceId}</span></Descriptions.Item>
              <Descriptions.Item label="Started"><span className="mono">{formatTime(detail?.run.startedAt)}</span></Descriptions.Item>
              <Descriptions.Item label="Ended"><span className="mono">{formatTime(detail?.run.endedAt)}</span></Descriptions.Item>
              <Descriptions.Item label="Report"><span className="mono">{detail?.run.reportPath ?? '运行完成后生成'}</span></Descriptions.Item>
              <Descriptions.Item label="Pixel Fallback">{detail?.run.pixelFallbackCount ? <RiskBadge count={detail.run.pixelFallbackCount} /> : '无'}</Descriptions.Item>
            </Descriptions>
          </div>

          <div className="console-card" style={{ padding: 16 }}>
            <h2 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}><Camera size={18} /> 最新截图</h2>
            {latestScreenshot ? <ArtifactPreview artifact={latestScreenshot} /> : <Empty description={isRunning ? '截图生成后会自动出现' : '本次运行暂无截图'} />}
          </div>

          {audits.length > 0 ? audits.map((audit, index) => audit ? <PixelRiskPanel key={index} audit={audit} /> : null) : <div className="console-card" style={{ padding: 16 }}>无像素兜底风险</div>}
        </div>
      </div>
    </div>
  );
}
