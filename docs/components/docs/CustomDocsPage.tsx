import React, { ReactNode } from 'react';
import { DocsPage, DocsPageProps } from 'fumadocs-ui/page';
import { AuthorInfo, AuthorInfoProps } from './AuthorInfo';

export interface CustomDocsPageProps extends DocsPageProps {
  authorInfo?: AuthorInfoProps;
}

export default function CustomDocsPage({
  children,
  authorInfo,
  ...props
}: CustomDocsPageProps) {
  // 将作者展示在 Toc 头部，便于与文档内容关联
  const customTocOptions = authorInfo ? {
    ...props.tableOfContent,
    header: (
      <div className="mb-6">
        <AuthorInfo {...authorInfo} />
      </div>
    )
  } : props.tableOfContent;

  return (
    <DocsPage 
      {...props}
      tableOfContent={customTocOptions}
    >
      {children}
    </DocsPage>
  );
} 
