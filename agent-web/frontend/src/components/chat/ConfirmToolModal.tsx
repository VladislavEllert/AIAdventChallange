import { useEffect } from 'react'
import type { ChatConfirmRequest } from '../../api/chat'

interface Props {
  request: ChatConfirmRequest
  onAllow: () => void
  onDeny: () => void
}

/**
 * Day 34: human-in-the-loop confirmation for DANGEROUS tool calls
 * (write_file/delete_file). No diff preview by design (plan explicitly calls
 * that gold-plating for this phase) — just tool name, arguments, reason.
 *
 * Day 35 fix: the raw-JSON argument block had no height cap. `write_file`'s
 * `content` argument can be an entire file (day 35's /ritual writes a full
 * README.md, several KB) — with no cap the modal card grew unbounded and
 * pushed the Allow/Deny buttons off-screen with no way to scroll to them,
 * found live via ritual-command.spec.ts (Playwright's "element outside of
 * viewport" click failure — a real user would hit the exact same dead end,
 * this wasn't a test-only artifact). Fix: cap the arguments block's height
 * and let IT scroll, so the button row always stays in the fixed-size card.
 */
export default function ConfirmToolModal({ request, onAllow, onDeny }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDeny()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onDeny])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1100,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
    }}>
      <div className="glass-strong" style={{
        borderRadius: 16, padding: 28, width: 460, maxWidth: '90vw',
        maxHeight: '85vh', display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>⚠️</span> Подтверди опасную операцию
        </div>

        <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
          {request.reason}
        </div>

        <div style={{
          padding: '10px 14px', borderRadius: 10, background: 'var(--bg-surface)',
          border: '1px solid var(--border)', fontFamily: 'monospace', fontSize: 13,
          maxHeight: '40vh', overflowY: 'auto',
        }}>
          <div style={{ color: 'var(--accent)', fontWeight: 600, marginBottom: 6 }}>
            {request.tool_name}
          </div>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>
            {JSON.stringify(request.arguments, null, 2)}
          </pre>
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
          <button
            onClick={onDeny}
            autoFocus
            style={{
              padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border)',
              background: 'transparent', color: 'var(--text-primary)',
              cursor: 'pointer', fontSize: 14, fontWeight: 500,
            }}
          >
            Отклонить (Esc)
          </button>
          <button
            onClick={onAllow}
            style={{
              padding: '10px 16px', borderRadius: 10, border: 'none',
              background: 'var(--red)', color: '#fff',
              cursor: 'pointer', fontSize: 14, fontWeight: 500,
            }}
          >
            Разрешить
          </button>
        </div>
      </div>
    </div>
  )
}
