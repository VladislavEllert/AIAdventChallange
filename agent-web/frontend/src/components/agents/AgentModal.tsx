import { useState, useEffect } from 'react'
import { createAgent, updateAgent, type AgentOut } from '../../api/agents'

interface Props {
  agent?: AgentOut | null
  onClose: () => void
  onSaved: (a: AgentOut) => void
}

const EMOJI_PICKS = ['🤖', '🧠', '🎓', '👨‍💻', '🦊', '🐉', '⚡', '🎯', '🔬', '📚', '🌟', '💡']

export default function AgentModal({ agent, onClose, onSaved }: Props) {
  const [name, setName] = useState(agent?.name ?? '')
  const [emoji, setEmoji] = useState(agent?.emoji ?? '🤖')
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  const save = async () => {
    if (!name.trim()) { setError('Введи имя агента'); return }
    setSaving(true)
    setError('')
    try {
      const result = agent
        ? await updateAgent(agent.id, { name, emoji, system_prompt: prompt })
        : await createAgent({ name, emoji, system_prompt: prompt })
      onSaved(result)
    } catch (e) {
      setError('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backdropFilter: 'blur(4px)',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="glass-strong"
        style={{
          width: 480, maxWidth: '90vw', borderRadius: 20,
          padding: 28, display: 'flex', flexDirection: 'column', gap: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: 17, fontWeight: 600, color: 'var(--text-primary)' }}>
            {agent ? 'Редактировать агента' : 'Новый агент'}
          </h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', fontSize: 20 }}
          >×</button>
        </div>

        {/* Emoji picker */}
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, display: 'block' }}>Аватар</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {EMOJI_PICKS.map((e) => (
              <button
                key={e}
                onClick={() => setEmoji(e)}
                style={{
                  width: 40, height: 40, borderRadius: 10, fontSize: 20,
                  border: emoji === e ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: emoji === e ? 'var(--accent-bg)' : 'var(--bg-surface)',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >{e}</button>
            ))}
            <input
              value={emoji}
              onChange={(e) => setEmoji(e.target.value)}
              style={{
                width: 40, height: 40, borderRadius: 10, fontSize: 20, textAlign: 'center',
                border: '1px solid var(--border)', background: 'var(--bg-input)',
                color: 'var(--text-primary)', outline: 'none',
              }}
              placeholder="?"
            />
          </div>
        </div>

        {/* Name */}
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Имя агента</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Например: Ментор по Python"
            style={{
              width: '100%', padding: '10px 14px', borderRadius: 10,
              border: '1px solid var(--border)', background: 'var(--bg-input)',
              color: 'var(--text-primary)', fontSize: 14, outline: 'none',
              fontFamily: 'inherit',
            }}
          />
        </div>

        {/* System prompt */}
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>
            Системный промпт
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ты — помощник по Python. Отвечай кратко, с примерами кода…"
            rows={5}
            style={{
              width: '100%', padding: '10px 14px', borderRadius: 10,
              border: '1px solid var(--border)', background: 'var(--bg-input)',
              color: 'var(--text-primary)', fontSize: 13, outline: 'none',
              resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5,
            }}
          />
        </div>

        {error && (
          <div style={{ fontSize: 13, color: 'var(--red)', padding: '8px 12px', background: 'var(--red-bg)', borderRadius: 8 }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '9px 20px', borderRadius: 10, fontSize: 14,
              border: '1px solid var(--border)', background: 'transparent',
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}
          >Отмена</button>
          <button
            onClick={save}
            disabled={saving}
            style={{
              padding: '9px 20px', borderRadius: 10, fontSize: 14, fontWeight: 500,
              border: 'none', background: 'var(--accent)',
              color: '#fff', cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >{saving ? 'Сохраняю…' : 'Сохранить'}</button>
        </div>
      </div>
    </div>
  )
}
