import { useEffect, useRef } from 'react'
import { useChatStore } from '../../stores/useChatStore'
import MessageBubble from './MessageBubble'

export default function ChatArea() {
  const messages = useChatStore((s) => s.messages)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const toolStatus = useChatStore((s) => s.toolStatus)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isStreaming])

  if (messages.length === 0) {
    return (
      <div
        style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: 16, userSelect: 'none',
        }}
      >
        <div style={{ fontSize: 40, opacity: 0.3 }}>✦</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Начни диалог</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 12, opacity: 0.6 }}>
          Enter — отправить
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', paddingTop: 24, paddingBottom: 8 }}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
      {toolStatus && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 20px', color: 'var(--text-secondary)', fontSize: 13,
        }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1s ease-in-out infinite' }} />
          {toolStatus}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
