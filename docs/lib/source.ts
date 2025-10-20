import { docs } from '@/.source';
import { i18n } from '@/lib/i18n';
import { loader } from 'fumadocs-core/source';
import { createElement, ReactElement } from 'react';
import 'remixicon/fonts/remixicon.css';

// 图标处理器函数，将图标名称转换为JSX元素
const iconHandler = (icon: string | undefined): ReactElement | undefined => {
  if (!icon) return undefined;
  
  // 使用Remixicon的CSS类实现
  return createElement('i', {
    className: `ri-${icon} ri-lg`
  });
};

// See https://fumadocs.vercel.app/docs/headless/source-api for more info
const resolveDocsUrl = (slugs: string[], locale?: string) => {
  const segments = ['docs'];
  const language = locale && i18n.languages.includes(locale) ? locale : i18n.defaultLanguage;
  if (language) {
    segments.push(language);
  }
  segments.push(...slugs);
  return `/${segments.filter(Boolean).join('/')}`;
};

export const source = loader({
  i18n,
  // it assigns a URL to your pages
  baseUrl: '/docs',
  url: resolveDocsUrl,
  source: docs.toFumadocsSource(),
  icon: iconHandler, // 添加图标处理器
});
