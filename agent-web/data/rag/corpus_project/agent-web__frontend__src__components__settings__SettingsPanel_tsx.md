<!-- source: agent-web/frontend/src/components/settings/SettingsPanel.tsx | title: SettingsPanel.tsx -->

import { useEffect, useState } from 'react'
import { useAppStore } from '../../stores/useAppStore'
import { getSettings, updateSettings, type Settings } from '../../api/settings'

function Slider({
  label, value, min, max, step, unit, onChange, hint,
}: {
  label: string; value: number; min: number; max: number; step: number
  unit?: string; onChange: (v: number) => void; hint?: string
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{value}{unit ?? ''}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: 'var(--accent)' }}
      />
      {hint && (
        <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2, lineHeight: 1.4 }}>{hint}</div>
      )}
    </div>
  )
}

export default function SettingsPanel() {
  const activeModel = useAppStore((s) => s.activeModel)
  const isImageModel = (activeModel ?? '').startsWith('comfyui/')
  const isOllamaModel = (activeModel ?? '').startsWith('ollama/')
  const userName = useAppStore((s) => s.userName)
  const setUserName = useAppStore((s) => s.setUserName)
  const [nameDraft, setNameDraft] = useState(userName)

  const [settings, setSettings] = useState<Settings | null>(null)
  const [savedFlash, setSavedFlash] = useState(false)

  useEffect(() => {
    getSettings().then(setSettings).catch(() => setSettings(null))
  }, [])

  const patch = async (p: Partial<Settings> & { image_seed_random?: boolean }) => {
    // Optimistic local update so the slider doesn't jump while the request is in flight.
    setSettings((s) => (s ? { ...s, ...p } as Settings : s))
    try {
      const updated = await updateSettings(p)
      setSettings(updated)
      setSavedFlash(true)
      setTimeout(() => setSavedFlash(false), 800)
    } catch {
      // leave optimistic value — next load will reconcile
    }
  }

  if (!settings) {
    return <div style={{ padding: 16, fontSize: 12, color: 'var(--text-tertiary)' }}>Загрузка настроек…</div>
  }

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ИМЯ</div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 8, lineHeight: 1.5 }}>
        Отделяет твои чаты от чужих на этом сервере — без пароля, просто метка.
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={nameDraft}
          onChange={(e) => setNameDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && nameDraft.trim()) setUserName(nameDraft.trim()) }}
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 8,
            border: '1px solid var(--border)', background: 'var(--bg-input)',
            color: 'var(--text-primary)', fontSize: 12, outline: 'none',
          }}
        />
        <button
          onClick={() => nameDraft.trim() && setUserName(nameDraft.trim())}
          disabled={!nameDraft.trim() || nameDraft.trim() === userName}
          style={{
            padding: '0 12px', borderRadius: 8, border: '1px solid var(--border)',
            background: 'transparent', color: 'var(--text-secondary)', fontSize: 11,
            cursor: nameDraft.trim() && nameDraft.trim() !== userName ? 'pointer' : 'not-allowed',
          }}
        >Сохранить</button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>ГЕНЕРАЦИЯ ТЕКСТА</div>
        {savedFlash && <span style={{ fontSize: 10, color: 'var(--accent)' }}>✓ сохранено</span>}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 8, lineHeight: 1.5 }}>
        Применяется к следующему запросу в любой модели (текстовой).
      </div>

      <Slider
        label="Temperature" value={settings.temperature} min={0} max={2} step={0.1}
        onChange={(v) => patch({ temperature: v })}
      />
      <Slider
        label="Max tokens" value={settings.max_tokens} min={64} max={4096} step={64}
        onChange={(v) => patch({ max_tokens: v })}
        hint={isOllamaModel
          ? '⚠️ Qwen3 сначала "думает" (<think>) — низкое значение может дать пустой ответ, если рассуждение не успело закончиться. Рекомендуется ≥1024.'
          : undefined}
      />
      <Slider
        label="Top P" value={settings.top_p} min={0} max={1} step={0.05}
        onChange={(v) => patch({ top_p: v })}
      />
      <Slider
        label="Context window (num_ctx)" value={settings.num_ctx} min={512} max={16384} step={512}
        onChange={(v) => patch({ num_ctx: v })}
        hint="Только для Ollama-моделей — размер контекстного окна."
      />

      {isImageModel && (
        <>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginTop: 16, marginBottom: 8 }}>
            ГЕНЕРАЦИЯ КАРТИНКИ (SDXL)
          </div>
          <Slider
            label="Steps" value={settings.image_steps} min={5} max={50} step={1}
            onChange={(v) => patch({ image_steps: v })}
          />
          <Slider
            label="CFG scale" value={settings.image_cfg} min={1} max={15} step={0.5}
            onChange={(v) => patch({ image_cfg: v })}
          />
          <Slider
            label="Width" value={settings.image_width} min={512} max={1536} step={64}
            onChange={(v) => patch({ image_width: v })}
          />
          <Slider
            label="Height" value={settings.image_height} min={512} max={1536} step={64}
            onChange={(v) => patch({ image_height: v })}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Seed</span>
            <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
              {settings.image_seed ?? 'случайный'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="number"
              value={settings.image_seed ?? ''}
              placeholder="случайный"
              onChange={(e) => {
                const v = e.target.value
                if (v === '') patch({ image_seed_random: true })
                else patch({ image_seed: parseInt(v, 10) })
              }}
              style={{
                flex: 1, padding: '6px 10px', borderRadius: 8,
                border: '1px solid var(--border)', background: 'var(--bg-input)',
                color: 'var(--text-primary)', fontSize: 12, outline: 'none',
              }}
            />
            <button
              onClick={() => patch({ image_seed_random: true })}
              style={{
                padding: '0 10px', borderRadius: 8, border: '1px solid var(--border)',
                background: 'transparent', color: 'var(--text-secondary)', fontSize: 11, cursor: 'pointer',
              }}
            >🎲 случайный</button>
          </div>
        </>
      )}
    </div>
  )
}
