import { useAppStore } from '../../stores/useAppStore'
import MemoryPanel from './MemoryPanel'
import InvariantsPanel from './InvariantsPanel'
import ProfilesPanel from './ProfilesPanel'
import TaskPanel from './TaskPanel'

type Tab = 'memory' | 'task' | 'invariants' | 'profiles'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'memory', label: 'Память', icon: '🧠' },
  { id: 'task', label: 'Задача', icon: '⚙️' },
  { id: 'invariants', label: 'Инварианты', icon: '🛡' },
  { id: 'profiles', label: 'Профиль', icon: '👤' },
]

export default function RightPanel() {
  const rightPanelOpen = useAppStore((s) => s.rightPanelOpen)
  const toggleRightPanel = useAppStore((s) => s.toggleRightPanel)
  const rightPanelTab = useAppStore((s) => s.rightPanelTab)
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab)

  if (!rightPanelOpen) return null

  return (
    <div
      className="glass"
      style={{
        width: 320,
        flexShrink: 0,
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{
        height: 52, display: 'flex', alignItems: 'center',
        padding: '0 12px', borderBottom: '1px solid var(--border)',
        flexShrink: 0, gap: 4,
      }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setRightPanelTab(t.id as any)}
            title={t.label}
            style={{
              flex: 1, padding: '5px 0', borderRadius: 8, border: 'none',
              background: rightPanelTab === t.id ? 'var(--accent-bg)' : 'transparent',
              color: rightPanelTab === t.id ? 'var(--accent)' : 'var(--text-tertiary)',
              cursor: 'pointer', fontSize: 15, transition: 'all 0.15s',
            }}
          >
            {t.icon}
          </button>
        ))}
        <button
          onClick={toggleRightPanel}
          style={{
            width: 28, height: 28, borderRadius: 8, border: 'none',
            background: 'transparent', color: 'var(--text-tertiary)',
            cursor: 'pointer', fontSize: 16, marginLeft: 4,
          }}
        >×</button>
      </div>

      {/* Tab label */}
      <div style={{ padding: '6px 16px 0', fontSize: 11, color: 'var(--text-tertiary)' }}>
        {TABS.find((t) => t.id === rightPanelTab)?.label}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {rightPanelTab === 'memory' && <MemoryPanel />}
        {rightPanelTab === 'task' && <TaskPanel />}
        {rightPanelTab === 'invariants' && <InvariantsPanel />}
        {rightPanelTab === 'profiles' && <ProfilesPanel />}
      </div>
    </div>
  )
}
