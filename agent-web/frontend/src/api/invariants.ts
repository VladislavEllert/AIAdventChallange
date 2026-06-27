import { get, post, del } from './client'

export const listInvariants = () => get<string[]>('/invariants')
export const addInvariant = (text: string) => post<string[]>('/invariants', { text })
export const removeInvariant = (index: number) => del<string[]>(`/invariants/${index}`)
