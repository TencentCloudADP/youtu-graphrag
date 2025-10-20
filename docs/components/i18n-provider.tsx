'use client';

import { usePathname } from 'next/navigation';
import { RootProvider } from 'fumadocs-ui/provider';
import type { ReactNode } from 'react';
import type { Translations } from 'fumadocs-ui/i18n';
import { generateI18nUrl } from '@/lib/i18n-utils';

interface I18nProviderProps {
  children: ReactNode;
  locale: string;
  translations?: Partial<Translations>;
}

const locales = [
  {
    name: 'English',
    locale: 'en',
  },
  {
    name: '中文',
    locale: 'zh',
  },
];

export function I18nProvider({ children, locale, translations }: I18nProviderProps) {
  const pathname = usePathname();

  return (
    <RootProvider
      i18n={{
        locale,
        locales: locales.map(localeItem => ({
          ...localeItem,
          // 使用当前路径动态生成语言切换 URL
          url: generateI18nUrl(localeItem.locale, pathname)
        })),
        translations,
      }}
    >
      {children}
    </RootProvider>
  );
}