import '../global.css';
import 'remixicon/fonts/remixicon.css';
import { RootProvider } from 'fumadocs-ui/provider';
import { Inter } from 'next/font/google';
import { use } from 'react';
import type { ReactNode } from 'react';
import type { Translations } from 'fumadocs-ui/i18n';
import type { Metadata } from 'next';
import { i18n } from '@/lib/i18n';

// 为静态导出生成静态参数
export function generateStaticParams() {
  return i18n.languages.map((lang) => ({
    lang,
  }));
}

const inter = Inter({
  subsets: ['latin'],
});

// 中文翻译
const zh: Partial<Translations> = {
  search: '搜索'
};


// 可用语言配置
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

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }) {
  // 解析Promise获取语言参数
  const resolvedParams = await params;
  const { lang } = resolvedParams;
  
  // 根据不同语言设置不同的标题和描述
  const titles = {
    en: 'Hello ADP - ADP Tutorials with Best Practice',
    zh: 'Hello ADP - 全网最齐全的免费ADP教程与最佳实践',
  };

  const descriptions = {
    en: 'ADP tutorials, guides, and best practices for building AI workflows and applications with ADP',
    zh: 'ADP教程、入门指南与最佳实践，涵盖AI应用与工作流构建',
  };

  const keywordsMap = {
    en: ['ADP', 'ADP tutorial', 'ADP guide', 'ADP best practices', 'AI workflow', 'AI application'],
    zh: ['ADP', 'ADP教程', 'ADP指南', 'ADP最佳实践', 'AI工作流', 'AI应用'],
  } as const;

  const locales = {
    en: 'en_US',
    zh: 'zh_CN',
  };

  const title = titles[lang as keyof typeof titles] || titles.en;
  const description = descriptions[lang as keyof typeof descriptions] || descriptions.en;
  const keywords = keywordsMap[lang as keyof typeof keywordsMap] || keywordsMap.en;
  const locale = locales[lang as keyof typeof locales] || locales.en;

  return {
    title,
    description,
    keywords,
    icons: {
      icon: '/images/youtu-logo.svg',
      apple: '/images/youtu-logo.svg',
    },
    openGraph: {
      title,
      description,
      images: [
        {
          url: '/images/hello-adp.png',
          width: 1200,
          height: 630,
          alt: 'Hello Dify Logo',
        },
      ],
      locale,
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: ['/images/hello-adp.png'],
    },
  };
}

export default function Layout({ 
  children,
  params 
}: { 
  children: ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const resolvedParams = use(params);
  const { lang } = resolvedParams;
  
  // 根据语言选择翻译
  const translations = {
    zh
  }[lang];

  return (
    <RootProvider
      i18n={{
        locale: lang,
        locales,
        translations
      }}
    >
      {children}
    </RootProvider>
  );
}
