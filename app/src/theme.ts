import { buildTheme, ITextTheme, ITheme, mergeTheme, ThemeMap } from '@kibalabs/ui-react';
import { buildToastThemes } from '@kibalabs/ui-react-toast';

export const buildRangeSeekerTheme = (): ITheme => {
  const baseTheme = buildTheme();
  const textThemes: ThemeMap<ITextTheme> = {
    ...baseTheme.texts,
    default: mergeTheme(baseTheme.texts.default, {
      'font-family': '"Source Sans Pro", sans-serif',
      'font-weight': '400',
    }),
    header1: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '800',
      color: '$colors.brandPrimary',
    },
    header2: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '700',
      color: '$colors.text',
    },
    header3: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '600',
      color: '$colors.text',
    },
  };

  const theme = buildTheme({
    colors: {
      background: '#141414',
      brandPrimary: '#CCF6F9',
      brandSecondary: '#C4F2C8',
    },
    fonts: {
      main: {
        url: 'https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&family=Source+Serif+Pro:wght@400;600;700&display=swap',
      },
    },
    texts: textThemes,
    inputWrappers: {
      default: {
        normal: {
          default: {
            background: {
              'background-color': 'rgba(255, 255, 255, 0.05)',
              'border-color': 'rgba(255, 255, 255, 0.08)',
            },
          },
        },
      },
    },
  });
  theme.toasts = buildToastThemes(theme.colors, theme.dimensions, theme.boxes, theme.texts);
  return theme;
};
