import { Button, Table } from 'antd';
import { RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Device } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [degraded, setDegraded] = useState(false);

  const load = async (scan = false) => {
    setLoading(true);
    const result = scan ? await api.scanDevices() : await api.listDevices();
    setDevices(result.data.devices);
    setDegraded(Boolean(result.degraded));
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Device Lab</div>
          <h1 className="page-title">A2 设备实验室</h1>
          <p className="page-description">展示 serial、型号、Android 版本、SDK、分辨率、电量、网络、存储与 ADB 状态；未授权设备给出明确处置入口。</p>
        </div>
        <Button type="primary" loading={loading} icon={<RefreshCw size={16} />} onClick={() => load(true)}>扫描设备</Button>
      </div>

      {degraded ? <div className="console-card risk-card" style={{ padding: 14, marginBottom: 18 }}>当前为本地预览设备，真实扫描需后端 `/api/devices/scan` 可用。</div> : null}

      <div className="console-card" style={{ padding: 16 }}>
        <Table
          rowKey="id"
          dataSource={devices}
          pagination={false}
          columns={[
            { title: 'Serial', dataIndex: 'serial', render: (value: string, record) => <Link className="mono" to={`/devices/${record.id}`}>{value}</Link> },
            { title: '型号', dataIndex: 'model' },
            { title: 'Android', dataIndex: 'androidVersion', render: (value, record) => `${value} / SDK ${record.sdkInt}` },
            { title: '分辨率', dataIndex: 'screenWidth', render: (value, record) => <span className="mono">{value}x{record.screenHeight}</span> },
            { title: '电量', dataIndex: 'battery', render: (value) => `${value}%` },
            { title: '网络', dataIndex: 'network' },
            { title: '存储', dataIndex: 'storage' },
            { title: 'ADB', dataIndex: 'adbStatus', render: (value) => <span className="mono">{value}</span> },
            { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge status={value} /> },
          ]}
        />
      </div>
    </div>
  );
}
