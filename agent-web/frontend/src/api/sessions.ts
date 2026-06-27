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
}

export interface MessageOut {
  role: string
  content: string
}

export interface SessionDetail extends SessionOut {
  summary: string
  messages: MessageOut[]
}

export const listSessions = (agentId?: string) =>
  get<SessionOut[]>(agentId ? `/sessions?agent_id=${encodeURIComponent(agentId)}` : '/sessions')

export const createSession = (name = '', agentId?: string) =>
  post<SessionOut>('/sessions', { name, agent_id: agentId })

export const getSession = (id: string) => get<SessionDetail>(`/sessions/${id}`)
export const renameSession = (id: string, name: string) => put(`/sessions/${id}`, { name })
export const deleteSession = (id: string) => del(`/sessions/${id}`)
