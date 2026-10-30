import { theme,type ThemeConfig } from 'antd';
export const appTheme:ThemeConfig={
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#2563eb',
          colorBgLayout: '#f5f7fb',
          borderRadius: 8,
          fontFamily:
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif',
        },
        components: {
          Layout: { siderBg: '#101b30', headerBg: '#fff' },
          Menu: {
            darkItemBg: '#101b30',
            darkItemSelectedBg: '#2563eb',
            darkItemHoverBg: '#1d2c46',
          },
          Table: { headerBg: '#f8fafc', cellPaddingBlock: 20 },
        },
      };
