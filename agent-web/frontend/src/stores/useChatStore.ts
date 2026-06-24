import { create } from 'zustand'
import type { ChatUsage } from '../api/chat'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  usage?: ChatUsage
  streaming?: boolean
  imagePreview?: string
}

interface ChatStore {
  messages: Message[]
  isStreaming: boolean
  sessionCost: number
  sessionTokens: number
  violation: { invariant: string; desc: string } | null
  toolStatus: string | null
  setMessages: (msgs: Message[]) => void
  addMessage: (msg: Message) => void
  appendChunk: (id: string, text: string) => void
  finalizeMessage: (id: string, usage: ChatUsage) => void
  setStreaming: (v: boolean) => void
  addCost: (u: ChatUsage) => void
  setViolation: (v: { invariant: string; desc: string } | null) => void
  clearViolation: () => void
  setToolStatus: (v: string | null) => void
  reset: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,
  sessionCost: 0,
  sessionTokens: 0,
  violation: null,
  toolStatus: null,

  setMessages: (msgs) => set({ messages: msgs }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendChunk: (id, text) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + text } : m
      ),
    })),

  finalizeMessage: (id, usage) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false, usage } : m
      ),
    })),

  setStreaming: (v) => set({ isStreaming: v }),

  addCost: (u) =>
    set((s) => ({
      sessionCost: s.sessionCost + u.cost_rub,
      sessionTokens: s.sessionTokens + u.total_tokens,
    })),

  setViolation: (v) => set({ violation: v }),
  clearViolation: () => set({ violation: null }),
  setToolStatus: (v) => set({ toolStatus: v }),

  reset: () =>
    set({ messages: [], isStreaming: false, sessionCost: 0, sessionTokens: 0, violation: null, toolStatus: null }),
}))
