import { get, post, put, del } from './client'

export interface SessionOut {
  session_id: string
  name: string
  display_name: string
  created_at: number
  updated_at: number
  profile_name: string
  model: string
  msg_count: number
  cost_rub: number
  owner: string
}

export interface MessageOut {
  role: string
  content: string
}

export interface SessionDetail extends SessionOut {
  summary: string
  messages: MessageOut[]
}

export const listSessions = (agentId?: string, owner?: string) => {
  const params = new URLSearchParams()
  if (agentId) params.set('agent_id', agentId)
  if (owner) params.set('owner', owner)
  const qs = params.toString()
  return get<SessionOut[]>(qs ? `/sessions?${qs}` : '/sessions')
}

export const createSession = (name = '', agentId?: string, owner = '') =>
  post<SessionOut>('/sessions', { name, agent_id: agentId, owner })

export const getSession = (id: string) => get<SessionDetail>(`/sessions/${id}`)
export const renameSession = (id: string, name: string) => put(`/sessions/${id}`, { name })
export const deleteSession = (id: string) => del(`/sessions/${id}`)
