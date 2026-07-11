import { useState } from 'react'
import { useAppStore } from '../../stores/useAppStore'

/**
 * First-run nickname prompt — light per-user session isolation without auth.
 * Sessions this browser creates are tagged with this nickname; the sidebar
 * only lists sessions matching it (+ legacy ownerless ones). Not a security
 * boundary — anyone can type any name — just keeps chats from mixing
 * together when multiple trusted people share the server.
 */
export default function NicknameModal() {
  const userName = useAppStore((s) => s.userName)
  const setUserName = useAppStore((s) => s.setUserName)
  const [draft, setDraft] = useState('')

  if (userName) return null

  const submit = () => {
    const trimmed = draft.trim()
    if (trimmed) setUserName(trimmed)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
    }}>
      <div className="glass-strong" style={{
        borderRadius: 16, padding: 28, width: 320, maxWidth: '90vw',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--text-primary)' }}>
          Как тебя зовут?
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
          Чтобы твои чаты не смешивались с чужими. Без пароля — просто имя для отличия
          (можно сменить позже в настройках).
        </div>
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          placeholder="Например: Влад"
          style={{
            padding: '10px 14px', borderRadius: 10, border: '1px solid var(--border)',
            background: 'var(--bg-surface)', color: 'var(--text-primary)', fontSize: 14,
            outline: 'none',
          }}
        />
        <button
          onClick={submit}
          disabled={!draft.trim()}
          style={{
            padding: '10px 14px', borderRadius: 10, border: 'none',
            background: draft.trim() ? 'var(--accent)' : 'var(--bg-surface)',
            color: draft.trim() ? '#fff' : 'var(--text-tertiary)',
            cursor: draft.trim() ? 'pointer' : 'not-allowed',
            fontSize: 14, fontWeight: 500,
          }}
        >
          Продолжить
        </button>
      </div>
    </div>
  )
}
