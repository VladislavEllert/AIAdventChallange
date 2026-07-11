import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'system' | 'light' | 'dark'
type RightTab = 'memory' | 'task' | 'invariants' | 'profiles' | 'settings'

interface AppStore {
  theme: Theme
  setTheme: (t: Theme) => void
  userName: string
  setUserName: (name: string) => void
  activeSessionId: string | null
  setActiveSessionId: (id: string | null) => void
  activeModel: string
  setActiveModel: (m: string) => void
  activeAgentId: string | null
  activeAgentPersona: string
  setActiveAgent: (id: string | null, persona: string) => void
  activeProfileName: string | null
  setActiveProfileName: (name: string | null) => void
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (v: boolean) => void
  rightPanelOpen: boolean
  toggleRightPanel: () => void
  rightPanelTab: RightTab
  setRightPanelTab: (t: RightTab) => void
  ragEnabled: boolean
  setRagEnabled: (v: boolean) => void
  mcpEnabled: boolean
  setMcpEnabled: (v: boolean) => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      theme: 'dark',
      setTheme: (theme) => set({ theme }),
      userName: '',
      setUserName: (userName) => set({ userName }),
      activeSessionId: null,
      setActiveSessionId: (id) => set({ activeSessionId: id }),
      activeModel: 'ollama/qwen3:4b',
      setActiveModel: (m) => set({ activeModel: m }),
      activeAgentId: null,
      activeAgentPersona: '',
      setActiveAgent: (id, persona) => set({ activeAgentId: id, activeAgentPersona: persona }),
      activeProfileName: null,
      setActiveProfileName: (activeProfileName) => set({ activeProfileName }),
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      rightPanelOpen: false,
      toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
      rightPanelTab: 'memory',
      setRightPanelTab: (rightPanelTab) => set({ rightPanelTab }),
      ragEnabled: false,
      setRagEnabled: (ragEnabled) => set({ ragEnabled }),
      mcpEnabled: true,
      setMcpEnabled: (mcpEnabled) => set({ mcpEnabled }),
    }),
    { name: 'agent-web-app' }
  )
)
