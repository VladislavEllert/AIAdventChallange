import { api } from './client'

export interface Settings {
  short_term_limit: number
  keep_recent: number
  default_model: string
  auto_profile_update: boolean
  theme: string
}

export async function getSettings(): Promise<Settings> {
  const r = await api('/settings')
  return r.json()
}

export async function updateSettings(patch: Partial<Settings>): Promise<Settings> {
  const r = await api('/settings', { method: 'PUT', body: JSON.stringify(patch) })
  return r.json()
}
