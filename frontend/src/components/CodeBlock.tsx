import { Button } from 'antd';
import { Copy } from 'lucide-react';

export function CodeBlock({ code, title }: { code: string; title?: string }) {
  const copy = async () => {
    await navigator.clipboard?.writeText(code);
  };

  return (
    <div className="console-card" style={{ overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid var(--border-default)' }}>
        <span className="mono" style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{title ?? '输出预览'}</span>
        <Button size="small" type="text" onClick={copy} icon={<Copy size={14} />}>
          复制
        </Button>
      </div>
      <pre className="mono" style={{ margin: 0, padding: 16, color: 'var(--text-primary)', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 360, overflow: 'auto' }}>
        {code}
      </pre>
    </div>
  );
}
