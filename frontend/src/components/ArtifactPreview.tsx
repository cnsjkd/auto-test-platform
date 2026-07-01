import { Button, Empty } from 'antd';
import { Download, LocateFixed } from 'lucide-react';
import { CodeBlock } from './CodeBlock';
import { PixelRiskPanel } from './PixelRiskPanel';
import type { Artifact } from '../api/types';

export function ScreenshotViewer({ artifact }: { artifact: Artifact }) {
  const audit = artifact.meta?.pixelAudit;
  const downloadUrl = `/api/artifacts/${artifact.id}/download`;
  return (
    <div className="console-card" style={{ padding: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: audit ? '1fr 320px' : '1fr', gap: 16 }}>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ minHeight: 420, border: '1px solid var(--border-default)', borderRadius: 'var(--radius-card)', background: 'var(--bg-elevated)', position: 'relative', overflow: 'hidden', display: 'grid', placeItems: 'center' }}>
            <img
              src={downloadUrl}
              alt={artifact.meta?.title ?? artifact.path}
              style={{ display: 'block', width: '100%', height: '100%', maxHeight: 720, objectFit: 'contain' }}
            />
            {audit ? (
              <div style={{ position: 'absolute', left: `${(audit.x / audit.screenWidth) * 100}%`, top: `${(audit.y / audit.screenHeight) * 100}%`, transform: 'translate(-50%, -50%)', color: 'var(--color-error)', display: 'grid', placeItems: 'center', pointerEvents: 'none' }}>
                <LocateFixed size={34} />
                <span className="mono" style={{ marginTop: 6, fontSize: 12 }}>x={audit.x}, y={audit.y}</span>
              </div>
            ) : null}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, color: 'var(--text-secondary)' }}>
            <div>
              <div>{artifact.meta?.title ?? artifact.path}</div>
              <div className="mono" style={{ marginTop: 4, fontSize: 12 }}>{artifact.mimeType} · {artifact.sizeBytes} bytes</div>
            </div>
            <Button icon={<Download size={16} />} href={downloadUrl}>
              下载截图
            </Button>
          </div>
        </div>
        {audit ? <PixelRiskPanel audit={audit} /> : null}
      </div>
    </div>
  );
}

export function ArtifactPreview({ artifact }: { artifact?: Artifact }) {
  if (!artifact) {
    return <Empty description="未找到 artifact，确认 run_id 与附件索引后重试" />;
  }

  if (artifact.type === 'screenshot' || artifact.type === 'pixel_audit') {
    return <ScreenshotViewer artifact={artifact} />;
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      {artifact.meta?.pixelAudit ? <PixelRiskPanel audit={artifact.meta.pixelAudit} /> : null}
      <CodeBlock title={artifact.path} code={artifact.meta?.content ?? `${artifact.type} artifact preview\npath=${artifact.path}\nchecksum=${artifact.checksum}`} />
      <Button icon={<Download size={16} />} href={`/api/artifacts/${artifact.id}/download`}>
        下载附件
      </Button>
    </div>
  );
}
