<!-- source: agent-web/frontend/src/components/panels/MemoryPanel.tsx | title: MemoryPanel.tsx -->

import { useEffect, useState } from 'react'
import { getMemory, type MemoryState } from '../../api/memory'
import { updateSettings } from '../../api/settings'
import { useAppStore } from '../../stores/useAppStore'

export default function MemoryPanel() {
  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const [mem, setMem] = useState<MemoryState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editN, setEditN] = useState(false)
  const [nLimit, setNLimit] = useState(16)
  const [nKeep, setNKeep] = useState(8)
  const [savingN, setSavingN] = useState(false)

  const load = async () => {
    if (!activeSessionId) return
    setLoading(true)
    setError('')
    try {
      const m = await getMemory(activeSessionId)
      setMem(m)
      setNLimit(m.short_term_limit)
      setNKeep(m.keep_recent)
    } catch {
      setError('Нет данных (начни чат)')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [activeSessionId])

  const saveN = async () => {
    setSavingN(true)
    try {
      await updateSettings({ short_term_limit: nLimit, keep_recent: nKeep })
      setSavingN(false)
      setEditN(false)
      load()
    } catch { setSavingN(false) }
  }

  const pct = mem ? Math.round((mem.short_term_count / mem.short_term_limit) * 100) : 0

  if (!activeSessionId) {
    return (
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ПАМЯТЬ АГЕНТА</span>
        </div>
        <div style={{
          textAlign: 'center', padding: '40px 20px',
          color: 'var(--text-tertiary)', fontSize: 13, lineHeight: 1.6,
        }}>
          🧠<br />
          <div style={{ marginTop: 8 }}>Выбери сессию<br />чтобы увидеть память</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ПАМЯТЬ АГЕНТА</span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            onClick={() => setEditN(!editN)}
            title="Настройки сжатия"
            style={{
              fontSize: 11, color: editN ? 'var(--accent)' : 'var(--text-secondary)',
              background: editN ? 'var(--accent-bg)' : 'var(--bg-surface)',
              border: '1px solid var(--border)', borderRadius: 6,
              cursor: 'pointer', padding: '3px 8px',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >⚙ Сжатие</button>
          <button onClick={load} disabled={loading}
            style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>
            {loading ? '…' : '↻ Обновить'}
          </button>
        </div>
      </div>

      {/* N settings */}
      {editN && (
        <div className="glass" style={{ borderRadius: 12, padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Настройки сжатия</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>Сжимать при N сообщ.</span>
            <input
              type="number" min={4} max={64} value={nLimit}
              onChange={(e) => setNLimit(Number(e.target.value))}
              style={{
                width: 60, padding: '4px 8px', borderRadius: 6,
                border: '1px solid var(--border)', background: 'var(--bg-input)',
                color: 'var(--text-primary)', fontSize: 12, textAlign: 'center', outline: 'none',
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>Оставлять K последних</span>
            <input
              type="number" min={2} max={32} value={nKeep}
              onChange={(e) => setNKeep(Number(e.target.value))}
              style={{
                width: 60, padding: '4px 8px', borderRadius: 6,
                border: '1px solid var(--border)', background: 'var(--bg-input)',
                color: 'var(--text-primary)', fontSize: 12, textAlign: 'center', outline: 'none',
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={saveN} disabled={savingN}
              style={{
                flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
                background: 'var(--accent)', color: '#fff', fontSize: 12,
                fontWeight: 600, cursor: 'pointer',
              }}>
              {savingN ? '…' : '✓ Сохранить'}
            </button>
            <button onClick={() => setEditN(false)}
              style={{
                padding: '6px 12px', borderRadius: 8,
                border: '1px solid var(--border)', background: 'none',
                color: 'var(--text-tertiary)', fontSize: 12, cursor: 'pointer',
              }}>Отмена</button>
          </div>
        </div>
      )}

      {error && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center', padding: '20px 0' }}>{error}</div>}

      {mem && (
        <>
          {/* Short-term */}
          <div className="glass" style={{ borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 8, textTransform: 'uppercase' }}>
              Краткосрочная память
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 3, transition: 'width 0.3s',
                  background: pct > 75 ? 'var(--red)' : pct > 50 ? '#f59e0b' : 'var(--accent)',
                  width: `${Math.min(pct, 100)}%`,
                }} />
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)', flexShrink: 0 }}>
                {mem.short_term_count}/{mem.short_term_limit}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
              Сжатие при {mem.short_term_limit} сообщ. · оставляем {mem.keep_recent} последних
            </div>
            {mem.summary && (
              <div style={{ marginTop: 8, padding: '8px 10px', background: 'var(--bg-base)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 4 }}>СЖАТОЕ РЕЗЮМЕ</div>
                {mem.summary.slice(0, 300)}{mem.summary.length > 300 ? '…' : ''}
              </div>
            )}
          </div>

          {/* Working memory */}
          <div className="glass" style={{ borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 8, textTransform: 'uppercase' }}>
              Рабочая память
            </div>
            {Object.keys(mem.working).length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Пусто</div>
            ) : (
              Object.entries(mem.working).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{k}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {typeof v === 'string' ? v : JSON.stringify(v)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Recent messages */}
          {mem.messages.length > 0 && (
            <div className="glass" style={{ borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 8, textTransform: 'uppercase' }}>
                Последние сообщения
              </div>
              {mem.messages.map((msg, i) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  <span style={{
                    fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                    color: msg.role === 'user' ? 'var(--accent)' : 'var(--green)',
                    marginRight: 6,
                  }}>{msg.role}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {msg.content.slice(0, 80)}{msg.content.length > 80 ? '…' : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
