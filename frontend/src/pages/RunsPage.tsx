import { Button, Table } from 'antd';
import { PlayCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { TestRun } from '../api/types';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

export function RunsPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);

  useEffect(() => {
    void api.listRuns().then((result) => setRuns(result.data.runs));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Runs</div>
          <h1 className="page-title">运行记录与报告入口</h1>
          <p className="page-description">任意运行保留状态、设备、报告路径与像素兜底风险摘要；失败运行可进入详情查看证据链。</p>
        </div>
        <Button type="primary" icon={<PlayCircle size={16} />}><Link to="/runs/new">创建运行</Link></Button>
      </div>
      <div className="console-card" style={{ padding: 16 }}>
        <Table
          rowKey="id"
          dataSource={runs}
          pagination={false}
          columns={[
            { title: 'Run ID', dataIndex: 'id', render: (value: string) => <Link className="mono" to={`/runs/${value}`}>{value}</Link> },
            { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge status={value} /> },
            { title: '设备', dataIndex: 'deviceSerial', render: (value) => <span className="mono">{value}</span> },
            { title: '结果', render: (_, record) => `${record.passedCount} passed / ${record.failedCount} failed / ${record.skippedCount} skipped` },
            { title: '开始时间', dataIndex: 'startedAt', render: (value) => <span className="mono">{value}</span> },
            { title: '报告', dataIndex: 'reportPath', render: (value) => <span className="mono">{value}</span> },
            { title: '像素风险', dataIndex: 'pixelFallbackCount', render: (value: number) => (value ? <RiskBadge count={value} /> : '无') },
          ]}
        />
      </div>
    </div>
  );
}
