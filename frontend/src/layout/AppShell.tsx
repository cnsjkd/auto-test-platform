import { Layout, Menu, Button } from 'antd';
import { Activity, Beaker, Cpu, FileArchive, FlaskConical, Home, PlayCircle, RefreshCw, Router, Settings } from 'lucide-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { Health } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';

const { Header, Sider, Content } = Layout;

const navItems = [
  { key: '/', label: 'Command Center', icon: <Home size={17} />, path: '/' },
  { key: '/setup', label: 'Setup', icon: <Settings size={17} />, path: '/setup' },
  { key: '/devices', label: 'Device Lab', icon: <Cpu size={17} />, path: '/devices' },
  { key: '/test-cases', label: 'Test Cases', icon: <FlaskConical size={17} />, path: '/test-cases' },
  { key: '/runs/new', label: 'New Run', icon: <PlayCircle size={17} />, path: '/runs/new' },
  { key: '/runs', label: 'Runs', icon: <Activity size={17} />, path: '/runs' },
  { key: '/artifacts', label: 'Artifacts', icon: <FileArchive size={17} />, path: '/artifacts' },
];

const selectedKey = (pathname: string) => {
  if (pathname === '/') return '/';
  if (pathname.startsWith('/devices')) return '/devices';
  if (pathname.startsWith('/test-cases')) return '/test-cases';
  if (pathname.startsWith('/runs/new')) return '/runs/new';
  if (pathname.startsWith('/runs')) return '/runs';
  if (pathname.startsWith('/artifacts')) return '/artifacts';
  return pathname;
};

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [health, setHealth] = useState<Health>();
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadHealth = async () => {
    setLoading(true);
    const result = await api.health();
    setHealth(result.data);
    setDegraded(Boolean(result.degraded));
    setLoading(false);
  };

  useEffect(() => {
    void loadHealth();
  }, []);

  const items = useMemo(
    () => navItems.map((item) => ({ key: item.key, icon: item.icon, label: <Link to={item.path}>{item.label}</Link> })),
    [],
  );

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--bg-app)' }}>
      <Sider width={252} style={{ borderRight: '1px solid var(--border-default)', padding: 18, position: 'sticky', top: 0, height: '100vh' }}>
        <button
          onClick={() => navigate('/')}
          style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', background: 'transparent', border: 0, color: 'var(--text-primary)', padding: 0, cursor: 'pointer' }}
        >
          <span style={{ width: 38, height: 38, borderRadius: 'var(--radius-card)', display: 'grid', placeItems: 'center', background: 'var(--color-primary)' }}>
            <Beaker size={20} />
          </span>
          <span style={{ textAlign: 'left' }}>
            <strong style={{ display: 'block' }}>A2 TestOps</strong>
            <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Local-first Console</span>
          </span>
        </button>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedKey(location.pathname)]} items={items} style={{ marginTop: 28, borderInlineEnd: 0 }} />
      </Sider>
      <Layout>
        <Header style={{ height: 66, padding: '0 28px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Router size={18} color="var(--color-primary-hover)" />
            <span style={{ color: 'var(--text-secondary)' }}>ADB 状态</span>
            <StatusBadge status={health?.adbAvailable ? 'pass' : degraded ? 'warn' : 'fail'} label={health?.adbAvailable ? 'available' : degraded ? 'degraded mock' : 'unavailable'} />
            <span className="mono" style={{ color: 'var(--text-muted)', fontSize: 12 }}>{health?.artifactRoot ?? 'detecting artifact root'}</span>
          </div>
          <Button loading={loading} icon={<RefreshCw size={16} />} onClick={loadHealth}>
            重新检测
          </Button>
        </Header>
        <Content style={{ padding: 28, background: 'var(--bg-app)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
