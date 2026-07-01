import { AlertTriangle } from 'lucide-react';
import { Tag } from 'antd';

export function RiskBadge({ count, compact = false }: { count?: number; compact?: boolean }) {
  return (
    <Tag
      style={{
        color: 'var(--color-error)',
        borderColor: 'var(--color-error)',
        background: 'var(--bg-surface)',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        marginInlineEnd: 0,
      }}
    >
      <AlertTriangle size={14} aria-hidden />
      {compact ? '像素兜底' : `像素兜底风险${count ? ` ${count}` : ''}`}
    </Tag>
  );
}
