import { useAppStore } from '../../stores/useAppStore'
import { useChatStore } from '../../stores/useChatStore'

export default function StatusBar() {
  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const activeModel = useAppStore((s) => s.activeModel)
  const activeProfileName = useAppStore((s) => s.activeProfileName)
  const { sessionCost, messages } = useChatStore()
  const msgCount = messages.filter((m) => m.role !== 'system').length

  return (
    <div className="glass" style={{
      height: 32, display: 'flex', alignItems: 'center',
      padding: '0 16px', gap: 12, flexShrink: 0,
      borderTop: '1px solid var(--border)',
      fontSize: 11, color: 'var(--text-tertiary)',
      userSelect: 'none',
    }}>
      <span>
        {activeSessionId
          ? <span>📍 <span style={{ color: 'var(--text-secondary)' }}>{activeSessionId.slice(0, 8)}</span></span>
          : '— нет сессии'
        }
      </span>
      <span style={{ color: 'var(--border)' }}>│</span>
      <span>{msgCount} сообщ.</span>
      <span style={{ color: 'var(--border)' }}>│</span>
      <span style={{ color: 'var(--text-secondary)' }}>{activeModel.split('/').pop()}</span>
      {activeProfileName && (
        <>
          <span style={{ color: 'var(--border)' }}>│</span>
          <span style={{ color: 'var(--green, #22c55e)' }}>👤 {activeProfileName}</span>
        </>
      )}
      <span style={{ color: 'var(--border)' }}>│</span>
      <span>₽ {sessionCost.toFixed(4)}</span>
    </div>
  )
}
