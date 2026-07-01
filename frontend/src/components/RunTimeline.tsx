import { Collapse, Space, Timeline, Tag } from 'antd';
import { Camera, FileText, MousePointerClick, Terminal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { RiskBadge } from './RiskBadge';
import { StatusBadge } from './StatusBadge';
import type { Artifact, TestResult } from '../api/types';

const iconByStrategy = {
  semantic: <MousePointerClick size={16} />,
  pixel_fallback: <MousePointerClick size={16} />,
  system: <Terminal size={16} />,
  evidence: <Camera size={16} />,
};

interface RunTimelineProps {
  results: TestResult[];
  artifactCountByResult?: Map<string, Artifact[]>;
}

export function RunTimeline({ results, artifactCountByResult }: RunTimelineProps) {
  return (
    <Timeline
      items={results.map((item) => {
        const artifacts = artifactCountByResult?.get(String(item.id)) ?? [];
        const screenshot = artifacts.find((artifact) => artifact.type === 'screenshot' || artifact.type === 'pixel_audit');
        const rawSteps = item.raw?.steps ?? [];
        return {
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
              <Space wrap style={{ marginTop: 10 }}>
                <Tag>{item.locatorStrategy}</Tag>
                <Tag>{item.durationMs ?? 0}ms</Tag>
                <Tag>{artifacts.length} artifacts</Tag>
                {item.errorCode ? <Tag color="error">code={item.errorCode}</Tag> : null}
                {screenshot ? <Link to={`/artifacts/${screenshot.id}`} state={{ artifact: screenshot }}>查看截图</Link> : null}
              </Space>
              {rawSteps.length > 0 ? (
                <Collapse
                  size="small"
                  style={{ marginTop: 12 }}
                  items={[
                    {
                      key: 'steps',
                      label: `动作步骤 ${rawSteps.length} 个`,
                      children: (
                        <div style={{ display: 'grid', gap: 8 }}>
                          {rawSteps.map((step) => {
                            const stepArtifacts = artifacts.filter((artifact) => step.artifactIds?.some((artifactId) => String(artifactId) === String(artifact.id)));
                            return (
                              <div key={`${item.id}-${step.index}`} style={{ border: '1px solid var(--border-default)', borderRadius: 'var(--radius-button)', padding: 10 }}>
                                <Space wrap>
                                  <Tag>#{step.index + 1}</Tag>
                                  <Tag>{step.action}</Tag>
                                  <Tag color={step.status === 'success' ? 'success' : 'error'}>{step.status}</Tag>
                                  {step.commandId !== undefined ? <span className="mono">command={step.commandId}</span> : null}
                                  {step.pixelAudit ? <RiskBadge compact /> : null}
                                </Space>
                                {stepArtifacts.length > 0 ? (
                                  <div style={{ marginTop: 8, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                                    {stepArtifacts.map((artifact) => (
                                      <Link key={artifact.id} to={`/artifacts/${artifact.id}`} state={{ artifact }}>
                                        {artifact.type} #{artifact.id}
                                      </Link>
                                    ))}
                                  </div>
                                ) : null}
                              </div>
                            );
                          })}
                        </div>
                      ),
                    },
                  ]}
                />
              ) : null}
            </div>
          ),
        };
      })}
    />
  );
}
