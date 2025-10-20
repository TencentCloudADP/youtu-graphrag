import { source } from '@/lib/source';
import {
  DocsBody,
  DocsDescription,
  DocsTitle,
} from 'fumadocs-ui/page';
import { notFound } from 'next/navigation';
import { getMDXComponents } from '@/mdx-components';
import { ClientComments, CustomDocsPage } from '@/components/docs';

export default async function Page({
  params
}: {
  params: Promise<{ slug?: string[]; lang: string }>
}) {
  // 使用await解构params
  const resolvedParams = await params;
  const { slug, lang } = resolvedParams;
  
  const page = source.getPage(slug, lang);
  
  if (!page) {
    // 尝试查找英文页面作为回退
    const englishPage = lang !== 'en' ? source.getPage(slug, 'en') : null;
    if (englishPage) {
      return renderPage(englishPage);
    }
    
    // 如果都没有找到，返回404
    notFound();
  }
  
  return renderPage(page);
}

// 渲染页面内容
function renderPage(page: any) {
  const MDXContent = page.data.body;
  
  // 全局评论控制：通过环境变量控制，优先级：环境变量 > 页面设置 > 默认值
  const globalCommentsEnabled = process.env.NEXT_PUBLIC_ENABLE_COMMENTS === 'true';
  const pageCommentsEnabled = page.data.enableComments !== false; // 页面级别设置
  const enableComments = globalCommentsEnabled && pageCommentsEnabled;
  
  // 提取作者相关信息
  const author = page.data.author;
  const avatar = page.data.avatar;
  const githubUsername = page.data.github_username;
  const xUsername = page.data.x_username;
  
  // 如果有GitHub用户名但没有头像，使用GitHub头像
  const avatarUrl = avatar || (githubUsername ? `https://avatars.githubusercontent.com/${githubUsername}` : undefined);

  return (
    <CustomDocsPage 
      toc={page.data.toc} 
      full={page.data.full}
      authorInfo={{
        author,
        avatar: avatarUrl,
        githubUsername,
        xUsername
      }}
    >
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDXContent
          components={getMDXComponents({})}
        />
        {enableComments && <ClientComments />}
      </DocsBody>
    </CustomDocsPage>
  );
}

// 生成静态参数列表
export async function generateStaticParams() {
  return source.generateParams();
}

// 生成页面元数据
export async function generateMetadata({
  params
}: {
  params: Promise<{ slug?: string[]; lang: string }>
}) {
  // 使用await解构params
  const resolvedParams = await params;
  const { slug, lang } = resolvedParams;
  
  const page = source.getPage(slug, lang);
  
  if (!page) {
    // 尝试获取英文页面的元数据
    const englishPage = lang !== 'en' ? source.getPage(slug, 'en') : null;
    if (englishPage) {
      return {
        title: englishPage.data.title,
        description: englishPage.data.description,
      };
    }
    
    notFound();
  }

  return {
    title: page.data.title,
    description: page.data.description,
  };
}

// 使页面静态渲染
export const dynamicParams = false; 