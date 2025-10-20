import { i18n } from '@/lib/i18n';
import { NextRequest, NextResponse } from 'next/server';

const DOCS_PREFIX = '/docs';

// 检查是否为静态导出模式（GitHub Pages）
const isStaticExport = process.env.NEXT_PUBLIC_BASE_PATH;

function resolveLocale(request: NextRequest) {
  const stored = request.cookies.get('NEXT_LOCALE')?.value;
  if (stored && i18n.languages.includes(stored)) {
    return stored;
  }

  const acceptLanguage = request.headers.get('Accept-Language') || '';
  if (acceptLanguage.includes('zh')) {
    return 'zh';
  }

  return i18n.defaultLanguage ?? 'en';
}

function shouldBypass(pathname: string) {
  return (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/public/') ||
    pathname === '/sitemap.xml' ||
    /\.(jpg|png|svg|gif)$/.test(pathname)
  );
}

function setLocaleCookie(response: NextResponse, locale: string) {
  response.cookies.set('NEXT_LOCALE', locale, {
    path: '/',
    maxAge: 31536000,
  });
}

function buildDocsPath(locale: string, rest: string[] = []) {
  const segments = [DOCS_PREFIX, locale, ...rest.filter(Boolean)];
  return segments.join('/').replace(/\/{2,}/g, '/');
}

// 创建基于Fumadocs的i18n中间件
export function middleware(request: NextRequest) {
  // 在静态导出模式下（GitHub Pages），跳过所有中间件逻辑
  if (isStaticExport) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;

  if (shouldBypass(pathname)) {
    return NextResponse.next();
  }

  const locale = resolveLocale(request);

  if (pathname === '/' || pathname === '') {
    const url = request.nextUrl.clone();
    url.pathname = DOCS_PREFIX;
    const response = NextResponse.redirect(url);
    setLocaleCookie(response, locale);
    return response;
  }

  if (pathname === DOCS_PREFIX || pathname === `${DOCS_PREFIX}/`) {
    const url = request.nextUrl.clone();
    url.pathname = buildDocsPath(locale);
    const response = NextResponse.redirect(url);
    setLocaleCookie(response, locale);
    return response;
  }

  if (pathname.startsWith(`${DOCS_PREFIX}/`)) {
    const segments = pathname.split('/').filter(Boolean);
    const lang = segments[1];
    const rest = segments.slice(2);

    if (lang && i18n.languages.includes(lang)) {
      if (rest.length > 0 && i18n.languages.includes(rest[0])) {
        const url = request.nextUrl.clone();
        url.pathname = buildDocsPath(lang, rest.slice(1));
        const response = NextResponse.redirect(url);
        setLocaleCookie(response, lang);
        return response;
      }

      const response = NextResponse.next();
      setLocaleCookie(response, lang);
      return response;
    }

    const url = request.nextUrl.clone();
    url.pathname = buildDocsPath(locale, rest);
    const response = NextResponse.redirect(url);
    setLocaleCookie(response, locale);
    return response;
  }

  const legacyDocs = pathname.match(/^\/(en|zh)\/docs(\/.*)?$/);
  if (legacyDocs) {
    const [, legacyLocale, rest = ''] = legacyDocs;
    const segments = rest.split('/').filter(Boolean);
    const url = request.nextUrl.clone();
    url.pathname = buildDocsPath(legacyLocale, segments);
    const response = NextResponse.redirect(url);
    setLocaleCookie(response, legacyLocale);
    return response;
  }

  if (/^\/(en|zh)(\/|$)/.test(pathname)) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${pathname.startsWith('/') ? pathname : `/${pathname}`}`;
  const response = NextResponse.redirect(url);
  setLocaleCookie(response, locale);
  return response;
}

// 配置匹配路径
export const config = {
  // 匹配所有路径，但排除_next、static等
  matcher: ['/((?!_next|static|favicon.ico|.*\\.(?:jpg|png|svg|gif)).*)']
};
