import { Button, Drawer, Form, Input, InputNumber, Select, Space, Table, message } from 'antd';
import { Plus, ShieldAlert } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api/client';
import { ACTIONS, type Action, type TestCase, type TestStep } from '../api/types';
import { CodeBlock } from '../components/CodeBlock';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

interface CaseFormValues {
  name: string;
  description: string;
  type: string;
  priority: 'P0' | 'P1' | 'P2';
  tags?: string;
  action: Action;
  selectorText?: string;
  fallbackReason?: string;
  riskNote?: string;
  improvementSuggestion?: string;
  x?: number;
  y?: number;
  screenWidth?: number;
  screenHeight?: number;
  orientation?: 'portrait' | 'landscape';
}

export function TestCasesPage() {
  const [cases, setCases] = useState<TestCase[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<TestCase>();
  const [form] = Form.useForm<CaseFormValues>();
  const action = Form.useWatch('action', form);
  const isPixel = action === 'pixel_tap' || action === 'pixel_swipe';

  const load = async () => {
    const result = await api.listCases();
    setCases(result.data.cases);
  };

  useEffect(() => {
    void load();
  }, []);

  const preview = useMemo(() => selected ? JSON.stringify(selected.steps, null, 2) : '选择一条用例查看 steps，字段必须使用 action，并遵守固定枚举。', [selected]);

  const createCase = async (values: CaseFormValues) => {
    const step: TestStep = {
      id: `step-${Date.now()}`,
      name: values.action,
      action: values.action,
      timeoutSec: 30,
    };

    if (values.selectorText && !isPixel) {
      step.selector = { text: values.selectorText };
    }

    if (isPixel) {
      const missing = ['fallbackReason', 'riskNote', 'improvementSuggestion', 'x', 'y', 'screenWidth', 'screenHeight', 'orientation'].filter((key) => values[key as keyof CaseFormValues] === undefined || values[key as keyof CaseFormValues] === '');
      if (missing.length > 0) {
        message.error(`像素兜底审计字段缺失：${missing.join(', ')}`);
        throw new ApiError(52003, '像素兜底审计字段缺失');
      }
      step.pixelAudit = {
        pixelFallback: true,
        fallbackReason: values.fallbackReason ?? '',
        riskNote: values.riskNote ?? '',
        improvementSuggestion: values.improvementSuggestion ?? '',
        x: values.x ?? 0,
        y: values.y ?? 0,
        screenWidth: values.screenWidth ?? 0,
        screenHeight: values.screenHeight ?? 0,
        orientation: values.orientation ?? 'portrait',
      };
    }

    const result = await api.createCase({
      name: values.name,
      description: values.description,
      type: values.type,
      priority: values.priority,
      tags: values.tags?.split(',').map((item) => item.trim()).filter(Boolean) ?? [],
      status: 'enabled',
      steps: [step],
    });
    setCases((items) => [result.data.case, ...items]);
    setDrawerOpen(false);
    form.resetFields();
    message.success('已创建本地用例预览');
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-kicker">Test Cases</div>
          <h1 className="page-title">用例资产与定位策略</h1>
          <p className="page-description">用例步骤只使用 `action` 字段。选择 pixel_tap 或 pixel_swipe 时强制填写原因、坐标、屏幕宽高、方向、风险与改造建议。</p>
        </div>
        <Button type="primary" icon={<Plus size={16} />} onClick={() => setDrawerOpen(true)}>创建用例</Button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 18 }}>
        <div className="console-card" style={{ padding: 16 }}>
          <Table
            rowKey="id"
            dataSource={cases}
            pagination={false}
            onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
            columns={[
              { title: '用例', dataIndex: 'name' },
              { title: '优先级', dataIndex: 'priority' },
              { title: '标签', dataIndex: 'tags', render: (tags: string[]) => tags.join(', ') },
              { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge status={value} /> },
              { title: '定位风险', dataIndex: 'pixelFallbackCount', render: (value: number) => (value ? <RiskBadge count={value} /> : '语义优先') },
            ]}
          />
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          {selected?.hasPixelFallback && selected.steps.find((step) => step.pixelAudit)?.pixelAudit ? (
            <div className="console-card risk-card" style={{ padding: 16 }}>
              <strong><ShieldAlert size={16} /> 像素兜底摘要</strong>
              <p style={{ color: 'var(--text-secondary)' }}>{selected.steps.find((step) => step.pixelAudit)?.pixelAudit?.riskNote}</p>
              <RiskBadge count={selected.pixelFallbackCount} />
            </div>
          ) : null}
          <CodeBlock title="steps JSON" code={preview} />
        </div>
      </div>

      <Drawer title="创建 P0 用例" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560} destroyOnClose>
        <Form form={form} layout="vertical" initialValues={{ type: 'smoke', priority: 'P0', action: 'semantic_click', orientation: 'portrait', screenWidth: 1404, screenHeight: 1872 }} onFinish={createCase}>
          <Form.Item name="name" label="用例名称" rules={[{ required: true, message: '请输入明确用例名称' }]}><Input placeholder="基础真机操作检查" /></Form.Item>
          <Form.Item name="description" label="验收说明" rules={[{ required: true, message: '请输入具体测试目标' }]}><Input.TextArea rows={3} placeholder="验证 A2 指定路径的操作与证据闭环" /></Form.Item>
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="type" label="类型" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="priority" label="优先级" rules={[{ required: true }]}><Select options={['P0', 'P1', 'P2'].map((value) => ({ value, label: value }))} /></Form.Item>
          </Space>
          <Form.Item name="tags" label="标签"><Input placeholder="ADB, smoke, A2" /></Form.Item>
          <Form.Item name="action" label="Step Action" rules={[{ required: true }]}><Select options={ACTIONS.map((value) => ({ value, label: value }))} /></Form.Item>
          {!isPixel ? <Form.Item name="selectorText" label="语义 selector.text"><Input placeholder="会议记录" /></Form.Item> : null}
          {isPixel ? (
            <div className="console-card risk-card" style={{ padding: 14, marginBottom: 16 }}>
              <RiskBadge />
              <Form.Item name="fallbackReason" label="fallbackReason" rules={[{ required: true, message: '必须说明为何无法语义定位' }]}><Input.TextArea rows={2} /></Form.Item>
              <Space>
                <Form.Item name="x" label="x" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
                <Form.Item name="y" label="y" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
              </Space>
              <Space>
                <Form.Item name="screenWidth" label="screenWidth" rules={[{ required: true }]}><InputNumber min={1} /></Form.Item>
                <Form.Item name="screenHeight" label="screenHeight" rules={[{ required: true }]}><InputNumber min={1} /></Form.Item>
              </Space>
              <Form.Item name="orientation" label="orientation" rules={[{ required: true }]}><Select options={[{ value: 'portrait', label: 'portrait' }, { value: 'landscape', label: 'landscape' }]} /></Form.Item>
              <Form.Item name="riskNote" label="riskNote" rules={[{ required: true, message: '必须说明稳定性风险' }]}><Input.TextArea rows={2} /></Form.Item>
              <Form.Item name="improvementSuggestion" label="improvementSuggestion" rules={[{ required: true, message: '必须给出可测试性改造建议' }]}><Input.TextArea rows={2} /></Form.Item>
            </div>
          ) : null}
          <Button type="primary" htmlType="submit" block>保存用例</Button>
        </Form>
      </Drawer>
    </div>
  );
}
