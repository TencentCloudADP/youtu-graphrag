'use client';

import { useTheme } from 'next-themes';
import { useEffect, useRef, useState } from 'react';

interface MermaidProps {
  chart: string;
}

export function Mermaid({ chart }: MermaidProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [id] = useState<string>(`mermaid-${Math.random().toString(36).substring(2, 10)}`);
  const mermaidRef = useRef<any>(null);
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  useEffect(() => {
    let mounted = true;

    const loadMermaid = async () => {
      if (!mermaidRef.current) {
        const mod = await import('mermaid');
        mermaidRef.current = mod.default ?? mod;
      }
      return mermaidRef.current;
    };

    const renderChart = async () => {
      if (!ref.current) return;

      const mermaid = await loadMermaid();
      mermaid.initialize({
        startOnLoad: true,
        theme: isDark ? 'dark' : 'default',
        securityLevel: 'loose',
      });

      try {
        const { svg } = await mermaid.render(id, chart);
        if (mounted) {
          setSvg(svg);
        }
      } catch (error) {
        console.error('Error rendering mermaid chart:', error);
        if (mounted) {
          setSvg(`<div class="text-red-500 p-2 border border-red-400 rounded">
            Error rendering chart: ${(error as Error).message || String(error)}
          </div>`);
        }
      }
    };

    renderChart();
    return () => {
      mounted = false;
    };
  }, [chart, id, isDark]);

  return (
    <div className="my-6 overflow-x-auto">
      {!svg && <div className="h-16 w-full animate-pulse bg-fd-muted/20 rounded" />}
      <div
        ref={ref}
        className="mermaid"
        dangerouslySetInnerHTML={{ __html: svg }}
        style={{ display: svg ? 'block' : 'none' }}
      />
    </div>
  );
}

export default Mermaid; 
