import { api } from './client'

export interface Settings {
  short_term_limit: number
  keep_recent: number
  default_model: string
  auto_profile_update: boolean
  theme: string
  temperature: number
  max_tokens: number
  top_p: number
  num_ctx: number
  image_steps: number
  image_cfg: number
  image_seed: number | null
  image_width: number
  image_height: number
}

export interface SettingsPatch extends Partial<Settings> {
  image_seed_random?: boolean
}

export async function getSettings(): Promise<Settings> {
  const r = await api('/settings')
  return r.json()
}

export async function updateSettings(patch: SettingsPatch): Promise<Settings> {
  const r = await api('/settings', { method: 'PUT', body: JSON.stringify(patch) })
  return r.json()
}
