import {defineTheme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral';

/**
 * Astryx Neutral, recolored to Home Assistant's default light and dark surfaces.
 * The accent is Home Assistant blue (#03a9f4). Labels on that blue are near-black
 * so the text stays readable; the brighter blue is the one in the Home Assistant UI.
 */
export const homeAssistantTheme = defineTheme({
  name: 'home-assistant',
  extends: neutralTheme,
  typography: {
    scale: {base: 14, ratio: 1.2},
    body: {
      family: 'system-ui',
      fallbacks: 'Roboto, "Segoe UI", Helvetica, Arial, sans-serif',
    },
    heading: {
      family: 'system-ui',
      fallbacks: 'Roboto, "Segoe UI", Helvetica, Arial, sans-serif',
      weights: {3: 'bold', 4: 'bold'},
    },
  },
  tokens: {
    '--color-background-body': ['#fafafa', '#111111'],
    '--color-background-surface': ['#ffffff', '#1c1c1c'],
    '--color-background-card': ['#ffffff', '#1c1c1c'],
    '--color-background-popover': ['#ffffff', '#202124'],
    '--color-background-muted': ['#f4f4f5', '#191919'],
    '--color-text-primary': ['#212121', '#e1e1e1'],
    '--color-text-secondary': ['#727272', '#9b9b9b'],
    '--color-text-disabled': ['#9e9e9e', '#6f6f6f'],
    '--color-border': ['#e0e0e0', '#ffffff1f'],
    '--color-border-emphasized': ['#bdbdbd', '#ffffff33'],
    '--color-accent': ['#03a9f4', '#03a9f4'],
    '--color-accent-muted': ['#e1f5fe', '#03a9f429'],
    '--color-on-accent': ['#102027', '#102027'],
    '--color-text-accent': ['#0277bd', '#81d4fa'],
    '--color-icon-accent': ['#0288d1', '#03a9f4'],
    '--color-info': ['#0288d1', '#29b6f6'],
    '--color-info-muted': ['#e1f5fe', '#03a9f429'],
    '--color-on-info': ['#ffffff', '#102027'],
  },
});
