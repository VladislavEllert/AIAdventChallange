import ChatList from '../sidebar/ChatList'
import { useAppStore } from '../../stores/useAppStore'

export default function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)

  return (
    <div
      className="glass"
      style={{
        width: sidebarOpen ? 260 : 0,
        flexShrink: 0,
        overflow: 'hidden',
        transition: 'width 0.2s ease',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {sidebarOpen && (
        <>
          {/* Header */}
          <div
            style={{
              height: 52, display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', padding: '0 16px',
              borderBottom: '1px solid var(--border)', flexShrink: 0,
            }}
          >
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              ✦ Agent
            </span>
            <button
              onClick={toggleSidebar}
              title="Скрыть сайдбар"
              style={{
                width: 28, height: 28, borderRadius: 8,
                border: 'none', background: 'transparent',
                color: 'var(--text-tertiary)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, transition: 'color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
            >←</button>
          </div>

          <div style={{ flex: 1, overflow: 'hidden' }}>
            <ChatList />
          </div>
        </>
      )}
    </div>
  )
}
