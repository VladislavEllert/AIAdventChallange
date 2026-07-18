<!-- source: agent-web/frontend/src/components/panels/InvariantsPanel.tsx | title: InvariantsPanel.tsx -->

import { useEffect, useState } from 'react'
import { listInvariants, addInvariant, removeInvariant } from '../../api/invariants'

export default function InvariantsPanel() {
  const [items, setItems] = useState<string[]>([])
  const [newText, setNewText] = useState('')
  const [loading, setLoading] = useState(false)

  const load = async () => {
    try { setItems(await listInvariants()) } catch { setItems([]) }
  }

  useEffect(() => { load() }, [])

  const add = async () => {
    if (!newText.trim()) return
    setLoading(true)
    try {
      setItems(await addInvariant(newText.trim()))
      setNewText('')
    } finally { setLoading(false) }
  }

  const remove = async (index: number) => {
    try { setItems(await removeInvariant(index)) } catch { load() }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); add() }
  }

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ИНВАРИАНТЫ</div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
        Правила для проверки ответов агента. Нарушение → ответ откатывается.
      </div>

      {/* Add new */}
      <div style={{ display: 'flex', gap: 6 }}>
        <textarea
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Добавить правило…"
          rows={2}
          style={{
            flex: 1, padding: '8px 10px', borderRadius: 8,
            border: '1px solid var(--border)', background: 'var(--bg-input)',
            color: 'var(--text-primary)', fontSize: 12, resize: 'none',
            fontFamily: 'inherit', outline: 'none', lineHeight: 1.4,
          }}
        />
        <button onClick={add} disabled={loading || !newText.trim()}
          style={{
            padding: '0 12px', borderRadius: 8, border: 'none',
            background: 'var(--accent)', color: '#fff',
            cursor: loading || !newText.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !newText.trim() ? 0.5 : 1,
            fontSize: 18, flexShrink: 0,
          }}>+</button>
      </div>

      {/* List */}
      {items.length === 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center', padding: '16px 0' }}>
          Нет инвариантов
        </div>
      )}
      {items.map((item, i) => (
        <div key={i} className="glass" style={{
          borderRadius: 10, padding: '10px 12px',
          display: 'flex', gap: 8, alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 700, flexShrink: 0, marginTop: 1 }}>
            {i + 1}.
          </span>
          <span style={{ flex: 1, fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>
            {item}
          </span>
          <button onClick={() => remove(i)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-tertiary)', fontSize: 16, flexShrink: 0,
              padding: 0, lineHeight: 1,
            }}
            title="Удалить"
          >×</button>
        </div>
      ))}
    </div>
  )
}
