import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/app/layout.config';
import type { ReactNode } from 'react';
import type { Translations } from 'fumadocs-ui/i18n';
import { i18n } from '@/lib/i18n';
import { I18nProvider } from '@/components/i18n-provider';

// 为静态导出生成静态参数
export function generateStaticParams() {
  return i18n.languages.map((lang) => ({
    lang,
  }));
}

const zh: Partial<Translations> = {
  search: '搜索'
};


export default async function Layout({
  children,
  params
}: {
  children: ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const pageTree = source.pageTree[lang] || source.pageTree.en;

  const translations = {
    zh,
  }[lang];

  return (
    <I18nProvider
      locale={lang}
      translations={translations}
    >
      <DocsLayout
        {...baseOptions(lang)}
        tree={pageTree}
      >
        {children}
      </DocsLayout>
    </I18nProvider>
  );
}
