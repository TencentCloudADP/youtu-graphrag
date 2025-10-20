import path from 'path';
import { promises as fs } from 'fs';
import LandingShowcase from '@/components/home/LandingShowcase';
import { source } from '@/lib/source';
import { i18n } from '@/lib/i18n';

// 为静态导出生成静态参数
export function generateStaticParams() {
  return i18n.languages.map((lang) => ({
    lang,
  }));
}

const DOCS_ROOT = path.join(process.cwd(), 'content/docs');

const copyMap = {
  en: {
    heroTitle: 'Workflow Automation Guides',
    heroSubtitle: 'Real-world Tencent Cloud ADP playbooks curated for builders and operators.',
    highlightPrefix: '',
    highlightSuffix: ' Workflow Recipes',
    searchPlaceholder: 'Search apps, workflows, tutorials…',
    searchCta: 'Search',
    filterHeading: 'Browse by area',
    featuredHeading: 'Newcomer essentials: learn by doing',
    defaultCategory: 'Overview',
    updatedPrefix: 'Updated',
    authorFallback: 'Unknown author',
    openLabel: 'Open guide',
    emptyStateTitle: 'No guides yet',
    emptyStateSubtitle: 'Add a new MDX document under content/docs to see it here.',
    demoPrimary: 'Try live demo',
    articleCta: 'Open article',
    demoExternal: 'Open demo in new tab',
    modalTitle: 'Interactive demo',
    modalClose: 'Close',
    modalFallback: 'Unable to load the embedded preview. Open it in a new tab instead.',
    featuredSubline: 'Dive into the step-by-step walkthrough',
  },
  zh: {
    heroTitle: '工作流自动化指南',
    heroSubtitle: '面向构建者的腾讯云 ADP 实战案例合集。',
    highlightPrefix: '已收录 ',
    highlightSuffix: ' 篇工作流模板',
    searchPlaceholder: '搜索应用、工作流或关键词…',
    searchCta: '搜索',
    filterHeading: '按领域浏览',
    featuredHeading: '新人必读：以做促学',
    defaultCategory: '总览',
    updatedPrefix: '最近更新',
    authorFallback: '未署名作者',
    openLabel: '查看指南',
    emptyStateTitle: '暂无指南',
    emptyStateSubtitle: '在 content/docs 下新增 MDX 文档后将自动展示。',
    demoPrimary: '立即体验',
    articleCta: '访问文章',
    demoExternal: '新标签页打开体验',
    modalTitle: '在线体验',
    modalClose: '关闭',
    modalFallback: '嵌入页面无法加载，请在新标签页打开。',
    featuredSubline: '点击开始体验完整教程',
  },
} as const;

type LanguageKey = keyof typeof copyMap;

type RawArticleCard = {
  id: string;
  href: string;
  title: string;
  description?: string;
  author?: string;
  avatar?: string;
  categoryKey: string;
  categoryLabel: string;
  demoUrl?: string;
  mtime: number;
};

type ArticleCardView = Omit<RawArticleCard, 'mtime'> & {
  updatedLabel: string;
};

type CategoryLink = {
  key: string;
  label: string;
  href: string;
};

function normalizeLanguage(lang: string): LanguageKey {
  if ((copyMap as Record<string, unknown>)[lang]) {
    return lang as LanguageKey;
  }
  return i18n.defaultLanguage as LanguageKey;
}

