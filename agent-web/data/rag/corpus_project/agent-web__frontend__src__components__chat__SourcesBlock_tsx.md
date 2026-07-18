<!-- source: agent-web/frontend/src/components/chat/SourcesBlock.tsx | title: SourcesBlock.tsx -->

import { useState } from 'react'
import type { Source, RagMeta } from '../../stores/useChatStore'

interface Props {
  sources: Source[]
  ragMeta?: RagMeta
}

export default function SourcesBlock({ sources, ragMeta }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  const toggle = (i: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })
  }

  if (!sources || sources.length === 0) return null

  return (
    <div style={{ marginTop: 12 }}>
      {/* RAG filter meta */}
      {ragMeta && (
        <div style={{
          fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 8,
          display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center',
        }}>
          <span>📚 RAG</span>
          <span>raw={ragMeta.top_k_raw} → kept={ragMeta.top_k_kept} → used={ragMeta.top_k_final}</span>
          <span>best={ragMeta.best_score.toFixed(3)}</span>
          {ragMeta.rewritten_query && (
            <span title={ragMeta.rewritten_query} style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              ✏️ {ragMeta.rewritten_query}
            </span>
          )}
        </div>
      )}

      {/* Sources list */}
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, fontWeight: 500 }}>
        Sources ({sources.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {sources.map((s, i) => (
          <div key={i} style={{
            borderRadius: 8, border: '1px solid var(--border)',
            background: 'var(--bg-surface)', overflow: 'hidden',
          }}>
            <div
              onClick={() => toggle(i)}
              style={{
                padding: '6px 10px', cursor: 'pointer', display: 'flex',
                alignItems: 'center', gap: 8,
              }}
            >
              <span style={{ fontSize: 10, color: 'var(--text-tertiary)', flexShrink: 0 }}>
                {expanded.has(i) ? '▾' : '▸'}
              </span>
              <a
                href={s.source}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                style={{
                  fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                }}
              >
                {s.section || s.source}
              </a>
              <span style={{
                fontSize: 10, color: 'var(--text-tertiary)', flexShrink: 0,
                background: 'var(--bg-surface-hover)', padding: '1px 5px', borderRadius: 4,
              }}>
                {s.score.toFixed(3)}
              </span>
            </div>

            {expanded.has(i) && (
              <div style={{
                padding: '0 10px 8px 24px',
                borderTop: '1px solid var(--border)',
                paddingTop: 6,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>
                  {s.chunk_id}
                </div>
                <blockquote style={{
                  margin: 0, padding: '6px 10px',
                  borderLeft: '2px solid var(--accent)',
                  background: 'var(--accent-bg)',
                  borderRadius: '0 6px 6px 0',
                  fontSize: 12, color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                }}>
                  {s.quote}…
                </blockquote>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
