import { get, put } from './client'

export const listProfiles = () => get<string[]>('/profiles')
export const getProfile = (name: string) => get<{ name: string; content: string }>(`/profiles/${name}`)
export const updateProfile = (name: string, content: string) => put(`/profiles/${name}`, { content })
