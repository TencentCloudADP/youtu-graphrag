import type { ReactNode } from 'react';
import { use } from 'react';
import { HomeLayout } from 'fumadocs-ui/layouts/home';
import { baseOptions } from '@/app/layout.config';
import { i18n } from '@/lib/i18n';

// 为静态导出生成静态参数
export function generateStaticParams() {
  return i18n.languages.map((lang) => ({
    lang,
  }));
}

export default function Layout({ 
  children,
  params
}: { 
  children: ReactNode;
  params: Promise<{ lang: string }>
}) {
  const resolvedParams = use(params);
  const { lang } = resolvedParams;
  
  // 根据不同语言设置链接文本
  const docText = {
    'zh': '文档',
    'ja': 'ドキュメント',
    'en': 'Documentation'
  }[lang] || 'Documentation';
  
  const githubText = {
    'zh': 'GitHub',
    'ja': 'GitHub',
    'en': 'GitHub'
  }[lang];
  
  const discordText = {
    'zh': 'Discord 社区',
    'ja': 'Discord コミュニティ',
    'en': 'Discord'
  }[lang] || 'Discord';

  return (
    <HomeLayout
      {...baseOptions(lang)}
      links={[
        {
          text: docText,
          url: `/docs/${lang}`,
        },
        {
          text: githubText,
          url: 'https://github.com/stvlynn/hello-adp',
          external: true,
        },
        {
          text: discordText,
          url: 'https://discord.gg/QjqhkHQVVM',
          external: true,
        },
      ]}
    >
      {children}
    </HomeLayout>
  );
}
