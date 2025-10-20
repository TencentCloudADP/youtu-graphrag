export type BooleanString = '0' | '1';
export type InputPosition = 'top' | 'bottom';
export type Repo = `${string}/${string}`;
export type Mapping = 'url' | 'title' | 'og:title' | 'specific' | 'number' | 'pathname';
export type GenericString = string & Record<never, never>;
export type Theme = 'light' | 'light_high_contrast' | 'light_protanopia' | 'light_tritanopia' | 'dark' | 'dark_high_contrast' | 'dark_protanopia' | 'dark_tritanopia' | 'dark_dimmed' | 'preferred_color_scheme' | 'transparent_dark' | 'noborder_light' | 'noborder_dark' | 'noborder_gray' | 'cobalt' | 'purple_dark' | 'gruvbox' | 'gruvbox_dark' | 'gruvbox_light' | 'catppuccin_latte' | 'catppuccin_frappe' | 'catppuccin_macchiato' | 'catppuccin_mocha' | 'fro' | `https://${string}` | GenericString;
export type AvailableLanguage = 'ar' | 'be' | 'bg' | 'ca' | 'cs' | 'da' | 'de' | 'en' | 'eo' | 'es' | 'eu' | 'fa' | 'fr' | 'gr' | 'gsw' | 'hbs' | 'he' | 'hu' | 'id' | 'it' | 'ja' | 'kh' | 'ko' | 'nl' | 'pl' | 'pt' | 'ro' | 'ru' | 'th' | 'tr' | 'vi' | 'uk' | 'uz' | 'zh-CN' | 'zh-Hans' | 'zh-Hant' | 'zh-HK' | 'zh-TW' | GenericString;
export type Loading = 'lazy' | 'eager';
