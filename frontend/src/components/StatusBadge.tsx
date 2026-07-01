import { CheckCircle2, CircleDashed, Clock3, HelpCircle, ShieldAlert, XCircle } from 'lucide-react';
import { Tag } from 'antd';
import type { DeviceStatus, RunStatus } from '../api/types';

type BadgeStatus = DeviceStatus | RunStatus | 'pass' | 'warn' | 'fail' | 'enabled' | 'disabled';

const config: Record<BadgeStatus, { label: string; color: string; Icon: typeof CheckCircle2 }> = {
  online: { label: 'online', color: 'var(--color-success)', Icon: CheckCircle2 },
  offline: { label: 'offline', color: 'var(--text-muted)', Icon: CircleDashed },
  unauthorized: { label: 'unauthorized', color: 'var(--color-warning)', Icon: ShieldAlert },
  missing: { label: 'missing', color: 'var(--color-error)', Icon: XCircle },
  queued: { label: 'queued', color: 'var(--color-info)', Icon: Clock3 },
  running: { label: 'running', color: 'var(--color-primary-hover)', Icon: CircleDashed },
  passed: { label: 'passed', color: 'var(--color-success)', Icon: CheckCircle2 },
  failed: { label: 'failed', color: 'var(--color-error)', Icon: XCircle },
  canceled: { label: 'canceled', color: 'var(--text-muted)', Icon: CircleDashed },
  pass: { label: 'pass', color: 'var(--color-success)', Icon: CheckCircle2 },
  warn: { label: 'warn', color: 'var(--color-warning)', Icon: ShieldAlert },
  fail: { label: 'fail', color: 'var(--color-error)', Icon: XCircle },
  enabled: { label: 'enabled', color: 'var(--color-success)', Icon: CheckCircle2 },
  disabled: { label: 'disabled', color: 'var(--text-muted)', Icon: HelpCircle },
};

export function StatusBadge({ status, label }: { status: BadgeStatus; label?: string }) {
  const item = config[status];
  const Icon = item.Icon;

  return (
    <Tag
      style={{
        color: item.color,
        borderColor: item.color,
        background: 'var(--bg-surface)',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        marginInlineEnd: 0,
      }}
    >
      <Icon size={14} aria-hidden />
      {label ?? item.label}
    </Tag>
  );
}
