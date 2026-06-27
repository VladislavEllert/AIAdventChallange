import { useEffect, useState } from 'react'
import { listProfiles, getProfile, updateProfile } from '../../api/profiles'
import { extractProfile } from '../../api/memory'
import { useAppStore } from '../../stores/useAppStore'

export default function ProfilesPanel() {
  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const activeProfileName = useAppStore((s) => s.activeProfileName)
  const setActiveProfileName = useAppStore((s) => s.setActiveProfileName)
  const [names, setNames] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(activeProfileName)
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [saved, setSaved] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [extractMsg, setExtractMsg] = useState('')

  useEffect(() => {
    listProfiles().then(setNames).catch(() => setNames([]))
  }, [])

  const selectProfile = async (name: string) => {
    const newName = selected === name ? null : name   // toggle off if already selected
    setSelected(newName)
    setActiveProfileName(newName)
    setEditing(false)
    setSaved(false)
    setExtractMsg('')
    if (!newName) return
    try {
      const p = await getProfile(name)
      setContent(p.content)
    } catch {
      setContent('Ошибка загрузки')
    }
  }

  const save = async () => {
    if (!selected) return
    try {
      await updateProfile(selected, content)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      setEditing(false)
    } catch {}
  }

  const extract = async () => {
    if (!selected || !activeSessionId) return
    setExtracting(true)
    setExtractMsg('')
    try {
      const res = await extractProfile(activeSessionId, selected)
      if (res.updated) {
        const layers = Object.entries(res.layers)
          .filter(([, v]) => v.length > 0)
          .map(([k]) => k)
          .join(', ')
        setExtractMsg(`✓ Обновлено: ${layers}`)
        // Reload profile content
        const p = await getProfile(selected)
        setContent(p.content)
      } else {
        setExtractMsg('Нет новых фактов')
      }
      setTimeout(() => setExtractMsg(''), 4000)
    } catch (e) {
      setExtractMsg('Ошибка извлечения')
    } finally {
      setExtracting(false)
    }
  }

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ПРОФИЛИ ПОЛЬЗОВАТЕЛЯ</div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
        Долгосрочная память агента о пользователе. Нажми на профиль → он инжектируется в каждый запрос.
      </div>
      {activeProfileName && (
        <div style={{
          padding: '6px 10px', borderRadius: 8, fontSize: 11,
          background: 'var(--green-bg, rgba(34,197,94,0.1))',
          color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)',
        }}>
          ✓ Активен: <strong>{activeProfileName}</strong> — инжектируется в промпт
        </div>
      )}

      {/* Profile list */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {names.map((n) => (
          <button key={n} onClick={() => selectProfile(n)}
            style={{
              padding: '5px 12px', borderRadius: 20, fontSize: 12,
              border: '1px solid var(--border)',
              background: selected === n ? 'var(--accent-bg)' : 'var(--bg-surface)',
              color: selected === n ? 'var(--accent)' : 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >{n}</button>
        ))}
        {names.length === 0 && (
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Нет профилей. Создай через CLI: /profile create</div>
        )}
      </div>

      {/* Profile content */}
      {selected && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{selected}.md</span>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              {/* Extract button — only if session is active */}
              {activeSessionId && !editing && (
                <button
                  onClick={extract}
                  disabled={extracting}
                  title="Извлечь факты из текущего разговора и добавить в профиль"
                  style={{
                    fontSize: 11, background: 'var(--accent-bg)', border: 'none',
                    borderRadius: 6, padding: '3px 10px',
                    color: 'var(--accent)', cursor: 'pointer', opacity: extracting ? 0.6 : 1,
                  }}>
                  {extracting ? '…' : '🔍 Извлечь из чата'}
                </button>
              )}
              {editing ? (
                <>
                  <button onClick={() => setEditing(false)}
                    style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)' }}>
                    Отмена
                  </button>
                  <button onClick={save}
                    style={{ fontSize: 11, background: 'var(--accent)', border: 'none', borderRadius: 6, padding: '3px 10px', color: '#fff', cursor: 'pointer' }}>
                    {saved ? '✓ Сохранено' : 'Сохранить'}
                  </button>
                </>
              ) : (
                <button onClick={() => setEditing(true)}
                  style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)' }}>
                  ✏ Редактировать
                </button>
              )}
            </div>
          </div>

          {extractMsg && (
            <div style={{
              padding: '6px 10px', marginBottom: 6, borderRadius: 8,
              background: extractMsg.startsWith('✓') ? 'var(--green-bg, rgba(34,197,94,0.1))' : 'var(--bg-surface)',
              color: extractMsg.startsWith('✓') ? 'var(--green)' : 'var(--text-tertiary)',
              fontSize: 11,
            }}>{extractMsg}</div>
          )}

          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            readOnly={!editing}
            rows={16}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 10,
              border: `1px solid ${editing ? 'var(--accent)' : 'var(--border)'}`,
              background: editing ? 'var(--bg-input)' : 'var(--bg-surface)',
              color: 'var(--text-primary)', fontSize: 12, resize: 'vertical',
              fontFamily: 'ui-monospace, monospace', lineHeight: 1.5, outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      )}

      {!activeSessionId && selected && (
        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          Открой чат для автоматического извлечения фактов из разговора
        </div>
      )}
    </div>
  )
}
