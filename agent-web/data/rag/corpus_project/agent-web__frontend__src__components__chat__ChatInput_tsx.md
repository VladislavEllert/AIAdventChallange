<!-- source: agent-web/frontend/src/components/chat/ChatInput.tsx | title: ChatInput.tsx -->

import { useRef, useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../../stores/useAppStore'
import { useChatStore } from '../../stores/useChatStore'
import { streamChat } from '../../api/chat'
import { listModels } from '../../api/models'
import { createSession } from '../../api/sessions'
import { listInvariants, addInvariant } from '../../api/invariants'
import { listProfiles, getProfile } from '../../api/profiles'
import { getMemory } from '../../api/memory'
import { useIsMobile } from '../../hooks/useIsMobile'

// All slash commands from CLI
const SLASH_COMMANDS = [
  { cmd: '/model', desc: 'Показать / сменить модель', usage: '/model [model-id]' },
  { cmd: '/clear', desc: 'Очистить чат (только UI)', usage: '/clear' },
  { cmd: '/new', desc: 'Новая сессия', usage: '/new [название]' },
  { cmd: '/task', desc: 'Открыть Task FSM', usage: '/task [запрос]' },
  { cmd: '/state', desc: 'Текущее состояние задачи', usage: '/state' },
  { cmd: '/profile', desc: 'Управление профилями', usage: '/profile show|list' },
  { cmd: '/invariants', desc: 'Управление инвариантами', usage: '/invariants list|add <текст>' },
  { cmd: '/memory', desc: 'Показать слои памяти', usage: '/memory' },
  { cmd: '/help', desc: 'Список команд', usage: '/help' },
  { cmd: '/mcp', desc: 'Список MCP-инструментов на VPS', usage: '/mcp' },
  { cmd: '/ping', desc: 'Live мониторинг цены (акция или индекс)', usage: '/ping IMOEX [сек]' },
  { cmd: '/history', desc: 'Сводка из SQLite за N минут (24/7 сбор)', usage: '/history IMOEX [минуты]' },
]

// Ping sub-suggestions: tickers + indices
const PING_TICKERS = [
  { value: 'IMOEX', desc: 'Индекс МосБиржи (~2240 пунктов)', icon: '📊' },
  { value: 'RTSI',  desc: 'Индекс РТС (в USD)',               icon: '💵' },
  { value: 'SBER',  desc: 'Сбербанк',                         icon: '🏦' },
  { value: 'GAZP',  desc: 'Газпром',                          icon: '⛽' },
  { value: 'YNDX',  desc: 'Яндекс',                           icon: '🔍' },
  { value: 'LKOH',  desc: 'ЛУКОЙЛ',                           icon: '🛢️' },
  { value: 'MOEX',  desc: 'Акции Мосбиржи',                   icon: '🏛️' },
  { value: 'TCSG',  desc: 'Т-Банк (Тинькофф)',                icon: '💳' },
]

const PING_INTERVALS = [
  { value: '3',  desc: 'каждые 3 сек (быстро)' },
  { value: '5',  desc: 'каждые 5 сек (по умолчанию)' },
  { value: '10', desc: 'каждые 10 сек (медленно)' },
]

const HISTORY_PERIODS = [
  { value: '30',  desc: 'последние 30 мин' },
  { value: '60',  desc: 'последний час' },
  { value: '120', desc: 'последние 2 часа' },
  { value: '480', desc: 'последние 8 часов' },
]


export default function ChatInput() {
  const isMobile = useIsMobile()
  const [text, setText] = useState('')
  const [imageB64, setImageB64] = useState<string | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [showCommands, setShowCommands] = useState(false)
  const [models, setModels] = useState<{ model_id: string; type?: 'text' | 'image' }[]>([])
  const [showModelPicker, setShowModelPicker] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const activeSessionId = useAppStore((s) => s.activeSessionId)
  const activeAgentId = useAppStore((s) => s.activeAgentId)
  const userName = useAppStore((s) => s.userName)
  const activeAgentPersona = useAppStore((s) => s.activeAgentPersona)
  const activeModel = useAppStore((s) => s.activeModel)
  const setActiveModel = useAppStore((s) => s.setActiveModel)
  const activeProfileName = useAppStore((s) => s.activeProfileName)
  const ragEnabled = useAppStore((s) => s.ragEnabled)
  const mcpEnabled = useAppStore((s) => s.mcpEnabled)
  const setActiveSessionId = useAppStore((s) => s.setActiveSessionId)
  const toggleRightPanel = useAppStore((s) => s.toggleRightPanel)
  const rightPanelOpen = useAppStore((s) => s.rightPanelOpen)
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const { addMessage, appendChunk, finalizeMessage, appendSources, appendRagMeta, appendTaskState, setImageProgress, setGeneratedImage, setStreaming, addCost, setViolation, setToolStatus, reset } = useChatStore()
  const isImageModel = (activeModel ?? '').startsWith('comfyui/')

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
  }, [setStreaming])

  // Filter commands by typed prefix
  const filteredCmds = SLASH_COMMANDS.filter((c) =>
    text.startsWith('/') && c.cmd.startsWith(text.split(' ')[0])
  )

  // Ping sub-suggestion state
  const _pingParts = text.trim().split(/\s+/)
  const isPingCmd = _pingParts[0] === '/ping'
  const pingHasSpace = text.startsWith('/ping ')
  const pingTickerRaw = _pingParts[1]?.toUpperCase() ?? ''
  const pingTickerMatch = PING_TICKERS.find(t => t.value === pingTickerRaw)
  const pingShowTickers = isPingCmd && pingHasSpace && !pingTickerMatch
  const pingShowInterval = isPingCmd && !!pingTickerMatch && _pingParts.length < 3
  const filteredPingTickers = pingShowTickers
    ? PING_TICKERS.filter(t => t.value.startsWith(pingTickerRaw))
    : []

  // History sub-suggestion state (same pattern as ping)
  const _histParts = text.trim().split(/\s+/)
  const isHistCmd = _histParts[0] === '/history'
  const histHasSpace = text.startsWith('/history ')
  const histTickerRaw = _histParts[1]?.toUpperCase() ?? ''
  const histTickerMatch = PING_TICKERS.find(t => t.value === histTickerRaw)
  const histShowTickers = isHistCmd && histHasSpace && !histTickerMatch
  const histShowPeriod = isHistCmd && !!histTickerMatch && _histParts.length < 3
  const filteredHistTickers = histShowTickers
    ? PING_TICKERS.filter(t => t.value.startsWith(histTickerRaw))
    : []

  useEffect(() => {
    if (text.startsWith('/')) {
      setShowCommands(
        filteredCmds.length > 0 ||
        filteredPingTickers.length > 0 ||
        pingShowInterval ||
        filteredHistTickers.length > 0 ||
        histShowPeriod
      )
    } else {
      setShowCommands(false)
    }
  }, [text])

  const adjustHeight = () => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
  }

  const clearImage = () => {
    setImageB64(null)
    setImagePreview(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      setImageB64(result.split(',')[1])
      setImagePreview(result)
    }
    reader.readAsDataURL(file)
  }

  // Execute slash command locally
  const executeCommand = useCallback(async (cmd: string): Promise<boolean> => {
    const parts = cmd.trim().split(/\s+/)
    const base = parts[0]

    if (base === '/clear') {
      reset()
      return true
    }

    if (base === '/help') {
      // No-args /help stays a pure client-side command list (unchanged UX).
      // `/help <question>` (day 31) is NOT handled here — it needs a backend
      // round-trip (RAG over the project KB + a real git-branch MCP call), so
      // fall through (return false) and let send() forward it to /api/chat/stream.
      if (parts.length === 1) {
        addMessage({
          id: crypto.randomUUID(), role: 'assistant',
          content: SLASH_COMMANDS.map((c) =>
            `**${c.cmd}** — ${c.desc}\n\`${c.usage}\``
          ).join('\n\n'),
        })
        return true
      }
      return false
    }

    if (base === '/model') {
      const modelArg = parts[1]
      if (modelArg) {
        setActiveModel(modelArg)
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `✅ Модель переключена на \`${modelArg}\`` })
      } else {
        // Show model picker
        try {
          const ms = await listModels()
          setModels(ms)
          setShowModelPicker(true)
        } catch {
          addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Не удалось загрузить список моделей' })
        }
      }
      return true
    }

    if (base === '/new') {
      const name = parts.slice(1).join(' ')
      try {
        const s = await createSession(name, activeAgentId ?? '__default__', userName)
        setActiveSessionId(s.session_id)
        reset()
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `✅ Новая сессия создана: \`${s.display_name}\`` })
      } catch {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Не удалось создать сессию' })
      }
      return true
    }

    if (base === '/memory') {
      if (!activeSessionId) {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '⚠ Выбери сессию' })
        return true
      }
      try {
        const m = await getMemory(activeSessionId)
        const lines = [
          `🧠 **Память сессии** \`${activeSessionId}\`\n`,
          `• Сообщений: **${m.short_term_count}/${m.short_term_limit}**`,
          `• После сжатия остаётся: ${m.keep_recent}`,
          m.summary ? `• Резюме: ${m.summary.slice(0, 200)}` : '',
          Object.keys(m.working).length
            ? `• Рабочая память: ${JSON.stringify(m.working).slice(0, 200)}`
            : '',
        ].filter(Boolean).join('\n')
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: lines })
      } catch {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Память не загружена (начни чат)' })
      }
      if (!rightPanelOpen) toggleRightPanel()
      return true
    }

    if (base === '/invariants') {
      const sub = parts[1]
      if (!sub || sub === 'list') {
        try {
          const invs = await listInvariants()
          const content = invs.length
            ? `🛡 **Инварианты** (${invs.length}):\n${invs.map((v, i) => `${i + 1}. ${v}`).join('\n')}`
            : '🛡 Нет инвариантов. Добавь: `/invariants add <правило>`'
          addMessage({ id: crypto.randomUUID(), role: 'assistant', content })
        } catch {
          addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Ошибка загрузки инвариантов' })
        }
      } else if (sub === 'add') {
        const text = parts.slice(2).join(' ')
        if (!text) {
          addMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'Использование: `/invariants add <текст правила>`' })
        } else {
          try {
            const invs = await addInvariant(text)
            addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `✅ Добавлено. Всего инвариантов: ${invs.length}` })
          } catch {
            addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Ошибка добавления' })
          }
        }
      }
      if (!rightPanelOpen) toggleRightPanel()
      return true
    }

    if (base === '/profile') {
      const sub = parts[1]
      try {
        const profiles = await listProfiles()
        if (!sub || sub === 'list') {
          addMessage({
            id: crypto.randomUUID(), role: 'assistant',
            content: `👤 **Профили:** ${profiles.length ? profiles.join(', ') : 'нет'}\n\nИспользование:\n- \`/profile show <name>\` — просмотр\n- \`/profile list\` — список`
          })
        } else if (sub === 'show') {
          const name = parts[2] || profiles[0]
          if (!name) {
            addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '⚠ Укажи имя профиля' })
          } else {
            const p = await getProfile(name)
            addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `👤 **Профиль: ${name}**\n\`\`\`\n${p.content.slice(0, 500)}\n\`\`\`` })
          }
        }
      } catch {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '❌ Ошибка загрузки профилей' })
      }
      if (!rightPanelOpen) toggleRightPanel()
      return true
    }

    if (base === '/state') {
      if (!activeSessionId) {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '⚠ Выбери сессию' })
        return true
      }
      try {
        const m = await getMemory(activeSessionId)
        addMessage({
          id: crypto.randomUUID(), role: 'assistant',
          content: `📊 **Состояние агента**\n\n- Сессия: \`${activeSessionId}\`\n- В контексте: ${m.short_term_count} сообщ.\n- Лимит: ${m.short_term_limit}\n- Резюме: ${m.summary ? 'есть' : 'нет'}\n- Рабочая память: ${Object.keys(m.working).length ? JSON.stringify(m.working) : 'пусто'}`
        })
      } catch {
        addMessage({ id: crypto.randomUUID(), role: 'assistant', content: '⚠ Нет данных о сессии' })
      }
      return true
    }

    // /task — открывает Task FSM панель
    if (base === '/task') {
      setRightPanelTab('task')
      if (!rightPanelOpen) toggleRightPanel()
      addMessage({
        id: crypto.randomUUID(), role: 'assistant',
        content: '⚙️ Открыл **Task FSM**. Введи задачу в правой панели и нажми ▶ Запустить.',
      })
      return true
    }

    return false
  }, [reset, addMessage, setActiveModel, setActiveSessionId, toggleRightPanel, rightPanelOpen, setRightPanelTab, activeAgentId, activeSessionId, userName])

  const send = useCallback(async () => {
    const msg = text.trim()
    if ((!msg && !imageB64) || isStreaming) return

    // Handle slash commands before sending
    if (msg.startsWith('/')) {
      const handled = await executeCommand(msg)
      if (handled) {
        setText('')
        if (textareaRef.current) textareaRef.current.style.height = 'auto'
        return
      }
    }

    if (!activeSessionId) return

    const sentImage = imagePreview
    const sentB64 = imageB64
    setText('')
    clearImage()
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const apiMsg = msg

    const userId = crypto.randomUUID()
    addMessage({ id: userId, role: 'user', content: msg, imagePreview: sentImage ?? undefined })

    const assistantId = crypto.randomUUID()
    addMessage({
      id: assistantId, role: 'assistant', content: '', streaming: true,
      imageProgressPct: isImageModel ? 0 : undefined,
    })
    setStreaming(true)

    const ctrl = new AbortController()
    abortRef.current = ctrl

    await streamChat(
      activeSessionId,
      apiMsg || '📎',
      {
        onChunk: (t) => appendChunk(assistantId, t),
        onUsage: (u) => { finalizeMessage(assistantId, u); addCost(u) },
        onViolation: (inv, desc) => setViolation({ invariant: inv, desc }),
        onToolStart: (_, label) => setToolStatus(label),
        onToolDone: () => setToolStatus(null),
        onSources: (sources) => appendSources(assistantId, sources),
        onRagMeta: (meta) => appendRagMeta(assistantId, meta),
        onTaskState: (ts) => appendTaskState(assistantId, ts),
        onImageProgress: (pct) => setImageProgress(assistantId, pct),
        onImage: (dataB64) => setGeneratedImage(assistantId, dataB64),
        onDone: () => { setToolStatus(null); setStreaming(false); abortRef.current = null },
        onError: (e) => {
          // Network-level failure (server unreachable, connection dropped) —
          // this used to only console.error and leave the bubble empty with
          // no visible feedback. Show something instead of silence.
          appendChunk(assistantId, `❌ Не удалось связаться с сервером: ${e.message}`)
          finalizeMessage(assistantId, { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, cost_rub: 0, elapsed_ms: 0 })
          setStreaming(false)
          abortRef.current = null
          console.error(e)
        },
      },
      sentB64 ?? undefined,
      activeAgentPersona || undefined,
      activeModel || undefined,
      activeProfileName || undefined,
      ctrl.signal,
      ragEnabled || undefined,
      mcpEnabled,
    )
  }, [text, imageB64, imagePreview, isStreaming, activeSessionId, activeAgentPersona, activeModel, isImageModel,
      activeProfileName, ragEnabled, mcpEnabled, executeCommand, addMessage, appendChunk, finalizeMessage,
      appendSources, appendRagMeta, appendTaskState, setImageProgress, setGeneratedImage, setStreaming, addCost,
      setViolation, setToolStatus])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
    if (e.key === 'Escape') setShowCommands(false)
  }

  const canSend = (text.trim().length > 0 || !!imageB64) && !isStreaming

  return (
    <div style={{ padding: '0 16px 20px', position: 'relative' }}>

      {/* Slash command popover */}
      {showCommands && (
        <div
          ref={popoverRef}
          className="glass-strong"
          style={{
            position: 'absolute', bottom: '100%', left: 16, right: 16,
            marginBottom: 8, borderRadius: 12, overflow: 'hidden', zIndex: 50,
          }}
        >
          {/* /ping TICKER suggestions */}
          {filteredPingTickers.length > 0 && (
            <>
              <div style={{ padding: '6px 14px 4px', fontSize: 11, color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border)' }}>
                /ping — выбери тикер или индекс:
              </div>
              {filteredPingTickers.map((t) => (
                <div
                  key={t.value}
                  onClick={() => { setText(`/ping ${t.value} `); setShowCommands(false); textareaRef.current?.focus() }}
                  style={{ padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'baseline', gap: 8, transition: 'background 0.1s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 13 }}>{t.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent)', flexShrink: 0 }}>{t.value}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.desc}</span>
                </div>
              ))}
            </>
          )}

          {/* /ping TICKER [interval] suggestions */}
          {pingShowInterval && (
            <>
              <div style={{ padding: '6px 14px 4px', fontSize: 11, color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border)' }}>
                /ping {pingTickerRaw} — выбери интервал (сек):
              </div>
              {PING_INTERVALS.map((iv) => (
                <div
                  key={iv.value}
                  onClick={() => { setText(`/ping ${pingTickerRaw} ${iv.value}`); setShowCommands(false); textareaRef.current?.focus() }}
                  style={{ padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'baseline', gap: 8, transition: 'background 0.1s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent)', flexShrink: 0 }}>{iv.value}с</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{iv.desc}</span>
                </div>
              ))}
            </>
          )}

          {/* /history TICKER suggestions */}
          {filteredHistTickers.length > 0 && (
            <>
              <div style={{ padding: '6px 14px 4px', fontSize: 11, color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border)' }}>
                /history — выбери тикер или индекс:
              </div>
              {filteredHistTickers.map((t) => (
                <div
                  key={t.value}
                  onClick={() => { setText(`/history ${t.value} `); setShowCommands(false); textareaRef.current?.focus() }}
                  style={{ padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'baseline', gap: 8, transition: 'background 0.1s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 13 }}>{t.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent)', flexShrink: 0 }}>{t.value}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.desc}</span>
                </div>
              ))}
            </>
          )}

          {/* /history TICKER [period] suggestions */}
          {histShowPeriod && (
            <>
              <div style={{ padding: '6px 14px 4px', fontSize: 11, color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border)' }}>
                /history {histTickerRaw} — выбери период:
              </div>
              {HISTORY_PERIODS.map((p) => (
                <div
                  key={p.value}
                  onClick={() => { setText(`/history ${histTickerRaw} ${p.value}`); setShowCommands(false); textareaRef.current?.focus() }}
                  style={{ padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'baseline', gap: 8, transition: 'background 0.1s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent)', flexShrink: 0 }}>{p.value} мин</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.desc}</span>
                </div>
              ))}
            </>
          )}

          {/* Regular slash commands (only when not in ping/history sub-mode) */}
          {!pingShowTickers && !pingShowInterval && !histShowTickers && !histShowPeriod && filteredCmds.map((c) => (
            <div
              key={c.cmd}
              onClick={() => { setText(c.cmd + ' '); setShowCommands(false); textareaRef.current?.focus() }}
              style={{
                padding: '9px 14px', cursor: 'pointer', display: 'flex',
                alignItems: 'baseline', gap: 10, transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent)', flexShrink: 0 }}>
                {c.cmd}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c.desc}</span>
            </div>
          ))}
        </div>
      )}

      {/* Model picker popover */}
      {showModelPicker && (
        <div
          className="glass-strong"
          style={{
            position: 'absolute', bottom: '100%', left: 16, right: 16,
            marginBottom: 8, borderRadius: 12, overflow: 'hidden', zIndex: 50, maxHeight: 320, overflowY: 'auto',
          }}
        >
          <div style={{ padding: '10px 14px', fontSize: 12, color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border)' }}>
            Выбери модель — текущая: <strong style={{ color: 'var(--text-primary)' }}>{activeModel}</strong>
          </div>
          {models.map((m) => (
            <div
              key={m.model_id}
              onClick={() => {
                setActiveModel(m.model_id)
                setShowModelPicker(false)
                addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `✅ Модель: \`${m.model_id}\`` })
              }}
              style={{
                padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                color: m.model_id === activeModel ? 'var(--accent)' : 'var(--text-primary)',
                background: m.model_id === activeModel ? 'var(--accent-bg)' : 'transparent',
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => { if (m.model_id !== activeModel) (e.currentTarget.style.background = 'var(--bg-surface-hover)') }}
              onMouseLeave={(e) => { if (m.model_id !== activeModel) (e.currentTarget.style.background = 'transparent') }}
            >
              {m.model_id === activeModel ? '✓ ' : ''}{m.type === 'image' ? '🖼 ' : '💬 '}{m.model_id}
            </div>
          ))}
        </div>
      )}

      {/* Image preview */}
      {imagePreview && (
        <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <img src={imagePreview} alt="attachment"
              style={{ maxHeight: 120, maxWidth: 200, borderRadius: 12, border: '1px solid var(--border)', display: 'block' }} />
            <button onClick={clearImage} style={{
              position: 'absolute', top: -8, right: -8, width: 22, height: 22, borderRadius: '50%',
              background: 'var(--red)', color: '#fff', border: 'none', cursor: 'pointer',
              fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>×</button>
          </div>
        </div>
      )}

      <div className="glass" style={{ borderRadius: 16, padding: '10px 10px 10px 14px', display: 'flex', alignItems: 'center', gap: 8, boxShadow: 'var(--shadow-md)' }}>
        {/* Attach */}
        <button onClick={() => fileRef.current?.click()} disabled={isStreaming} title="Прикрепить файл"
          style={{ width: isMobile ? 44 : 32, height: isMobile ? 44 : 32, borderRadius: 8, border: 'none', background: 'transparent', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'color 0.15s' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
        <input ref={fileRef} type="file" accept="image/*" onChange={onFileChange} style={{ display: 'none' }} />

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => { setText(e.target.value); adjustHeight() }}
          onKeyDown={handleKeyDown}
          placeholder={
            !activeSessionId ? 'Выбери или создай сессию'
              : isImageModel ? 'Опиши картинку… (например: рыжий кот на подоконнике, фотореализм)'
              : 'Напиши сообщение… (/ — команды, Shift+Enter — перенос)'
          }
          disabled={isStreaming}
          rows={1}
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none', resize: 'none',
            // iOS Safari auto-zooms the page on focus if font-size < 16px — keep it at 16 on mobile.
            color: 'var(--text-primary)', fontSize: isMobile ? 16 : 14, lineHeight: 1.6,
            minHeight: 24, maxHeight: 200, fontFamily: 'inherit',
          }}
        />

        {isStreaming ? (
          /* Stop button — shown during streaming */
          <button
            onClick={stopStreaming}
            title="Остановить"
            style={{
              width: isMobile ? 44 : 34, height: isMobile ? 44 : 34, borderRadius: 8,
              background: 'var(--accent)', color: '#fff',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'all 0.15s', border: 'none',
            } as React.CSSProperties}
          >
            {/* Square stop icon */}
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <rect x="1" y="1" width="10" height="10" rx="2" />
            </svg>
          </button>
        ) : (
          /* Send button */
          <button onClick={send} disabled={!canSend}
            style={{
              width: isMobile ? 44 : 34, height: isMobile ? 44 : 34, borderRadius: '50%',
              background: canSend ? 'var(--accent)' : 'var(--bg-surface)',
              color: canSend ? '#fff' : 'var(--text-tertiary)',
              cursor: canSend ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'all 0.15s',
              border: canSend ? 'none' : '1px solid var(--border)',
            } as React.CSSProperties}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        )}
      </div>
      <div style={{ textAlign: 'center', marginTop: 6, fontSize: 11, color: 'var(--text-tertiary)' }}>
        Enter — отправить · Shift+Enter — новая строка · / — команды
      </div>
    </div>
  )
}
