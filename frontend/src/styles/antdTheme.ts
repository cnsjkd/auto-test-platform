import type { ThemeConfig } from 'antd';

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: 'var(--color-primary)',
    colorSuccess: 'var(--color-success)',
    colorWarning: 'var(--color-warning)',
    colorError: 'var(--color-error)',
    colorInfo: 'var(--color-info)',
    colorBgBase: 'var(--bg-app)',
    colorBgContainer: 'var(--bg-surface)',
    colorBgElevated: 'var(--bg-elevated)',
    colorBorder: 'var(--border-default)',
    colorText: 'var(--text-primary)',
    colorTextSecondary: 'var(--text-secondary)',
    colorTextTertiary: 'var(--text-muted)',
    borderRadius: 6,
    borderRadiusLG: 8,
    fontFamily: "Inter, 'Noto Sans SC', sans-serif",
    fontFamilyCode: "'JetBrains Mono', 'Fira Code', monospace",
    motionDurationFast: '0.15s',
    motionDurationMid: '0.25s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  components: {
    Layout: {
      bodyBg: 'var(--bg-app)',
      headerBg: 'var(--bg-app)',
      siderBg: 'var(--bg-surface)',
    },
    Menu: {
      darkItemBg: 'var(--bg-surface)',
      darkSubMenuItemBg: 'var(--bg-surface)',
      darkItemSelectedBg: 'var(--color-primary)',
      darkItemColor: 'var(--text-secondary)',
      darkItemHoverColor: 'var(--text-primary)',
      darkItemSelectedColor: 'var(--text-primary)',
    },
  },
};
