import { useEffect, useState } from 'react'
import { getMetrics, type Metrics } from '../../api/metrics'

// Status color by threshold — magnitude mapped to state (good/warning/critical),
// numeric value always shown alongside so color is never the only signal.
function statusColor(pct: number | null | undefined): string {
  if (pct == null) return 'var(--text-tertiary)'
  if (pct >= 90) return 'var(--red)'
  if (pct >= 70) return 'var(--yellow)'
  return 'var(--green)'
}

function Meter({ label, pct, detail }: { label: string; pct: number | null | undefined; detail: string }) {
  const color = statusColor(pct)
  return (
    <div title={`${label}: ${detail}`} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <span style={{ color: 'var(--text-tertiary)' }}>{label}</span>
      <div style={{
        width: 36, height: 5, borderRadius: 3, background: 'var(--border)',
        overflow: 'hidden', flexShrink: 0,
      }}>
        <div style={{
          height: '100%', width: `${Math.min(100, Math.max(0, pct ?? 0))}%`,
          background: color, transition: 'width 0.4s ease, background 0.4s ease',
        }} />
      </div>
      <span style={{ color, fontVariantNumeric: 'tabular-nums', minWidth: 28 }}>
        {pct == null ? '—' : `${Math.round(pct)}%`}
      </span>
    </div>
  )
}

export default function MetricsHud() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const m = await getMetrics()
        if (!cancelled) setMetrics(m)
      } catch {
        if (!cancelled) setMetrics({ reachable: false })
      }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  if (!metrics) return null

  if (!metrics.reachable) {
    return (
      <span style={{ color: 'var(--text-tertiary)' }} title="Windows-агент метрик недоступен (metrics_server.py на :11435)">
        🖥 офлайн
      </span>
    )
  }

  const ramPct = metrics.ram_used_gb != null && metrics.ram_total_gb
    ? (metrics.ram_used_gb / metrics.ram_total_gb) * 100 : null
  const vramPct = metrics.vram_used_gb != null && metrics.vram_total_gb
    ? (metrics.vram_used_gb / metrics.vram_total_gb) * 100 : null

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <Meter label="CPU" pct={metrics.cpu_pct} detail={`${metrics.cpu_pct?.toFixed(0)}%`} />
      <Meter
        label="RAM" pct={ramPct}
        detail={`${metrics.ram_used_gb?.toFixed(1)}/${metrics.ram_total_gb?.toFixed(1)} GB`}
      />
      <Meter label="GPU" pct={metrics.gpu_pct} detail={`${metrics.gpu_pct?.toFixed(0)}%${metrics.gpu_temp_c ? `, ${metrics.gpu_temp_c.toFixed(0)}°C` : ''}`} />
      <Meter
        label="VRAM" pct={vramPct}
        detail={`${metrics.vram_used_gb?.toFixed(1)}/${metrics.vram_total_gb?.toFixed(1)} GB`}
      />
      {metrics.ollama_models && metrics.ollama_models.length > 0 && (
        <span style={{ color: 'var(--text-tertiary)' }}>
          🧠 {metrics.ollama_models.map((m) => m.name).join(', ')}
        </span>
      )}
    </div>
  )
}
