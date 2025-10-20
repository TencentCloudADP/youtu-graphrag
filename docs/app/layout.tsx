import './global.css';
import 'remixicon/fonts/remixicon.css';
import { RootProvider } from 'fumadocs-ui/provider';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import type { ReactNode } from 'react';
import type { Metadata } from 'next';

const inter = Inter({
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Youtu-Embedding - 腾讯优图文本表示模型文档',
  description: 'Youtu-Embedding是腾讯优图实验室开源的通用文本表示模型，支持信息检索、语义相似度、聚类、重排序与分类等多种自然语言处理任务。',
  icons: {
    icon: '/images/youtu-logo.svg',
    apple: '/images/youtu-logo.svg',
  },
  openGraph: {
    title: 'Youtu-Embedding - 腾讯优图文本表示模型文档',
    description: 'Youtu-Embedding是腾讯优图实验室开源的通用文本表示模型，支持信息检索、语义相似度、聚类、重排序与分类等多种自然语言处理任务。',
    images: [
      {
        url: '/images/youtu-logo.svg',
        width: 1200,
        height: 630,
        alt: 'Hello ADP Logo',
      },
    ],
    locale: 'zh_CN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Hello ADP - 学习和分享腾讯云智能体平台最佳实践',
    description: '帮助新手快速上手腾讯云智能体平台（Tencent Cloud Agent Development Platform，ADP）的教程',
    images: ['/images/hello-adp.png'],
  },
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=G-1VYY79X6HL"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-1VYY79X6HL');
          `}
        </Script>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
