import { Timeline } from 'antd';
import { Camera, FileText, MousePointerClick, Terminal } from 'lucide-react';
import { RiskBadge } from './RiskBadge';
import { StatusBadge } from './StatusBadge';
import type { TestResult } from '../api/types';

const iconByStrategy = {
  semantic: <MousePointerClick size={16} />,
  pixel_fallback: <MousePointerClick size={16} />,
  system: <Terminal size={16} />,
  evidence: <Camera size={16} />,
};

export function RunTimeline({ results }: { results: TestResult[] }) {
  return (
    <Timeline
      items={results.map((item) => ({
        dot: <span style={{ color: item.pixelFallbackUsed ? 'var(--color-error)' : 'var(--color-primary-hover)' }}>{iconByStrategy[item.locatorStrategy] ?? <FileText size={16} />}</span>,
        children: (
          <div className={`console-card ${item.pixelFallbackUsed ? 'risk-card' : ''}`} style={{ padding: 14, marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <strong>{item.caseName}</strong>
              <div style={{ display: 'flex', gap: 8 }}>
                {item.pixelFallbackUsed ? <RiskBadge compact /> : null}
                <StatusBadge status={item.status} />
              </div>
            </div>
            <p style={{ color: 'var(--text-secondary)', margin: '8px 0 0' }}>{item.message}</p>
            <div className="mono" style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 10 }}>
              {item.locatorStrategy} · {item.durationMs}ms {item.errorCode ? `· code=${item.errorCode}` : ''}
            </div>
          </div>
        ),
      }))}
    />
  );
}
