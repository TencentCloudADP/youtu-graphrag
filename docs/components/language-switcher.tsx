'use client';

import { usePathname } from 'next/navigation';
import { generateI18nUrl } from '@/lib/i18n-utils';

interface LanguageSwitcherProps {
  currentLocale: string;
  locales: Array<{
    name: string;
    locale: string;
  }>;
}

export function LanguageSwitcher({ currentLocale, locales }: LanguageSwitcherProps) {
  const pathname = usePathname();

  return locales.map(locale => ({
    ...locale,
    url: generateI18nUrl(locale.locale, pathname)
  }));
}