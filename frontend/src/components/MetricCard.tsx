import type { ReactNode } from 'react';

export function MetricCard({ label, value, helper, icon }: { label: string; value: ReactNode; helper?: string; icon?: ReactNode }) {
  return (
    <div className="console-card" style={{ padding: 18, minHeight: 116 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{label}</div>
          <div style={{ color: 'var(--text-primary)', fontSize: 28, fontWeight: 700, marginTop: 8 }}>{value}</div>
        </div>
        <div style={{ color: 'var(--color-primary-hover)' }}>{icon}</div>
      </div>
      {helper ? <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 12 }}>{helper}</div> : null}
    </div>
  );
}
