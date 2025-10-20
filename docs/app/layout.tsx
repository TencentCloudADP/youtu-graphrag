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
  title: 'Youtu-GraphRAG - 垂直统一的图增强复杂推理新范式',
  description: 'Youtu-GraphRAG是一个基于图 Schema 实现垂直统一的图增强推理范式，将 GraphRAG 框架精巧地集成为一个以智能体为核心的有机整体。',
  icons: {
    icon: '/images/youtu-logo.svg',
    apple: '/images/youtu-logo.svg',
  },
  openGraph: {
    title: 'Youtu-GraphRAG - 垂直统一的图增强复杂推理新范式',
    description: 'Youtu-GraphRAG是一个基于图 Schema 实现垂直统一的图增强推理范式，将 GraphRAG 框架精巧地集成为一个以智能体为核心的有机整体。',
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
        title: 'Youtu-GraphRAG - 垂直统一的图增强复杂推理新范式',
        description: 'Youtu-GraphRAG是一个基于图 Schema 实现垂直统一的图增强推理范式，将 GraphRAG 框架精巧地集成为一个以智能体为核心的有机整体。',
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
