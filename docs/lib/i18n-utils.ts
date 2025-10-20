/**
 * Generate proper i18n URL for language switching
 */
export function generateI18nUrl(targetLocale: string, currentPathname: string): string {
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
  
  // Remove basePath from pathname if present
  let pathname = currentPathname;
  if (basePath && pathname.startsWith(basePath)) {
    pathname = pathname.slice(basePath.length);
  }
  
  // Ensure pathname starts with /
  if (!pathname.startsWith('/')) {
    pathname = `/${pathname}`;
  }
  
  // Split pathname into segments
  const segments = pathname.split('/').filter(Boolean);
  
  // Check if first segment after /docs is a language code
  if (segments[0] === 'docs' && segments[1]) {
    // Replace the language code
    segments[1] = targetLocale;
    return `${basePath}/${segments.join('/')}`;
  } else {
    // Default to docs structure
    return `${basePath}/docs/${targetLocale}/`;
  }
}