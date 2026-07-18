<!-- source: agent-web/frontend/src/components/sidebar/ChatList.tsx | title: ChatList.tsx -->

import { useEffect, useState } from 'react'
import { useAppStore } from '../../stores/useAppStore'
import { useChatStore } from '../../stores/useChatStore'
import { listSessions, createSession, deleteSession, getSession, type SessionOut } from '../../api/sessions'
import { listAgents, deleteAgent, type AgentOut } from '../../api/agents'
import AgentModal from '../agents/AgentModal'

const DEFAULT_AGENT: AgentOut = {
  id: '__default__',
  name: 'Default',
  emoji: '✦',
  system_prompt: '',
  created_at: 0,
}

interface ConfirmState {
  type: 'session' | 'agent'
  id: string
  name: string
}

export default function ChatList() {
  const [sessions, setSessions] = useState<SessionOut[]>([])
  const [agents, setAgents] = useState<AgentOut[]>([])
  const [agentModal, setAgentModal] = useState<AgentOut | null | false>(false)
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)

  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const setActiveSessionId = useAppStore((s) => s.setActiveSessionId)
  const activeAgentId = useAppStore((s) => s.activeAgentId)
  const setActiveAgent = useAppStore((s) => s.setActiveAgent)
  const userName = useAppStore((s) => s.userName)
  const { setMessages, reset } = useChatStore()

  const loadSessions = async (agentId?: string | null) => {
    try {
      const id = agentId !== undefined ? agentId : activeAgentId
      setSessions(await listSessions(id ?? '__default__', userName))
    } catch (e) { console.error(e) }
  }

  const loadAgents = async () => {
    try { setAgents(await listAgents()) } catch (e) { console.error(e) }
  }

  useEffect(() => {
    loadSessions(activeAgentId ?? '__default__')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeAgentId, userName])

  useEffect(() => { loadAgents() }, [])

  const switchSession = async (id: string) => {
    if (id === activeSessionId) return
    try {
      const detail = await getSession(id)
      setActiveSessionId(id)
      setMessages(detail.messages.map((m, i) => ({
        id: `${id}-${i}`,
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })))
    } catch (e) { console.error(e) }
  }

  const newSession = async () => {
    try {
      const agentId = activeAgentId ?? '__default__'
      const s = await createSession('', agentId, userName)
      await loadSessions(agentId)
      reset()
      setActiveSessionId(s.session_id)
    } catch (e) { console.error(e) }
  }

  const askDelete = (e: React.MouseEvent, type: 'session' | 'agent', id: string, name: string) => {
    e.stopPropagation()
    setConfirm({ type, id, name })
  }

  const confirmDelete = async () => {
    if (!confirm) return
    if (confirm.type === 'session') {
      try {
        await deleteSession(confirm.id)
        await loadSessions()
        if (confirm.id === activeSessionId) { reset(); setActiveSessionId(null) }
      } catch (e) { console.error(e) }
    } else {
      try {
        await deleteAgent(confirm.id)
        await loadAgents()
        if (confirm.id === activeAgentId) {
          setActiveAgent(null, '')
          await loadSessions('__default__')
        }
      } catch (e) { console.error(e) }
    }
    setConfirm(null)
  }

  const selectAgent = (a: AgentOut) => {
    if (a.id === activeAgentId) {
      setActiveAgent(null, '')
    } else {
      setActiveAgent(a.id, a.system_prompt)
    }
    reset()
    setActiveSessionId(null)
  }

  const allAgents = [DEFAULT_AGENT, ...agents]
  const effectiveAgentId = activeAgentId ?? '__default__'

  return (
    <>
      {/* Confirm dialog */}
      {confirm && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
        }}
          onClick={() => setConfirm(null)}
        >
          <div
            className="glass"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 320, padding: 24, borderRadius: 16,
              border: '1px solid var(--border)',
              display: 'flex', flexDirection: 'column', gap: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                Удалить {confirm.type === 'agent' ? 'агента' : 'сессию'}?
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                «{confirm.name}» будет удалён{confirm.type === 'session' ? 'а' : ''} без возможности восстановления.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setConfirm(null)}
                style={{
                  flex: 1, padding: '9px 0', borderRadius: 10,
                  border: '1px solid var(--border)', background: 'transparent',
                  color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer',
                }}
              >Отмена</button>
              <button
                onClick={confirmDelete}
                style={{
                  flex: 1, padding: '9px 0', borderRadius: 10,
                  border: 'none', background: 'var(--red)',
                  color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >Удалить</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>

        {/* New Chat button */}
        <div style={{ padding: '12px 12px 4px' }}>
          <button
            onClick={newSession}
            style={{
              width: '100%', padding: '9px 14px',
              borderRadius: 10, border: '1px solid var(--border)',
              background: 'var(--bg-surface)', color: 'var(--text-primary)',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8,
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-surface)')}
          >
            <span style={{ fontSize: 16 }}>+</span>
            <span>Новый чат</span>
          </button>
        </div>

        {/* Agents section */}
        <div style={{ padding: '16px 12px 4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)' }}>
              Агенты
            </span>
            <button
              onClick={() => setAgentModal(null)}
              title="Создать агента"
              style={{
                width: 24, height: 24, borderRadius: 6, border: 'none',
                background: 'var(--accent-bg)', color: 'var(--accent)',
                cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >+</button>
          </div>

          {allAgents.map((a) => {
            const isActive = a.id === effectiveAgentId
            return (
              <div
                key={a.id}
                onClick={() => selectAgent(a)}
                className="group"
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                  marginBottom: 2,
                  background: isActive ? 'var(--accent-bg)' : 'transparent',
                  border: isActive
                    ? '1px solid color-mix(in srgb, var(--accent) 30%, transparent)'
                    : '1px solid transparent',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface-hover)' }}
                onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
              >
                <span style={{ fontSize: 16, flexShrink: 0 }}>{a.emoji}</span>
                <span style={{
                  flex: 1, fontSize: 13, overflow: 'hidden',
                  textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  color: isActive ? 'var(--accent)' : 'var(--text-primary)',
                }}>{a.name}</span>
                {a.id !== '__default__' && (
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); setAgentModal(a) }}
                      title="Редактировать агента"
                      style={{
                        width: 26, height: 26, borderRadius: 6, border: 'none',
                        background: 'var(--bg-surface)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer', fontSize: 13,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { (e.currentTarget.style.background = 'var(--accent-bg)'); (e.currentTarget.style.color = 'var(--accent)') }}
                      onMouseLeave={(e) => { (e.currentTarget.style.background = 'var(--bg-surface)'); (e.currentTarget.style.color = 'var(--text-secondary)') }}
                    >✏</button>
                    <button
                      onClick={(e) => askDelete(e, 'agent', a.id, a.name)}
                      title="Удалить агента"
                      style={{
                        width: 26, height: 26, borderRadius: 6, border: 'none',
                        background: 'var(--bg-surface)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer', fontSize: 15,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { (e.currentTarget.style.background = 'var(--red-bg, rgba(239,68,68,0.15))'); (e.currentTarget.style.color = 'var(--red)') }}
                      onMouseLeave={(e) => { (e.currentTarget.style.background = 'var(--bg-surface)'); (e.currentTarget.style.color = 'var(--text-secondary)') }}
                    >×</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'var(--border)', margin: '8px 12px' }} />

        {/* Sessions section */}
        <div style={{ padding: '0 12px 4px' }}>
          <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)', display: 'block', marginBottom: 6 }}>
            Сессии
          </span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 12px' }}>
          {sessions.map((s) => {
            const isActive = s.session_id === activeSessionId
            return (
              <div
                key={s.session_id}
                onClick={() => switchSession(s.session_id)}
                className="group"
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                  marginBottom: 2,
                  background: isActive ? 'var(--accent-bg)' : 'transparent',
                  border: isActive
                    ? '1px solid color-mix(in srgb, var(--accent) 30%, transparent)'
                    : '1px solid transparent',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface-hover)' }}
                onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 500,
                    color: isActive ? 'var(--accent)' : 'var(--text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {s.display_name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 1 }}>
                    {s.msg_count} сообщ. · ₽{s.cost_rub.toFixed(4)}
                  </div>
                </div>
                <button
                  onClick={(e) => askDelete(e, 'session', s.session_id, s.display_name)}
                  title="Удалить сессию"
                  style={{
                    width: 26, height: 26, borderRadius: 6, border: 'none',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer', fontSize: 15, flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget.style.background = 'var(--red-bg, rgba(239,68,68,0.15))'); (e.currentTarget.style.color = 'var(--red)') }}
                  onMouseLeave={(e) => { (e.currentTarget.style.background = 'var(--bg-surface)'); (e.currentTarget.style.color = 'var(--text-secondary)') }}
                >×</button>
              </div>
            )
          })}
          {sessions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '24px 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
              Нет сессий
            </div>
          )}
        </div>
      </div>

      {agentModal !== false && (
        <AgentModal
          agent={agentModal ?? undefined}
          onClose={() => setAgentModal(false)}
          onSaved={() => { loadAgents(); setAgentModal(false) }}
        />
      )}
    </>
  )
}
