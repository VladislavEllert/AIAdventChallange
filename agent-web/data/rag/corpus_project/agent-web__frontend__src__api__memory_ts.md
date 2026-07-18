<!-- source: agent-web/frontend/src/api/memory.ts | title: memory.ts -->

import { api, get } from './client'

export interface MemoryState {
  session_id: string
  short_term_count: number
  short_term_limit: number
  keep_recent: number
  summary: string
  working: Record<string, unknown>
  messages: { role: string; content: string }[]
}

export const getMemory = (sessionId: string) => get<MemoryState>(`/memory/${sessionId}`)

export async function extractProfile(sessionId: string, profileName: string): Promise<{ updated: boolean; layers: Record<string, string[]> }> {
  const r = await api(`/memory/${sessionId}/extract-profile?profile_name=${encodeURIComponent(profileName)}`, { method: 'POST' })
  return r.json()
}
