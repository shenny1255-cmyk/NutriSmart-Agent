import { Platform } from 'react-native';

export const Theme = {
  colors: {
    background: '#F2F6F4',      // --color-paper (light mint paper)
    card: '#FAFDFB',            // --color-paper-2 (elevated white card)
    cardSecondary: '#E8EEEC',   // --color-paper-3 (slightly darker tint)
    text: '#1F2E2A',            // --color-ink (dark ink)
    textSecondary: '#2C3E3A',   // --color-ink-2 (secondary text)
    textMuted: '#57706A',       // --color-muted (grey-green label text)
    border: '#E4EAE7',          // --color-rule-2 (soft gray-green divider)
    borderStrong: '#CBD5E1',    // strong input border
    accent: '#10B981',          // --color-accent (emerald green primary)
    accentStrong: '#059669',    // --color-accent-strong (active solid green)
    accentSoft: '#E6FAF0',      // --color-accent-soft (emerald tint)
    success: '#10B981',
    warning: '#F59E0B',
    warningSoft: '#FEF3C7',
    danger: '#EF4444',
    dangerSoft: '#FEE2E2',
  },
  radius: {
    sm: 8,
    md: 12,
    lg: 20,
    full: 9999,
  },
  fonts: {
    display: Platform.OS === 'ios' ? 'System' : 'sans-serif',
    body: Platform.OS === 'ios' ? 'System' : 'sans-serif',
  }
};
