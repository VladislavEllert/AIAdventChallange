<!-- source: agent-web/frontend/src/components/panels/TaskPanel.tsx | title: TaskPanel.tsx -->

import { useEffect, useRef, useState } from 'react'
import { createTask, sendFeedback, streamTask, type TaskMessage } from '../../api/tasks'

const STAGES = ['planning', 'execution', 'validation', 'done'] as const
type Stage = typeof STAGES[number]

const STAGE_LABELS: Record<string, string> = {
  planning: 'Планирование',
  execution: 'Выполнение',
  validation: 'Валидация',
  done: 'Готово',
}

const STAGE_ICONS: Record<string, string> = {
  planning: '🧠',
  execution: '⚙️',
  validation: '✅',
  done: '🎉',
}

export default function TaskPanel() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [stage, setStage] = useState<string>('planning')
  const [log, setLog] = useState<TaskMessage[]>([])
  const [running, setRunning] = useState(false)
  const [paused, setPaused] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmPrompt, setConfirmPrompt] = useState<string | null>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [request, setRequest] = useState('')
  const logRef = useRef<HTMLDivElement>(null)
  const stopStream = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [log])

  const handleMessage = (msg: TaskMessage) => {
    setLog((prev) => [...prev, msg])
    if (msg.type === 'confirm') {
      setPaused(true)
      setConfirmPrompt(msg.prompt ?? 'Продолжить?')
    } else if (msg.type === 'done') {
      setDone(true)
      setRunning(false)
      setPaused(false)
      if (msg.stage) setStage(msg.stage)
    } else if (msg.type === 'error') {
      setError(msg.text ?? 'Неизвестная ошибка')
      setRunning(false)
      setPaused(false)
    }
  }

  const start = async () => {
    if (!request.trim()) return
    setLog([])
    setDone(false)
    setPaused(false)
    setError(null)
    setConfirmPrompt(null)
    setFeedbackText('')
    setStage('planning')
    setRunning(true)

    try {
      const res = await createTask(request.trim())
      setTaskId(res.task_id)
      setStage(res.stage)
      const stop = streamTask(res.task_id, handleMessage, () => {
        setRunning(false)
      })
      stopStream.current = stop
    } catch (e: unknown) {
      setError(String(e))
      setRunning(false)
    }
  }

  const feedback = async (action: 'continue' | 'pause' | 'feedback') => {
    if (!taskId) return
    try {
      await sendFeedback(taskId, action, feedbackText)
      if (action === 'pause') {
        setRunning(false)
        setPaused(false)
      } else {
        setPaused(false)
        setRunning(true)
        setConfirmPrompt(null)
        setFeedbackText('')
      }
    } catch (e) {
      console.error(e)
    }
  }

  const reset = () => {
    stopStream.current?.()
    stopStream.current = null
    setTaskId(null)
    setLog([])
    setDone(false)
    setPaused(false)
    setRunning(false)
    setError(null)
    setConfirmPrompt(null)
    setFeedbackText('')
    setRequest('')
    setStage('planning')
  }

  const stageIdx = STAGES.indexOf(stage as Stage)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 16, gap: 12 }}>

      {/* Stage indicator */}
      <div style={{ display: 'flex', gap: 4 }}>
        {STAGES.map((s, i) => {
          const isActive = s === stage && running
          const isDone = i < stageIdx || (s === 'done' && done)
          return (
            <div key={s} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
              <div style={{
                width: '100%', height: 3, borderRadius: 2,
                background: isDone ? 'var(--green)' : isActive ? 'var(--accent)' : 'var(--border)',
                transition: 'background 0.3s',
              }} />
              <span style={{
                fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.05em',
                color: isActive ? 'var(--accent)' : isDone ? 'var(--green)' : 'var(--text-tertiary)',
              }}>
                {STAGE_ICONS[s]} {STAGE_LABELS[s]}
              </span>
            </div>
          )
        })}
      </div>

      {/* Task input (only when not running) */}
      {!taskId && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="Опиши задачу для агента…"
            rows={4}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 10,
              border: '1px solid var(--border)', background: 'var(--bg-input)',
              color: 'var(--text-primary)', fontSize: 13, resize: 'none',
              fontFamily: 'inherit', lineHeight: 1.5, outline: 'none',
              boxSizing: 'border-box',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.metaKey) { e.preventDefault(); start() }
            }}
          />
          <button
            onClick={start}
            disabled={!request.trim()}
            style={{
              padding: '9px 16px', borderRadius: 10, border: 'none',
              background: request.trim() ? 'var(--accent)' : 'var(--border)',
              color: '#fff', fontSize: 13, fontWeight: 600, cursor: request.trim() ? 'pointer' : 'default',
              transition: 'background 0.15s',
            }}
          >
            ▶ Запустить задачу
          </button>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textAlign: 'center' }}>
            ⌘↵ для запуска
          </div>
        </div>
      )}

      {/* Output log */}
      {taskId && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
              Задача <span style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>{taskId}</span>
            </span>
            <button
              onClick={reset}
              style={{
                fontSize: 11, color: 'var(--text-tertiary)', background: 'none',
                border: 'none', cursor: 'pointer',
              }}
            >✕ Сбросить</button>
          </div>

          <div
            ref={logRef}
            style={{
              flex: 1, overflowY: 'auto', padding: '10px 12px',
              background: 'var(--bg-base)', borderRadius: 10,
              border: '1px solid var(--border)',
              fontFamily: 'ui-monospace, monospace', fontSize: 11.5,
              lineHeight: 1.6, color: 'var(--text-secondary)',
              minHeight: 120,
            }}
          >
            {log.filter(m => m.type === 'output').map((m, i) => (
              <div key={i} style={{ whiteSpace: 'pre-wrap', marginBottom: 2 }}>{m.text}</div>
            ))}
            {running && !paused && (
              <div style={{ color: 'var(--accent)', marginTop: 4 }}>▌</div>
            )}
            {done && (
              <div style={{ color: 'var(--green)', marginTop: 8, fontWeight: 600 }}>
                🎉 Задача завершена
              </div>
            )}
            {error && (
              <div style={{ color: 'var(--red)', marginTop: 8 }}>⚠ {error}</div>
            )}
          </div>

          {/* Confirm/feedback controls */}
          {paused && confirmPrompt && (
            <div className="glass" style={{ borderRadius: 12, padding: 12, border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}>
              <div style={{ fontSize: 12, color: 'var(--accent)', marginBottom: 8, fontWeight: 500 }}>
                ⏸ {confirmPrompt}
              </div>
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Комментарий (необязательно)…"
                rows={2}
                style={{
                  width: '100%', padding: '8px 10px', borderRadius: 8,
                  border: '1px solid var(--border)', background: 'var(--bg-input)',
                  color: 'var(--text-primary)', fontSize: 12, resize: 'none',
                  fontFamily: 'inherit', lineHeight: 1.4, outline: 'none',
                  marginBottom: 8, boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  onClick={() => feedback('continue')}
                  style={{
                    flex: 1, padding: '7px 0', borderRadius: 8, border: 'none',
                    background: 'var(--accent)', color: '#fff', fontSize: 12,
                    fontWeight: 600, cursor: 'pointer',
                  }}
                >▶ Продолжить</button>
                {feedbackText.trim() && (
                  <button
                    onClick={() => feedback('feedback')}
                    style={{
                      flex: 1, padding: '7px 0', borderRadius: 8, border: 'none',
                      background: 'var(--accent-bg)', color: 'var(--accent)', fontSize: 12,
                      fontWeight: 600, cursor: 'pointer',
                    }}
                  >↺ С правками</button>
                )}
                <button
                  onClick={() => feedback('pause')}
                  style={{
                    padding: '7px 12px', borderRadius: 8,
                    border: '1px solid var(--border)',
                    background: 'transparent', color: 'var(--text-tertiary)',
                    fontSize: 12, cursor: 'pointer',
                  }}
                >⏸ Пауза</button>
              </div>
            </div>
          )}

          {/* Done state */}
          {done && (
            <button
              onClick={reset}
              style={{
                padding: '9px 16px', borderRadius: 10, border: 'none',
                background: 'var(--accent-bg)', color: 'var(--accent)',
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }}
            >+ Новая задача</button>
          )}
        </>
      )}
    </div>
  )
}
