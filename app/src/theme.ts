import { buildTheme, ITextTheme, ITheme, mergeTheme, ThemeMap } from '@kibalabs/ui-react';
import { buildToastThemes } from '@kibalabs/ui-react-toast';

export const buildRangeSeekerTheme = (): ITheme => {
  const baseTheme = buildTheme();
  const textThemes: ThemeMap<ITextTheme> = {
    ...baseTheme.texts,
    default: mergeTheme(baseTheme.texts.default, {
      'font-family': '"Source Sans Pro", sans-serif',
      'font-weight': '400',
      'font-size': '18px',
    }),
    header1: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '800',
      color: '$colors.brandPrimary',
    },
    header2: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '600',
      color: '$colors.text',
    },
    header3: {
      'font-family': '"Source Serif Pro", serif',
      'font-weight': '600',
      color: '$colors.text',
    },
    extraLarge: {
      'font-size': '1.75em',
    },
  };

  const theme = buildTheme({
    colors: {
      background: '#141414',
      brandPrimary: 'rgb(110,211,233)',
      brandSecondary: '#C4F2C8',
    },
    fonts: {
      main: {
        url: 'https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&family=Source+Serif+Pro:wght@400;600;700&display=swap',
      },
    },
    texts: textThemes,
    buttons: {
      default: {
        normal: {
          default: {
            background: {
              'backdrop-filter': 'blur(10px)',
              '-webkit-backdrop-filter': 'blur(10px)',
            },
          },
        },
      },
      primary: {
        normal: {
          default: {
            background: {
              'background-color': '$colors.brandPrimaryClear90',
              'border-width': '0',
            },
            text: {
              color: '$colors.brandPrimary',
            },
          },
          hover: {
            background: {
              'background-color': '$colors.brandPrimaryClear80',
            },
          },
        },
      },
      secondary: {
        normal: {
          default: {
            background: {
              'background-color': '$colors.backgroundLight05',
              'border-width': '0',
            },
          },
          hover: {
            background: {
              'background-color': '$colors.backgroundLight10',
            },
          },
        },
      },
      sidebar: {
        normal: {
          default: {
            background: {
              'border-color': '$colors.backgroundClear90',
              'border-style': 'solid',
              'border-width': '0 0 1px 0',
              'border-radius': '0',
              padding: `${baseTheme.dimensions.paddingWide} ${baseTheme.dimensions.paddingWide}`,
            },
            text: {
              'font-weight': 'normal',
              color: '$colors.text',
            },
          },
        },
      },
      sidebarActive: {
        normal: {
          default: {
            background: {
              'background-color': '$colors.brandPrimaryDark50',
            },
            text: {
              color: '$colors.text',
            },
          },
        },
      },
    },
    boxes: {
      card: {
        'background-color': '$colors.backgroundClear50',
        'backdrop-filter': 'blur(10px)',
        '-webkit-backdrop-filter': 'blur(10px)',
        border: '0px',
        'box-shadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
      },
      sidebar: {
        'border-width': '0',
        'background-color': '$colors.backgroundClear50',
        'border-radius': '0',
        'backdrop-filter': 'blur(10px)',
        '-webkit-backdrop-filter': 'blur(10px)',
      },
    },
    inputWrappers: {
      default: {
        normal: {
          default: {
            background: {
              'background-color': '$colors.backgroundLight05',
              'border-color': '$colors.backgroundLight10',
            },
          },
        },
      },
    },
  });
  theme.toasts = buildToastThemes(theme.colors, theme.dimensions, theme.boxes, theme.texts);
  return theme;
};
