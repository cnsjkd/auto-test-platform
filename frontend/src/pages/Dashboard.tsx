import { Button, Table } from 'antd';
import { AlertTriangle, Cpu, FileText, PlayCircle, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Device, TestRun } from '../api/types';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

export function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    void Promise.all([api.listDevices(), api.listRuns()]).then(([deviceResult, runResult]) => {
      setDevices(deviceResult.data.devices);
      setRuns(runResult.data.runs);
      setDegraded(Boolean(deviceResult.degraded || runResult.degraded));
    });
  }, []);

  const latestRun = runs[0];
  const onlineCount = devices.filter((item) => item.status === 'online').length;
  const pixelCount = runs.reduce((sum, item) => sum + item.pixelFallbackCount, 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Command Center</div>
          <h1 className="page-title">A2 真机自动化控制台</h1>
          <p className="page-description">聚焦 Windows 本机 + ADB A2 真机接入、基础 UI 操作编排与失败证据闭环。当前页面支持后端不可用时的本地降级预览。</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Button icon={<Cpu size={16} />}><Link to="/devices">扫描设备</Link></Button>
          <Button type="primary" icon={<PlayCircle size={16} />}><Link to="/runs/new">创建运行</Link></Button>
        </div>
      </div>

      {degraded ? (
        <div className="console-card risk-card" style={{ padding: 14, marginBottom: 18, color: 'var(--text-secondary)' }}>
          后端暂不可用，已启用 mock/degraded 数据；UI 闭环可预览，但真机动作需等待 FastAPI 与 ADB 执行器启动。
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
        <MetricCard label="在线 A2 设备" value={`${onlineCount}/${devices.length}`} helper="区分 online、unauthorized、offline" icon={<Cpu size={24} />} />
        <MetricCard label="最近运行" value={latestRun?.status ?? 'none'} helper={latestRun?.id !== undefined ? String(latestRun.id) : '尚未创建运行'} icon={<ShieldCheck size={24} />} />
        <MetricCard label="失败用例" value={latestRun?.failedCount ?? 0} helper="失败保留截图、logcat、UI XML" icon={<FileText size={24} />} />
        <MetricCard label="像素兜底" value={pixelCount} helper="必须显式风险审计与改造建议" icon={<AlertTriangle size={24} />} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>设备在线状态</h2>
          <Table
            rowKey="id"
            pagination={false}
            dataSource={devices}
            columns={[
              { title: 'Serial', dataIndex: 'serial', render: (value: string, record) => <Link className="mono" to={`/devices/${record.id}`}>{value}</Link> },
              { title: '型号', dataIndex: 'model' },
              { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge status={value} /> },
            ]}
          />
        </div>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>最新运行</h2>
          <Table
            rowKey="id"
            pagination={false}
            dataSource={runs}
            columns={[
              { title: 'Run ID', dataIndex: 'id', render: (value: string) => <Link className="mono" to={`/runs/${value}`}>{value}</Link> },
              { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge status={value} /> },
              { title: '风险', dataIndex: 'pixelFallbackCount', render: (value: number) => (value ? <RiskBadge count={value} /> : '无像素兜底') },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
