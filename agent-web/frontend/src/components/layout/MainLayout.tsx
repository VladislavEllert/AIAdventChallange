import { useEffect } from 'react'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'
import NicknameModal from './NicknameModal'
import ChatArea from '../chat/ChatArea'
import ChatInput from '../chat/ChatInput'
import RightPanel from '../panels/RightPanel'
import { useAppStore } from '../../stores/useAppStore'
import { useChatStore } from '../../stores/useChatStore'
import { useIsMobile } from '../../hooks/useIsMobile'

export default function MainLayout() {
  const isMobile = useIsMobile()
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)
  const rightPanelOpen = useAppStore((s) => s.rightPanelOpen)
  const toggleRightPanel = useAppStore((s) => s.toggleRightPanel)
  const activeAgentPersona = useAppStore((s) => s.activeAgentPersona)
  const rightPanelTab = useAppStore((s) => s.rightPanelTab)
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab)
  const ragEnabled = useAppStore((s) => s.ragEnabled)
  const setRagEnabled = useAppStore((s) => s.setRagEnabled)
  const mcpEnabled = useAppStore((s) => s.mcpEnabled)
  const setMcpEnabled = useAppStore((s) => s.setMcpEnabled)
  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const violation = useChatStore((s) => s.violation)
  const clearViolation = useChatStore((s) => s.clearViolation)

  // Auto-dismiss violation after 5s
  useEffect(() => {
    if (!violation) return
    const t = setTimeout(clearViolation, 5000)
    return () => clearTimeout(t)
  }, [violation, clearViolation])

  // Alt+P keyboard shortcut for right panel
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && e.key === 'p') { e.preventDefault(); toggleRightPanel() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggleRightPanel])

  // Sidebar defaults open (desktop preference, persisted) — on a phone that
  // would cover the whole screen on first load. Auto-close once on mobile.
  useEffect(() => {
    if (isMobile) setSidebarOpen(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', background: 'var(--bg-gradient)' }}>
      <NicknameModal />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Sidebar */}
        <Sidebar />

        {/* Chat column */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', minWidth: 0 }}>

          {/* Top bar */}
          <div className="glass" style={{
            height: 52, display: 'flex', alignItems: 'center', gap: 10,
            padding: '0 16px', flexShrink: 0, borderBottom: '1px solid var(--border)',
          }}>
            {!sidebarOpen && (
              <button onClick={toggleSidebar} title="Открыть боковую панель"
                style={{
                  width: isMobile ? 44 : 32, height: isMobile ? 44 : 32, borderRadius: 8,
                  border: '1px solid var(--border)', background: 'transparent',
                  color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 15,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>☰</button>
            )}

            {!isMobile && (
              <span style={{ flex: 1, fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)' }}>
                {activeAgentPersona
                  ? <span style={{ color: 'var(--accent)', fontSize: 13 }}>✦ Custom agent</span>
                  : 'Чат'
                }
              </span>
            )}
            {isMobile && <span style={{ flex: 1 }} />}

            {/* RAG toggle */}
            <button
              onClick={() => setRagEnabled(!ragEnabled)}
              title={ragEnabled ? 'RAG включён (GitLab Handbook)' : 'RAG выключен'}
              style={{
                height: isMobile ? 40 : 28, minWidth: isMobile ? 44 : undefined,
                padding: '0 10px', borderRadius: 8,
                border: `1px solid ${ragEnabled ? 'var(--accent)' : 'var(--border)'}`,
                background: ragEnabled ? 'var(--accent-bg)' : 'transparent',
                color: ragEnabled ? 'var(--accent)' : 'var(--text-tertiary)',
                cursor: 'pointer', fontSize: 12, fontWeight: 600, letterSpacing: '0.02em',
                transition: 'all 0.15s', flexShrink: 0,
              }}
            >
              {isMobile ? (ragEnabled ? '◈' : '◇') : (ragEnabled ? '◈ RAG' : '◇ RAG')}
            </button>

            {/* MCP toggle */}
            <button
              onClick={() => setMcpEnabled(!mcpEnabled)}
              title={mcpEnabled ? 'MCP включён (инструменты)' : 'MCP выключен'}
              style={{
                height: isMobile ? 40 : 28, minWidth: isMobile ? 44 : undefined,
                padding: '0 10px', borderRadius: 8,
                border: `1px solid ${mcpEnabled ? '#f59e0b' : 'var(--border)'}`,
                background: mcpEnabled ? 'rgba(245,158,11,0.12)' : 'transparent',
                color: mcpEnabled ? '#f59e0b' : 'var(--text-tertiary)',
                cursor: 'pointer', fontSize: 12, fontWeight: 600, letterSpacing: '0.02em',
                transition: 'all 0.15s', flexShrink: 0,
              }}
            >
              {isMobile ? (mcpEnabled ? '⚡' : '○') : (mcpEnabled ? '⚡ MCP' : '○ MCP')}
            </button>

            {/* Right panel toggle buttons — on mobile, one button opens the panel (it has its own tab bar) */}
            <div style={{ display: 'flex', gap: 4 }}>
              {(isMobile
                ? [{ icon: '☰', title: 'Панели', tab: rightPanelTab }]
                : [
                    { icon: '🧠', title: 'Память', tab: 'memory' as const },
                    { icon: '⚙️', title: 'Задача FSM', tab: 'task' as const },
                    { icon: '🛡', title: 'Инварианты', tab: 'invariants' as const },
                    { icon: '👤', title: 'Профиль', tab: 'profiles' as const },
                    { icon: '🎛', title: 'Настройки', tab: 'settings' as const },
                  ]
              ).map(({ icon, title, tab }) => {
                const isActive = rightPanelOpen && rightPanelTab === tab
                return (
                  <button key={tab}
                    onClick={() => {
                      if (rightPanelOpen && rightPanelTab === tab) {
                        toggleRightPanel()
                      } else {
                        setRightPanelTab(tab)
                        if (!rightPanelOpen) toggleRightPanel()
                      }
                    }}
                    title={title}
                    style={{
                      width: isMobile ? 44 : 32, height: isMobile ? 44 : 32, borderRadius: 8, border: 'none',
                      background: isActive ? 'var(--accent-bg)' : 'transparent',
                      color: isActive ? 'var(--accent)' : 'var(--text-tertiary)',
                      cursor: 'pointer', fontSize: 16,
                    }}>{icon}</button>
                )
              })}
            </div>
          </div>

          {/* Messages */}
          <ChatArea />

          {/* Violation alert */}
          {violation && (
            <div style={{
              margin: '0 16px 8px', padding: '10px 16px', borderRadius: 12,
              background: 'var(--red-bg)', border: '1px solid color-mix(in srgb, var(--red) 40%, transparent)',
              color: 'var(--red)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span>⚠</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>Нарушение инварианта</div>
                {violation.desc && <div style={{ fontSize: 12, opacity: 0.8 }}>{violation.desc}</div>}
              </div>
              <button onClick={clearViolation}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 18 }}>×</button>
            </div>
          )}

          {/* Input — hidden until a session exists, nothing to send to */}
          {activeSessionId && <ChatInput />}
        </div>

        {/* Right panel */}
        <RightPanel />
      </div>

      <StatusBar />
    </div>
  )
}
