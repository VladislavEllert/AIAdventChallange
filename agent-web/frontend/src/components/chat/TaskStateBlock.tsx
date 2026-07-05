import { useState } from 'react'
import type { TaskState } from '../../stores/useChatStore'

interface Props {
  taskState?: TaskState
}

export default function TaskStateBlock({ taskState }: Props) {
  const [open, setOpen] = useState(false)

  if (!taskState?.goal) return null

  const hasDetails =
    (taskState.clarified_facts?.length ?? 0) > 0 ||
    (taskState.constraints?.length ?? 0) > 0

  return (
    <div style={{ marginTop: 8 }}>
      <div
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          cursor: 'pointer', fontSize: 11, color: 'var(--text-tertiary)',
          padding: '3px 8px', borderRadius: 6,
          border: '1px solid var(--border)',
          background: 'var(--bg-surface)',
          userSelect: 'none',
        }}
      >
        <span>{open ? '▾' : '▸'}</span>
        <span>🎯 Task memory</span>
        <span style={{ color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {taskState.goal}
        </span>
      </div>

      {open && (
        <div style={{
          marginTop: 4, padding: '8px 10px',
          border: '1px solid var(--border)',
          borderRadius: 8, background: 'var(--bg-surface)',
          fontSize: 12,
        }}>
          <div style={{ color: 'var(--text-primary)', marginBottom: hasDetails ? 6 : 0 }}>
            <span style={{ color: 'var(--text-tertiary)' }}>Goal: </span>
            {taskState.goal}
          </div>
          {taskState.clarified_facts?.length > 0 && (
            <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
              <span style={{ color: 'var(--text-tertiary)' }}>Clarified: </span>
              {taskState.clarified_facts.join(' · ')}
            </div>
          )}
          {taskState.constraints?.length > 0 && (
            <div style={{ color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--text-tertiary)' }}>Constraints: </span>
              {taskState.constraints.join(' · ')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
