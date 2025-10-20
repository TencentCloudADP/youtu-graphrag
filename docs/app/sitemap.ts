import type { MetadataRoute } from 'next';
import { i18n } from '@/lib/i18n';

// 静态导出配置
export const dynamic = 'force-static';
export const revalidate = false;

// 获取基本URL，根据环境变量设置或默认为本地开发URL
const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || 'https://hellodify.com';

// 确保 BASE_URL 包含协议前缀
function formatBaseUrl(url: string): string {
  // 如果URL已经包含协议前缀，直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  // 如果是本地开发环境
  if (url.includes('localhost')) {
    return `http://${url}`;
  }
  
  // 默认添加https前缀
  return `https://${url}`;
}

export default function sitemap(): MetadataRoute.Sitemap {
  // 支持的语言
  const languages = i18n.languages;
  const defaultLanguage = i18n.defaultLanguage;
  const docsBase = '/docs';
  
  // 格式化基本URL
  const formattedBaseUrl = formatBaseUrl(BASE_URL);
  
  // 创建包含所有语言版本的站点地图条目
  const sitemapEntries: MetadataRoute.Sitemap = [];

  // 首页
  const homeAlternates: Record<string, string> = {};
  languages.forEach((lang) => {
    homeAlternates[lang] = `${formattedBaseUrl}/${lang}`;
  });
  sitemapEntries.push({
    url: `${formattedBaseUrl}/`,
    lastModified: new Date(),
    changeFrequency: 'daily',
    priority: 1.0,
    alternates: {
      languages: homeAlternates,
    },
  });

  // 文档相关路由（不带语言前缀，后续拼接）
  const docSlugs = [
    '',
    '/quickstart',
    '/contributing',
    '/workflow',
    '/workflow/workflow-chatflow-difference',
    '/workflow/twitter-mbti-receipt',
    '/knowledge-base/image-retrieval',
    '/plugin',
    '/plugin/ssh-plugin-vibe-coding',
    '/plugin/cursor-rules',
  ];

  docSlugs.forEach((slug) => {
    const languageAlternates: Record<string, string> = {};
    languages.forEach((lang) => {
      languageAlternates[lang] = `${formattedBaseUrl}${docsBase}/${lang}${slug}`;
    });

    const mainRoute = `${docsBase}/${defaultLanguage}${slug}`;
    const priority =
      slug === ''
        ? 0.9
        : slug === '/quickstart'
          ? 0.8
          : 0.7;

    sitemapEntries.push({
      url: `${formattedBaseUrl}${mainRoute}`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority,
      alternates: {
        languages: languageAlternates,
      },
    });
  });

  return sitemapEntries;
}
