<!-- source: agent-web/frontend/src/api/metrics.ts | title: metrics.ts -->

import { get } from './client'

export interface OllamaModelLoad {
  name: string
  size_vram_gb: number
}

export interface Metrics {
  reachable: boolean
  cpu_pct?: number | null
  ram_used_gb?: number | null
  ram_total_gb?: number | null
  gpu_pct?: number | null
  vram_used_gb?: number | null
  vram_total_gb?: number | null
  gpu_temp_c?: number | null
  ollama_models?: OllamaModelLoad[]
}

export const getMetrics = () => get<Metrics>('/metrics')
