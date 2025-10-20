import React, { ReactNode } from 'react';

interface PictureInPictureProps {
  children: ReactNode;
}

export function PictureInPicture({ children }: PictureInPictureProps) {
  return (
    <div className="pip-container">
      {children}
    </div>
  );
}

export function createPictureInPicture(content: ReactNode) {
  return <PictureInPicture>{content}</PictureInPicture>;
} 