function segmentFormatter(segment: string) {
  return segment
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function resolveRelativePath(page: ReturnType<typeof source.getPages>[number]) {
  const dir = page.file.dirname && page.file.dirname !== '.' ? page.file.dirname : '';
  const ext = page.file.ext ? page.file.ext : '.mdx';
  const filename = `${page.file.name}${ext}`;
  return dir ? `${dir}/${filename}` : filename;
}

async function resolveMTime(relativePath: string) {
  const absolute = path.join(DOCS_ROOT, relativePath);
  try {
    const stat = await fs.stat(absolute);
    return stat.mtimeMs;
  } catch (error) {
    if (!relativePath.endsWith('.mdx')) {
      const fallback = path.join(DOCS_ROOT, `${relativePath}.mdx`);
      try {
        const stat = await fs.stat(fallback);
        return stat.mtimeMs;
      } catch (innerError) {
        console.warn('Failed to resolve MDX path for home cards:', relativePath, innerError);
      }
    } else {
      console.warn('Failed to resolve MDX path for home cards:', relativePath, error);
    }
  }
  return 0;
}

function formatCategoryLabel(key: string, fallback: string) {
  if (!key) return fallback;
  return key.split('/').map(segmentFormatter).join(' / ');
}

function formatRelativeUpdate(timestamp: number, lang: LanguageKey) {
  if (!timestamp) return '';

  const now = Date.now();
  const diffInSeconds = (now - timestamp) / 1000;
  const units: { limit: number; divisor: number; unit: Intl.RelativeTimeFormatUnit }[] = [
    { limit: 60, divisor: 1, unit: 'second' },
    { limit: 3600, divisor: 60, unit: 'minute' },
    { limit: 86_400, divisor: 3600, unit: 'hour' },
    { limit: 604_800, divisor: 86_400, unit: 'day' },
    { limit: 2_592_000, divisor: 604_800, unit: 'week' },
    { limit: 31_536_000, divisor: 2_592_000, unit: 'month' },
    { limit: Infinity, divisor: 31_536_000, unit: 'year' },
  ];

  const locale = lang === 'zh' ? 'zh-CN' : 'en';
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

  for (const { limit, divisor, unit } of units) {
    if (Math.abs(diffInSeconds) < limit) {
      const value = Math.round(diffInSeconds / divisor);
      return rtf.format(-value, unit);
    }
  }

  return '';
}

async function getArticles(lang: LanguageKey): Promise<RawArticleCard[]> {
  const preferredPages = source.getPages(lang);
  const pages = preferredPages.length
    ? preferredPages
    : lang !== (i18n.defaultLanguage as LanguageKey)
      ? source.getPages(i18n.defaultLanguage as LanguageKey)
      : preferredPages;

  const results = await Promise.all(
    pages
      .filter((page) => page?.data?.title)
      .map(async (page) => {
        const relativePath = resolveRelativePath(page);
        const mtime = await resolveMTime(relativePath);
        const segments = [...page.slugs];
        const categorySegments = segments.slice(0, -1);
        const categoryKey = categorySegments.join('/');
        const categoryLabel = formatCategoryLabel(
          categoryKey,
          copyMap[lang].defaultCategory,
        );
        const avatar =
          (page.data as any).avatar ||
          ((page.data as any).github_username
            ? `https://avatars.githubusercontent.com/${(page.data as any).github_username}`
            : undefined);

        return {
          id: page.url,
          href: page.url,
          title: page.data.title as string,
          description: page.data.description as string | undefined,
          author: (page.data as any).author as string | undefined,
          avatar,
          categoryKey,
          categoryLabel,
          demoUrl: (page.data as any).demo_url as string | undefined,
          mtime,
        } satisfies RawArticleCard;
      }),
  );

  return results
    .sort((a, b) => b.mtime - a.mtime || a.title.localeCompare(b.title));
}

async function buildCategoryLinks(
  articles: RawArticleCard[],
  lang: LanguageKey,
): Promise<CategoryLink[]> {
  const seen = new Set<string>();
  const links: CategoryLink[] = [];

  for (const article of articles) {
    if (seen.has(article.categoryKey)) continue;
    seen.add(article.categoryKey);

    const segments = article.categoryKey ? article.categoryKey.split('/') : [];
    const directPage = segments.length
      ? source.getPage(segments, lang) ||
        (lang !== (i18n.defaultLanguage as LanguageKey)
          ? source.getPage(segments, i18n.defaultLanguage as LanguageKey)
          : undefined)
      : undefined;

    const href = directPage?.url
      || articles.find((item) => item.categoryKey === article.categoryKey)?.href
      || `/docs/${lang}`;

    links.push({
      key: article.categoryKey,
      label: article.categoryLabel,
      href,
    });
  }

  return links;
}

export default async function HomePage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const language = normalizeLanguage(lang);
  const copy = copyMap[language];

  const articlesRaw = await getArticles(language);
  const categories = await buildCategoryLinks(articlesRaw, language);

  const articleViews: ArticleCardView[] = articlesRaw.map(({ mtime, ...rest }) => ({
    ...rest,
    updatedLabel: formatRelativeUpdate(mtime, language),
  }));

  const totalCount = articleViews.length;
  const [featured, ...rest] = articleViews;
  const searchHref = `/docs/${language}`;

  return (
    <LandingShowcase
      copy={copy}
      totalCount={totalCount}
      categories={categories}
      featured={featured}
      rest={rest}
      searchHref={searchHref}
    />
  );
}

export type { ArticleCardView, CategoryLink };
