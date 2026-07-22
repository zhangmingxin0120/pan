import type { GlobalThemeOverrides } from 'naive-ui'

export const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#176B5B',
    primaryColorHover: '#12584B',
    primaryColorPressed: '#0D463C',
    primaryColorSuppl: '#176B5B',
    borderRadius: '8px',
    borderColor: '#DDE4E0',
    textColorBase: '#1C2824',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  Button: { heightMedium: '40px', borderRadiusMedium: '8px' },
  Input: { heightMedium: '40px', borderRadius: '8px' },
  Dialog: { borderRadius: '12px' },
  Dropdown: { borderRadius: '8px' },
}

