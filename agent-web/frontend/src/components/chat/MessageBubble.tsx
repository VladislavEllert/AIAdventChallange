import { useState } from 'react'
import type { Message } from '../../stores/useChatStore'
import MarkdownRenderer from './MarkdownRenderer'
import SourcesBlock from './SourcesBlock'
import TaskStateBlock from './TaskStateBlock'

interface Props {
  msg: Message
}

// Shared centered column — both user and assistant within same axis
const CENTER: React.CSSProperties = {
  maxWidth: 720,
  margin: '0 auto',
  padding: '0 20px',
  width: '100%',
}

export default function MessageBubble({ msg }: Props) {
  const [showMeta, setShowMeta] = useState(false)
  const isUser = msg.role === 'user'

  return (
    <div style={{ marginBottom: isUser ? 12 : 20 }}>
      <div style={CENTER}>
        {isUser ? (
          /* User: right-aligned bubble inside centered column */
          <div style={{ display: 'flex', justifyContent: 'flex-end', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            {msg.imagePreview && (
              <img
                src={msg.imagePreview}
                alt="attachment"
                style={{ maxHeight: 160, maxWidth: 260, borderRadius: 12, border: '1px solid var(--border)' }}
              />
            )}
            {msg.content && (
              <div
                style={{
                  maxWidth: '75%',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '18px 18px 4px 18px',
                  padding: '10px 16px',
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: 'var(--text-primary)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {msg.content}
              </div>
            )}
          </div>
        ) : (
          /* Assistant: full-width text, no bubble */
          <div>
            {msg.generatedImageB64 ? (
              <img
                src={`data:image/png;base64,${msg.generatedImageB64}`}
                alt="generated"
                style={{ maxWidth: '100%', borderRadius: 12, border: '1px solid var(--border)', display: 'block' }}
              />
            ) : msg.imageProgressPct !== undefined ? (
              <div style={{ maxWidth: 360 }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  🎨 Генерирую картинку… {msg.imageProgressPct}%
                </div>
                <div style={{ height: 6, borderRadius: 3, background: 'var(--bg-surface)', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${msg.imageProgressPct}%`,
                    background: 'var(--accent)', transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            ) : msg.streaming ? (
              <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                {msg.content}
              </div>
            ) : (
              <div
                className="prose"
                onClick={() => msg.usage && setShowMeta((v) => !v)}
                style={{ cursor: msg.usage ? 'pointer' : 'default' }}
              >
                <MarkdownRenderer content={msg.content} />
              </div>
            )}

            {/* Sources block (day 24) */}
            {msg.sources && msg.sources.length > 0 && (
              <SourcesBlock sources={msg.sources} ragMeta={msg.ragMeta} />
            )}

            {/* Task memory block (day 25) */}
            <TaskStateBlock taskState={msg.taskState} />

            {showMeta && msg.usage && (
              <div style={{
                marginTop: 8, fontSize: 11, color: 'var(--text-tertiary)',
                display: 'flex', gap: 12, alignItems: 'center',
              }}>
                <span>↑{msg.usage.prompt_tokens} ↓{msg.usage.completion_tokens} tok</span>
                <span>₽{msg.usage.cost_rub.toFixed(4)}</span>
                <span>{msg.usage.elapsed_ms}ms</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
