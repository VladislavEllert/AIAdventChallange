const BASE = '/api/agents'

export interface AgentOut {
  id: string
  name: string
  emoji: string
  system_prompt: string
  created_at: number
}

export async function listAgents(): Promise<AgentOut[]> {
  const r = await fetch(BASE)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function createAgent(data: { name: string; emoji: string; system_prompt: string }): Promise<AgentOut> {
  const r = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateAgent(id: string, data: Partial<{ name: string; emoji: string; system_prompt: string }>): Promise<AgentOut> {
  const r = await fetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function deleteAgent(id: string): Promise<void> {
  const r = await fetch(`${BASE}/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
