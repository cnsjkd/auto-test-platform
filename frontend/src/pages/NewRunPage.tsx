import { Alert, Button, Checkbox, List, Select, message } from 'antd';
import { ClipboardCheck, FileText, PlayCircle, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { Device, EntityId, SmokeSuite, TestCase } from '../api/types';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

const toOptionValue = (id: EntityId) => String(id);
const toNumericId = (id?: EntityId) => {
  const value = typeof id === 'number' ? id : Number(id);
  return Number.isFinite(value) ? value : undefined;
};

export function NewRunPage() {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [smokeSuite, setSmokeSuite] = useState<SmokeSuite>();
  const [deviceId, setDeviceId] = useState<string>();
  const [caseIds, setCaseIds] = useState<string[]>([]);
  const [riskAccepted, setRiskAccepted] = useState(false);
  const [suiteRiskAccepted, setSuiteRiskAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [suiteSubmitting, setSuiteSubmitting] = useState(false);
  const [degraded, setDegraded] = useState(false);

  useEffect(() => {
    void Promise.all([api.listDevices(), api.listCases(), api.getP0SmokeSuite()]).then(([deviceResult, caseResult, suiteResult]) => {
      setDevices(deviceResult.data.devices);
      setCases(caseResult.data.cases);
      setSmokeSuite(suiteResult.data);
      setDegraded(Boolean(deviceResult.degraded || caseResult.degraded || suiteResult.degraded));
      setDeviceId(deviceResult.data.devices.find((item) => item.status === 'online')?.id !== undefined ? toOptionValue(deviceResult.data.devices.find((item) => item.status === 'online')?.id ?? '') : undefined);
      setCaseIds(caseResult.data.cases.slice(0, 1).map((item) => toOptionValue(item.id)));
    });
  }, []);

  const selectedDevice = useMemo(() => devices.find((item) => toOptionValue(item.id) === deviceId), [deviceId, devices]);
  const selectedCases = cases.filter((item) => caseIds.includes(toOptionValue(item.id)));
  const pixelFallbackCount = useMemo(() => selectedCases.reduce((sum, item) => sum + item.pixelFallbackCount, 0), [selectedCases]);
  const mustAcceptRisk = pixelFallbackCount > 0;
  const suiteDeviceId = toNumericId(selectedDevice?.id);
  const smokeSuiteReady = smokeSuite?.ready ?? Boolean(smokeSuite);
  const suiteRequiresRisk = Boolean(smokeSuite?.requiresRiskAcceptance || (smokeSuite?.pixelFallbackCount ?? 0) > 0);
  const canRunSuite = Boolean(selectedDevice && selectedDevice.status === 'online' && suiteDeviceId !== undefined && smokeSuiteReady);

  const startRun = async () => {
    if (!deviceId || caseIds.length === 0) {
      message.error('请选择在线设备和至少一条用例');
      return;
    }
    if (mustAcceptRisk && !riskAccepted) {
      message.error('包含像素兜底用例，必须确认风险后才能启动');
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.createRun({ deviceId, caseIds });
      navigate(`/runs/${result.data.run.id}`);
    } catch (error) {
      const content = error instanceof ApiError ? error.message : '创建运行失败，请检查后端服务与设备状态';
      message.error(content);
    } finally {
      setSubmitting(false);
    }
  };

  const startSmokeSuite = async () => {
    if (!selectedDevice || selectedDevice.status !== 'online' || suiteDeviceId === undefined) {
      message.error('请选择已授权在线设备后再运行 P0 冒烟套件');
      return;
    }
    if (!smokeSuiteReady) {
      message.error('P0 冒烟套件尚未 ready，请等待后端 seed 完成');
      return;
    }
    setSuiteSubmitting(true);
    try {
      const result = await api.runP0SmokeSuite({
        deviceId: suiteDeviceId,
        riskAccepted: suiteRiskAccepted,
        config: { trigger: 'ui' },
      });
      message.success(result.degraded ? '已启动本地 P0 冒烟预览运行' : '已提交 A2 P0 冒烟套件运行');
      navigate(`/runs/${result.data.run.id}`);
    } catch (error) {
      const content = error instanceof ApiError && (error.status === 422 || error.code === 42201)
        ? `P0 冒烟套件未启动：${error.message}`
        : error instanceof ApiError
          ? error.message
          : 'P0 冒烟套件启动失败，请检查后端校验结果';
      message.error(content);
    } finally {
      setSuiteSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">New Run</div>
          <h1 className="page-title">创建 A2 真机运行</h1>
          <p className="page-description">选择已授权 A2 设备与 P0 用例。若包含像素坐标兜底，启动前必须显式确认风险。</p>
        </div>
        <Button type="primary" loading={submitting} icon={<PlayCircle size={16} />} onClick={startRun}>启动运行</Button>
      </div>

      {degraded ? (
        <Alert
          type="warning"
          showIcon
          message="当前存在 degraded/mock 数据"
          description="后端不可用时保留本地预览；真实 P0 冒烟执行需 FastAPI、ADB 与 /api/smoke-suite/p0/run 可用。"
          style={{ marginBottom: 18 }}
        />
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>设备选择</h2>
          <Select
            value={deviceId}
            onChange={setDeviceId}
            style={{ width: '100%' }}
            placeholder="选择在线 A2 设备"
            options={devices.map((device) => ({
              value: toOptionValue(device.id),
              label: `${device.serial} · ${device.model} · ${device.status}`,
              disabled: device.status !== 'online',
            }))}
          />
          <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
            {devices.map((device) => (
              <div key={toOptionValue(device.id)} className="console-card" style={{ padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="mono">{device.serial}</span>
                <StatusBadge status={device.status} />
              </div>
            ))}
          </div>
        </div>
        <div className="console-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>用例选择</h2>
          <Select
            mode="multiple"
            value={caseIds}
            onChange={setCaseIds}
            style={{ width: '100%' }}
            options={cases.map((item) => ({ value: toOptionValue(item.id), label: `${item.name}${item.hasPixelFallback ? ' · 像素兜底' : ''}` }))}
          />
          <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
            {selectedCases.map((item) => (
              <div key={toOptionValue(item.id)} className={`console-card ${item.hasPixelFallback ? 'risk-card' : ''}`} style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <strong>{item.name}</strong>
                  {item.hasPixelFallback ? <RiskBadge count={item.pixelFallbackCount} /> : <span style={{ color: 'var(--text-secondary)' }}>语义优先</span>}
                </div>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 0 }}>{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="console-card risk-card" style={{ marginTop: 18, padding: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start' }}>
          <div>
            <div className="page-kicker">P0 Smoke Suite</div>
            <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}><ShieldCheck size={20} /> {smokeSuite?.suite.name ?? 'A2 P0 冒烟套件'}</h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 0 }}>{smokeSuite?.suite.description ?? '等待后端 seed/upsert P0 冒烟套件。'}</p>
          </div>
          {smokeSuite?.pixelFallbackCount ? <RiskBadge count={smokeSuite.pixelFallbackCount} /> : <StatusBadge status={smokeSuiteReady ? 'pass' : 'warn'} label={smokeSuiteReady ? 'ready' : 'pending'} />}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginTop: 18 }}>
          <MetricCard label="套件用例" value={smokeSuite?.caseCount ?? '-'} helper="后端自动 seed/upsert" icon={<ClipboardCheck size={22} />} />
          <MetricCard label="Pixel Fallback" value={smokeSuite?.pixelFallbackCount ?? '-'} helper="需保留审计说明与证据" icon={<ShieldAlert size={22} />} />
          <MetricCard label="运行设备" value={selectedDevice?.status === 'online' ? selectedDevice.serial : '未选择'} helper="仅在线授权设备可执行" icon={<FileText size={22} />} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 18, marginTop: 18, alignItems: 'start' }}>
          <div className="console-card" style={{ padding: 14 }}>
            <strong>必验项说明</strong>
            <List
              size="small"
              dataSource={smokeSuite?.acceptanceNotes ?? ['等待后端返回 acceptanceNotes', '运行前必须选择 online 设备', 'Pixel Fallback 风险确认只传给后端校验']}
              renderItem={(item) => <List.Item style={{ color: 'var(--text-secondary)' }}>{item}</List.Item>}
            />
          </div>
          <div className="console-card" style={{ padding: 14, display: 'grid', gap: 12 }}>
            <Checkbox checked={suiteRiskAccepted} onChange={(event) => setSuiteRiskAccepted(event.target.checked)}>
              我已确认 P0 套件 Pixel Fallback 风险
            </Checkbox>
            <Button
              type="primary"
              block
              loading={suiteSubmitting}
              disabled={!canRunSuite}
              icon={<PlayCircle size={16} />}
              onClick={startSmokeSuite}
            >
              一键运行 P0 冒烟套件
            </Button>
            <span style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.6 }}>
              前端仅提交 deviceId、riskAccepted 与 config；riskAccepted 校验由后端 /api/smoke-suite/p0/run 执行。
            </span>
          </div>
        </div>
      </div>

      {mustAcceptRisk ? (
        <Alert
          type="error"
          showIcon
          message="运行包含像素兜底操作"
          description="像素坐标依赖当前分辨率、方向与布局。报告会保留原因、x/y、screenWidth/screenHeight、orientation、riskNote、improvementSuggestion。"
          style={{ marginTop: 18 }}
          action={<Checkbox checked={riskAccepted} onChange={(event) => setRiskAccepted(event.target.checked)}>我已确认风险</Checkbox>}
        />
      ) : null}
    </div>
  );
}
