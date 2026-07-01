import { Alert, Descriptions } from 'antd';
import { AlertTriangle } from 'lucide-react';
import type { PixelAudit } from '../api/types';

export function PixelRiskPanel({ audit }: { audit: PixelAudit }) {
  return (
    <div className="console-card risk-card" style={{ padding: 16 }}>
      <Alert
        type="error"
        showIcon
        icon={<AlertTriangle size={18} />}
        message="像素坐标兜底已显式启用"
        description="该操作不是语义定位，报告与 artifact 必须保留完整风险说明，后续应推动可测试性改造。"
        style={{ marginBottom: 16, background: 'var(--bg-surface)', borderColor: 'var(--color-error)', color: 'var(--text-primary)' }}
      />
      <Descriptions bordered column={2} size="small" labelStyle={{ color: 'var(--text-secondary)' }} contentStyle={{ color: 'var(--text-primary)' }}>
        <Descriptions.Item label="原因" span={2}>{audit.fallbackReason}</Descriptions.Item>
        <Descriptions.Item label="x" contentStyle={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}>{audit.x}</Descriptions.Item>
        <Descriptions.Item label="y" contentStyle={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}>{audit.y}</Descriptions.Item>
        <Descriptions.Item label="screenWidth" contentStyle={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}>{audit.screenWidth}</Descriptions.Item>
        <Descriptions.Item label="screenHeight" contentStyle={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}>{audit.screenHeight}</Descriptions.Item>
        <Descriptions.Item label="orientation">{audit.orientation}</Descriptions.Item>
        <Descriptions.Item label="riskNote" span={2}>{audit.riskNote}</Descriptions.Item>
        <Descriptions.Item label="improvementSuggestion" span={2}>{audit.improvementSuggestion}</Descriptions.Item>
      </Descriptions>
    </div>
  );
}
