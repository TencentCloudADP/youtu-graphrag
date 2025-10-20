'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { ArticleCardView, CategoryLink } from '@/app/[lang]/(home)/page';

interface LandingCopy {
  heroTitle: string;
  heroSubtitle: string;
  highlightPrefix: string;
  highlightSuffix: string;
  searchPlaceholder: string;
  searchCta: string;
  filterHeading: string;
  featuredHeading: string;
  defaultCategory: string;
  updatedPrefix: string;
  authorFallback: string;
  openLabel: string;
  emptyStateTitle: string;
  emptyStateSubtitle: string;
  demoPrimary: string;
  articleCta: string;
  demoExternal: string;
  modalTitle: string;
  modalClose: string;
  modalFallback: string;
  featuredSubline: string;
}

interface LandingShowcaseProps {
  copy: LandingCopy;
  totalCount: number;
  categories: CategoryLink[];
  featured?: ArticleCardView;
  rest: ArticleCardView[];
  searchHref: string;
}

type DemoState = {
  title: string;
  url: string;
};

function Avatar({
  name,
  avatar,
  fallback,
  size = 48,
}: {
  name?: string;
  avatar?: string;
  fallback: string;
  size?: number;
}) {
  if (avatar) {
    return (
      <Image
        src={avatar}
        alt={name || fallback}
        width={size}
        height={size}
        className="rounded-full border border-white/20 object-cover"
      />
    );
  }

  return (
    <div
      className="flex items-center justify-center rounded-full border border-white/20 bg-white/10 text-lg font-semibold text-white/80"
      style={{ width: size, height: size }}
    >
      {(name || fallback).charAt(0)}
    </div>
  );
}

