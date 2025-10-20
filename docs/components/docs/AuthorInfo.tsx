import React from 'react';
import Image from 'next/image';
import Link from 'next/link';

export interface AuthorInfoProps {
  author?: string;
  avatar?: string;
  githubUsername?: string;
  xUsername?: string;
}

export function AuthorInfo({ author, avatar, githubUsername, xUsername }: AuthorInfoProps) {
  if (!author && !githubUsername && !xUsername) {
    return null;
  }

  // 如果有GitHub用户名但没有头像，使用GitHub头像
  const avatarUrl = avatar || (githubUsername ? `https://avatars.githubusercontent.com/${githubUsername}` : undefined);

  return (
    <div className="flex flex-col items-center gap-2">
      {avatarUrl && (
        <div className="relative h-16 w-16 overflow-hidden rounded-full mb-2">
          <Image
            src={avatarUrl}
            alt={author || "Author"}
            width={64}
            height={64}
            className="object-cover"
          />
        </div>
      )}
      {author && (
        <span className="text-sm font-medium text-center">{author}</span>
      )}
      <div className="flex gap-3 justify-center">
        {githubUsername && (
          <Link 
            href={`https://github.com/${githubUsername}`} 
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-fd-muted-foreground hover:text-fd-primary"
          >
            <i className="ri-github-fill ri-lg"></i>
          </Link>
        )}
        {xUsername && (
          <Link 
            href={`https://x.com/${xUsername}`} 
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-fd-muted-foreground hover:text-fd-primary"
          >
            <i className="ri-twitter-x-fill ri-lg"></i>
          </Link>
        )}
      </div>
    </div>
  );
}

export default AuthorInfo; 
