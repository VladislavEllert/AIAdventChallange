import ChatList from '../sidebar/ChatList'
import { useAppStore } from '../../stores/useAppStore'
import { useIsMobile } from '../../hooks/useIsMobile'

export default function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const isMobile = useIsMobile()

  const content = (
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
            width: isMobile ? 44 : 28, height: isMobile ? 44 : 28, borderRadius: 8,
            border: 'none', background: 'transparent',
            color: 'var(--text-tertiary)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, transition: 'color 0.15s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
        >{isMobile ? '×' : '←'}</button>
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ChatList />
      </div>
    </>
  )

  if (isMobile) {
    if (!sidebarOpen) return null
    return (
      <>
        {/* Backdrop */}
        <div
          onClick={toggleSidebar}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 40 }}
        />
        {/* Drawer */}
        <div
          className="glass-strong"
          style={{
            position: 'fixed', top: 0, left: 0, bottom: 0, width: '82vw', maxWidth: 320,
            zIndex: 41, display: 'flex', flexDirection: 'column',
            borderRight: '1px solid var(--border)',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          {content}
        </div>
      </>
    )
  }

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
      {sidebarOpen && content}
    </div>
  )
}