export default function LandingShowcase({
  copy,
  totalCount,
  categories,
  featured,
  rest,
  searchHref,
}: LandingShowcaseProps) {
  const [activeDemo, setActiveDemo] = useState<DemoState | null>(null);

  useEffect(() => {
    if (activeDemo) {
      const original = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = original;
      };
    }
  }, [activeDemo]);

  const openDemo = (title: string, url: string) => {
    setActiveDemo({ title, url });
  };

  const closeDemo = () => {
    setActiveDemo(null);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#090417] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(104,58,183,0.35),_transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(3,169,244,0.18),_transparent_55%)]" />
        <div className="absolute -top-40 right-[-15%] h-[28rem] w-[28rem] rounded-full bg-purple-600/40 blur-[8rem]" />
        <div className="absolute bottom-[-20%] left-[-10%] h-[22rem] w-[22rem] rounded-full bg-sky-500/30 blur-[7rem]" />
      </div>

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-14 px-6 pb-24 pt-20 md:px-10">
        <header className="space-y-8 text-center md:text-left">
          <div className="inline-flex flex-wrap items-center justify-center gap-3 md:justify-start">
            <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-sm font-medium uppercase tracking-[0.2em] text-white/80">
              HELLO ADP
            </span>
            <span className="text-lg text-white/70">
              {copy.highlightPrefix}
              {totalCount}
              {copy.highlightSuffix}
            </span>
          </div>
          <h1 className="text-4xl font-bold leading-tight md:text-6xl">
            {copy.heroTitle}
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-white/70 md:mx-0">
            {copy.heroSubtitle}
          </p>
        </header>

        <section className="flex flex-col gap-6">
          <form
            action={searchHref}
            className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <input
                name="q"
                type="search"
                placeholder={copy.searchPlaceholder}
                className="w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-white/50 focus:border-white/30 focus:outline-none focus:ring-2 focus:ring-white/20"
              />
              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-fuchsia-500 to-indigo-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-fuchsia-500/25 transition hover:shadow-xl"
              >
                {copy.searchCta}
              </button>
            </div>
            {categories.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm text-white/70">
                <span className="mr-2 font-semibold text-white/80">{copy.filterHeading}</span>
                {categories.map((category) => (
                  <Link
                    key={category.key || 'root'}
                    href={category.href}
                    className="group inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-white/70 transition hover:border-white/30 hover:bg-white/10 hover:text-white"
                  >
                    <span className="h-2 w-2 rounded-full bg-gradient-to-r from-rose-500 via-fuchsia-500 to-indigo-500" />
                    {category.label}
                  </Link>
                ))}
              </div>
            )}
          </form>
        </section>

        {featured ? (
          <section className="space-y-8">
            <div className="text-sm font-semibold uppercase tracking-[0.3em] text-white/60">
              {copy.featuredHeading}
            </div>

            <article className="group relative grid gap-8 overflow-hidden rounded-3xl border border-white/10 bg-white/8 p-8 shadow-[0_20px_60px_rgba(24,6,68,0.35)] transition hover:-translate-y-1 hover:border-white/20 md:grid-cols-[1.6fr_1fr]">
              <div className="pointer-events-none absolute inset-0 rounded-3xl bg-transparent transition group-hover:bg-white/10 group-hover:backdrop-blur-[6px]" />
              <div className="relative z-10 flex flex-col">
                <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-white/80">
                  <span className="h-2 w-2 rounded-full bg-gradient-to-r from-purple-500 to-cyan-400" />
                  {featured.categoryLabel}
                </span>
                <Link
                  href={featured.href}
                  className="mt-4 text-3xl font-semibold text-white transition hover:text-white md:text-4xl"
                >
                  {featured.title}
                </Link>
                {featured.description && (
                  <p className="mt-4 text-white/70">
                    {featured.description}
                  </p>
                )}
                <div className="mt-8 flex items-center gap-4">
                  <Avatar
                    name={featured.author}
                    avatar={featured.avatar}
                    fallback={copy.authorFallback}
                    size={48}
                  />
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-white">
                      {featured.author || copy.authorFallback}
                    </span>
                    <span className="text-xs text-white/60">
                      {copy.updatedPrefix}: {featured.updatedLabel}
                    </span>
                  </div>
                </div>
                <div className="mt-8 flex flex-wrap gap-3 opacity-0 transition duration-200 group-hover:translate-y-0 group-hover:opacity-100 md:gap-4">
                  {featured.demoUrl && (
                    <button
                      type="button"
                      onClick={() => openDemo(featured.title, featured.demoUrl!)}
                      className="rounded-xl bg-gradient-to-r from-amber-500 to-pink-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-500/25 transition hover:shadow-xl"
                    >
                      {copy.demoPrimary}
                    </button>
                  )}
                  <Link
                    href={featured.href}
                    className="inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white/90 backdrop-blur transition hover:border-white/40 hover:bg-white/20"
                  >
                    {copy.articleCta}
                  </Link>
                </div>
              </div>

              <div className="relative flex h-56 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600/60 via-rose-500/50 to-amber-400/40">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle,_rgba(255,255,255,0.25),_transparent_55%)]" />
                <div className="relative z-10 flex flex-col items-center gap-4 text-center text-white">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-3xl">
                    <i className="ri-magic-line" />
                  </div>
                  <span className="text-sm font-semibold uppercase tracking-[0.3em] text-white/80">
                    {copy.openLabel}
                  </span>
                  <span className="text-xs text-white/70">
                    {copy.featuredSubline}
                  </span>
                </div>
                <div className="pointer-events-none absolute -bottom-10 right-10 h-32 w-32 rounded-full bg-white/20 blur-3xl transition duration-300 group-hover:scale-110" />
              </div>
            </article>

            {rest.length > 0 && (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {rest.map((article) => (
                  <article
                    key={article.id}
                    className="group relative flex h-full flex-col gap-6 overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:-translate-y-1 hover:border-white/20"
                  >
                    <div className="pointer-events-none absolute inset-0 rounded-2xl bg-transparent transition group-hover:bg-white/10 group-hover:backdrop-blur-[6px]" />
                    <div className="relative z-10 flex flex-col gap-4">
                      <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-medium uppercase tracking-widest text-white/70">
                        <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-fuchsia-500 to-indigo-500" />
                        {article.categoryLabel}
                      </span>
                      <Link
                        href={article.href}
                        className="text-xl font-semibold text-white transition hover:text-white"
                      >
                        {article.title}
                      </Link>
                      {article.description && (
                        <p className="text-sm leading-relaxed text-white/65">
                          {article.description}
                        </p>
                      )}
                    </div>
                    <div className="relative z-10 mt-auto flex items-center justify-between text-sm text-white/70">
                      <div className="flex items-center gap-3">
                        <Avatar
                          name={article.author}
                          avatar={article.avatar}
                          fallback={copy.authorFallback}
                          size={36}
                        />
                        <span className="font-medium text-white">
                          {article.author || copy.authorFallback}
                        </span>
                      </div>
                      <span className="text-xs text-white/60">{article.updatedLabel}</span>
                    </div>
                    <div className="relative z-10 mt-4 flex flex-wrap gap-3 opacity-0 transition duration-200 group-hover:translate-y-0 group-hover:opacity-100">
                      {article.demoUrl && (
                        <button
                          type="button"
                          onClick={() => openDemo(article.title, article.demoUrl!)}
                          className="rounded-lg bg-gradient-to-r from-amber-500 to-pink-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-amber-500/25 transition hover:shadow-lg"
                        >
                          {copy.demoPrimary}
                        </button>
                      )}
                      <Link
                        href={article.href}
                        className="inline-flex items-center justify-center rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold text-white/90 backdrop-blur transition hover:border-white/40 hover:bg-white/20"
                      >
                        {copy.articleCta}
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        ) : (
          <section className="rounded-3xl border border-white/10 bg-white/5 p-16 text-center">
            <h2 className="text-2xl font-semibold text-white">
              {copy.emptyStateTitle}
            </h2>
            <p className="mt-4 text-white/70">
              {copy.emptyStateSubtitle}
            </p>
          </section>
        )}
      </main>

      {activeDemo && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="relative flex w-[95vw] max-w-4xl flex-col gap-4 rounded-2xl border border-white/10 bg-[#0d081b] p-6 shadow-2xl">
            <header className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-semibold uppercase tracking-[0.3em] text-white/60">
                  {copy.modalTitle}
                </span>
                <h3 className="text-lg font-semibold text-white">{activeDemo.title}</h3>
              </div>
              <button
                type="button"
                onClick={closeDemo}
                className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm font-semibold text-white/70 transition hover:border-white/40 hover:bg-white/20 hover:text-white"
              >
                {copy.modalClose}
              </button>
            </header>
            <iframe
              src={activeDemo.url}
              title={activeDemo.title}
              className="h-[70vh] w-full rounded-xl border border-white/10 bg-black"
              allow="microphone; camera; clipboard-write; autoplay; encrypted-media"
              loading="lazy"
            />
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-white/50">
              <span>{copy.modalFallback}</span>
              <Link
                href={activeDemo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full border border-white/20 px-3 py-1 text-xs font-semibold text-white/80 transition hover:border-white/40 hover:text-white"
              >
                {copy.demoExternal}
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
